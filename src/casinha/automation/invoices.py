"""
Portuguese tax portal (IRS) invoice automation.

Issues a Fatura-Recibo for an Airbnb stay.
"""

from __future__ import annotations

import io
import time
from datetime import date

import pandas as pd

from ..config import (
    AL_ADDRESS,
    AL_NUMBER,
    INVOICE_URL,
    VAT_RATE,
    countries_mapping,
    pdf_nif,
    pdf_senha,
)
from ..domain.columns import CHECKIN_DATE, CHECKOUT_DATE, COUNTRY_OF_RESIDENCE, FIRST_NAME, LAST_NAME, PASSPORT_NUMBER
from .driver import (
    AutomationResult,
    ProgressCallback,
    find_xpath,
    js_click,
    make_driver,
)

# ---------------------------------------------------------------------------
# XPath selectors
# ---------------------------------------------------------------------------

_XPATH_NIF_TAB = '//*[@id="radix-:r0:-trigger-N"]'
_XPATH_NIF_INPUT = '/html/body/div/div/main/div[1]/div[3]/div[1]/div[3]/form/div[1]/div[2]/div/input'
_XPATH_SENHA_INPUT = '/html/body/div/div/main/div[1]/div[3]/div[1]/div[3]/form/div[2]/div[2]/div/input'
_XPATH_SUBMIT_LOGIN = '//*[@id="radix-:r0:-content-N"]/form/button'
_XPATH_CONTINUE_LOGIN = '/html/body/div/div/div[1]/div/div[3]/button[1]'

_XPATH_DATE = (
    '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2'
    '/div[1]/div[2]/div/dados-de-operacao-v2/div/div[3]/div[3]/div[1]/lf-date/div/div[1]/input'
)
_XPATH_TYPE = (
    '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2'
    '/div[1]/div[2]/div/dados-de-operacao-v2/div/div[3]/div[3]/div[2]/lf-dropdown/div/select'
)
_XPATH_COUNTRY = (
    '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2'
    '/div[1]/div[2]/div/dados-adquirente-v2/div[1]/div[2]/div[1]/div[1]/lf-dropdown/div/select'
)
_XPATH_PASSPORT_FIELD = (
    '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2'
    '/div[1]/div[2]/div/dados-adquirente-v2/div[1]/div[2]/div[1]/div[2]/lf-text/div/input'
)
_XPATH_NIF_FIELD = (
    '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2'
    '/div[1]/div[2]/div/dados-adquirente-v2/div[1]/div[2]/div[1]/div[2]/lf-nif/div/input'
)
_XPATH_NAME = (
    '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2'
    '/div[1]/div[2]/div/dados-adquirente-v2/div[1]/div[2]/div[2]/div/lf-text/div/input'
)
_XPATH_PAYMENT = '//*[@id="motivoEmissao"]/div/div/pf-radio/div/div[1]/label/input'
_XPATH_ADD_SERVICE = '//*[@id="Bens&ServicosFT"]/div/div/table/tfoot/tr/td/button'

