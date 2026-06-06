"""
Portuguese tax portal (IRS) invoice automation.

Issues a Fatura-Recibo for an Airbnb stay.
"""

from __future__ import annotations

import io
from datetime import date

import pandas as pd
from selenium.webdriver.remote.webdriver import WebDriver

from ..config import (
    AL_ADDRESS,
    AL_NUMBER,
    VAT_RATE,
    countries_mapping,
    pdf_nif,
    pdf_senha,
)
from ..domain.columns import CHECKIN_DATE, CHECKOUT_DATE, COUNTRY_OF_RESIDENCE, FIRST_NAME, LAST_NAME, PASSPORT_NUMBER
from .driver import AutomationResult, ProgressCallback
from .irs_flow import (
    capture_and_save_service_modal,
    fill_acquirer,
    fill_operation_details,
    fill_service_modal,
    finish_invoice,
    locate_service_modal,
    login_irs,
    open_service_modal,
    run_invoice_session,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_amount(raw: float) -> str:
    """Remove VAT and format to two decimal places as a string."""
    net = round(raw / (1 + VAT_RATE), 2)
    s = str(net)
    if "." not in s:
        return s + ".00"
    decimals = s.split(".")[1]
    return s + "0" if len(decimals) == 1 else s


def _issue_invoice(
    driver: WebDriver,
    screenshot_buf: io.BytesIO,
    callback: ProgressCallback,
    *,
    row: pd.Series,
    amount: float,
    date_str: str,
    invoice_nif: str | None,
    dry_run: bool,
) -> AutomationResult:
    countries = countries_mapping()

    login_irs(driver, callback, nif=pdf_nif(), senha=pdf_senha())
    fill_operation_details(driver, callback, date_str)

    callback("Filling in the invoice details...")
    country = countries[row[COUNTRY_OF_RESIDENCE]]
    is_portugal = country.lower() == "portugal"
    fill_acquirer(
        driver,
        country=country,
        client_name=f"{row[FIRST_NAME]} {row[LAST_NAME]}",
        client_id=(invoice_nif or "") if is_portugal else row[PASSPORT_NUMBER],
        use_nif=is_portugal,
    )

    open_service_modal(driver)
    modal = locate_service_modal(driver)

    checkin_str = pd.to_datetime(row[CHECKIN_DATE], dayfirst=True).strftime("%d/%m/%Y")
    checkout_str = pd.to_datetime(row[CHECKOUT_DATE], dayfirst=True).strftime("%d/%m/%Y")
    description = (
        f"Prestação de serviços de alojamento mobilado para turistas, "
        f"da data {checkin_str} a {checkout_str}, "
        f"no AL {AL_NUMBER}, sito na morada: {AL_ADDRESS}"
    )

    fill_service_modal(
        modal,
        type_value="Serviço",
        type_ref="Outro",
        reference="Alojamento Local",
        description=description,
        unit="N/A",
        amount=_format_amount(amount),
        iva="6%",
    )
    capture_and_save_service_modal(driver, modal, screenshot_buf)
    return finish_invoice(driver, callback, screenshot_buf, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fill_in_invoice(
    callback: ProgressCallback,
    guest_df: pd.DataFrame,
    amount: float,
    invoice_date: date | None = None,
    invoice_nif: str | None = None,
    *,
    headless: bool = True,
    dry_run: bool = False,
) -> AutomationResult:
    """
    Issue a Fatura-Recibo on the Portuguese IRS portal.

    Args:
        callback:     Called with a progress string after each step.
        guest_df:     Single-row DataFrame with guest details.
        amount:       Gross payout amount (VAT will be stripped before submission).
        invoice_date: Invoice date; defaults to the guest's check-out date.
        invoice_nif:  NIF to use when the guest's country is Portugal.
        headless:     Run Chrome headless. Set False (dev) to watch the browser.
        dry_run:      When True, fills the form but does NOT click the two final
                      submit buttons; instead pauses 5 minutes so the populated
                      form can be inspected.

    Returns:
        AutomationResult with a screenshot (bytes) captured just before
        submission (or at the point of failure).
    """
    if guest_df.empty:
        return AutomationResult(success=False, message="Guest data is empty.", screenshot=None)

    row = guest_df.iloc[0]
    if invoice_date is None:
        invoice_date = pd.to_datetime(row[CHECKOUT_DATE], dayfirst=True).date()
    date_str = invoice_date.strftime("%Y-%m-%d")

    return run_invoice_session(
        callback,
        headless=headless,
        run=lambda driver, screenshot_buf: _issue_invoice(
            driver,
            screenshot_buf,
            callback,
            row=row,
            amount=amount,
            date_str=date_str,
            invoice_nif=invoice_nif,
            dry_run=dry_run,
        ),
    )