_XPATH_MODAL_TYPE = (
    '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[4]/div[1]/lf-dropdown/div/select'
)
_XPATH_MODAL_TYPE_REF = (
    '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[4]/div[2]/lf-dropdown/div/select'
)
_XPATH_MODAL_REFERENCE = (
    '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[5]/div/lf-text/div/input'
)
_XPATH_MODAL_DESCRIPTION = (
    '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[6]/div/lf-textarea/div/textarea'
)
_XPATH_MODAL_UNIT = (
    '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[8]/div[2]/lf-dropdown/div/select'
)
_XPATH_MODAL_AMOUNT = (
    '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div[1]/div/div[2]/div/div[9]/div[1]/div[1]/input'
)
_XPATH_MODAL_IVA = (
    '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div[1]/div/div[2]/div/div[11]/div/lf-dropdown/div/select'
)
_XPATH_MODAL_SAVE = (
    '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[3]/button[2]'
)
_XPATH_FIRST_EMITIR = (
    '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2'
    '/div[1]/div[1]/div[1]/div[1]/div[2]/button'
)
_XPATH_SECOND_EMITIR = (
    '//*[@id="confirmarEmissaoModal"]/confirmar-emissao/div/div/div[3]/button[2]'
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fill_in_invoice(
    callback: ProgressCallback,
    guest_df: pd.DataFrame,
    amount: float,
    invoice_date: date | None = None,
    invoice_nif: str | None = None,
) -> AutomationResult:
    """
    Issue a Fatura-Recibo on the Portuguese IRS portal.

    Args:
        callback:     Called with a progress string after each step.
        guest_df:     Single-row DataFrame with guest details.
        amount:       Gross payout amount (VAT will be stripped before submission).
        invoice_date: Invoice date; defaults to the guest's check-out date.
        invoice_nif:  NIF to use when the guest's country is Portugal.

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

    screenshot_buf = io.BytesIO()
    countries = countries_mapping()
    driver = make_driver(width=1200, height=768)
    # NOTE: for debugging purposes, pass headless=False to watch the browser:
    # driver = make_driver(width=1200, height=768, headless=False)

    try:
        callback("Opening the IRS website...")
        driver.get(INVOICE_URL)
        time.sleep(3)

        callback("Filling in the login details...")
        find_xpath(driver, _XPATH_NIF_TAB).click()
        time.sleep(1)

        find_xpath(driver, _XPATH_NIF_INPUT).send_keys(pdf_nif())
        find_xpath(driver, _XPATH_SENHA_INPUT).send_keys(pdf_senha())
        find_xpath(driver, _XPATH_SUBMIT_LOGIN).click()
        time.sleep(2)

        callback("Clicking on 'Continuar Login'...")
        try:
            find_xpath(driver, _XPATH_CONTINUE_LOGIN).click()
            time.sleep(2)
        except Exception as exc:
            callback(f"'Continuar Login' button not found! Error: {exc}")

        callback("Logged in successfully.")
        time.sleep(1)

        callback("Filling in the date and type of invoice...")
        find_xpath(driver, _XPATH_DATE).send_keys(date_str)
        find_xpath(driver, _XPATH_TYPE).send_keys("Fatura-Recibo")
        time.sleep(2)

        callback("Filling in the invoice details...")
        country = countries[row[COUNTRY_OF_RESIDENCE]]
        find_xpath(driver, _XPATH_COUNTRY).send_keys(country)

        if country.lower() == "portugal":
            find_xpath(driver, _XPATH_NIF_FIELD).send_keys(invoice_nif or "")
        else:
            find_xpath(driver, _XPATH_PASSPORT_FIELD).send_keys(row[PASSPORT_NUMBER])

        find_xpath(driver, _XPATH_NAME).send_keys(f"{row[FIRST_NAME]} {row[LAST_NAME]}")
        find_xpath(driver, _XPATH_PAYMENT).click()
        find_xpath(driver, _XPATH_ADD_SERVICE).click()
        time.sleep(2)

        find_xpath(driver, _XPATH_MODAL_TYPE).send_keys("Serviço")
        find_xpath(driver, _XPATH_MODAL_TYPE_REF).send_keys("Outro")
        find_xpath(driver, _XPATH_MODAL_REFERENCE).send_keys("Alojamento Local")

        checkin_str = pd.to_datetime(row[CHECKIN_DATE], dayfirst=True).strftime("%d/%m/%Y")
        checkout_str = pd.to_datetime(row[CHECKOUT_DATE], dayfirst=True).strftime("%d/%m/%Y")
        description = (
            f"Prestação de serviços de alojamento mobilado para turistas, "
            f"da data {checkin_str} a {checkout_str}, "
            f"no AL {AL_NUMBER}, sito na morada: {AL_ADDRESS}"
        )
        find_xpath(driver, _XPATH_MODAL_DESCRIPTION).send_keys(description)
        find_xpath(driver, _XPATH_MODAL_UNIT).send_keys("N/A")
        find_xpath(driver, _XPATH_MODAL_AMOUNT).send_keys(_format_amount(amount))
        find_xpath(driver, _XPATH_MODAL_IVA).send_keys("6%")

        screenshot_buf.write(driver.get_screenshot_as_png())
        screenshot_buf.seek(0)

        find_xpath(driver, _XPATH_MODAL_SAVE).click()
        time.sleep(1)

        callback("Submitting the invoice (first button)...")
        js_click(driver, find_xpath(driver, _XPATH_FIRST_EMITIR))
        time.sleep(2)

        callback("Submitting the invoice (second button)...")
        js_click(driver, find_xpath(driver, _XPATH_SECOND_EMITIR))
        time.sleep(2)

        # NOTE: for debugging purposes when running automation in browser, uncomment to pause:
        # time.sleep(20)

        callback("Done.")
        return AutomationResult(
            success=True,
            message="Invoice issued successfully.",
            screenshot=screenshot_buf.getvalue() or None,
        )

    except Exception as exc:
        msg = f"Invoice automation error: {exc}"
        callback(msg)
        try:
            screenshot_buf = io.BytesIO(driver.get_screenshot_as_png())
        except Exception:
            pass
        return AutomationResult(
            success=False,
            message=msg,
            screenshot=screenshot_buf.getvalue() or None,
        )

    finally:
        driver.quit()
