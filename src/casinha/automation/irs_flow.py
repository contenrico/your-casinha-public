"""
Shared automation steps for the Portuguese IRS Fatura-Recibo portal.

Both ``invoices.py`` (Airbnb guest invoices) and ``eva_invoices.py`` (Eva's
recurring invoices) drive the same portal pages.  The fragile modal interaction
(locate-all-then-fill) lives here so it cannot drift between the two flows.
"""

from __future__ import annotations

import io
import time
from dataclasses import dataclass
from typing import Callable

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from ..config import INVOICE_URL
from .driver import AutomationResult, ProgressCallback, find_xpath, js_click, make_driver
from .selectors import XPaths

_INITIAL_WINDOW = (756, 556, 22, 22)
_FORM_WINDOW = (1200, 768, 22, 47)


# ---------------------------------------------------------------------------
# Session wrapper
# ---------------------------------------------------------------------------

def run_invoice_session(
    callback: ProgressCallback,
    *,
    headless: bool,
    run: Callable[[WebDriver, io.BytesIO], AutomationResult],
) -> AutomationResult:
    """Open a Chrome session, run *run*, and always quit the driver."""
    screenshot_buf = io.BytesIO()
    w, h, x, y = _INITIAL_WINDOW
    driver = make_driver(width=w, height=h, x=x, y=y, headless=headless)
    try:
        return run(driver, screenshot_buf)
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


# ---------------------------------------------------------------------------
# Login and form header
# ---------------------------------------------------------------------------

def login_irs(
    driver: WebDriver,
    callback: ProgressCallback,
    *,
    nif: str,
    senha: str,
) -> None:
    callback("Opening the IRS website...")
    driver.get(INVOICE_URL)
    time.sleep(3)

    callback("Filling in the login details...")
    find_xpath(driver, XPaths.NIF_TAB).click()
    time.sleep(1)
    find_xpath(driver, XPaths.NIF_INPUT).send_keys(nif)
    find_xpath(driver, XPaths.SENHA_INPUT).send_keys(senha)
    find_xpath(driver, XPaths.SUBMIT_LOGIN).click()
    time.sleep(2)

    callback("Clicking on 'Continuar Login'...")
    try:
        find_xpath(driver, XPaths.CONTINUE_LOGIN).click()
        time.sleep(2)
    except Exception as exc:
        callback(f"'Continuar Login' button not found! Error: {exc}")

    callback("Logged in successfully.")
    time.sleep(1)


def fill_operation_details(
    driver: WebDriver,
    callback: ProgressCallback,
    date_str: str,
) -> None:
    callback("Filling in the date and type of invoice...")
    w, h, x, y = _FORM_WINDOW
    driver.set_window_size(w, h)
    driver.set_window_position(x, y)
    find_xpath(driver, XPaths.DATE).send_keys(date_str)
    find_xpath(driver, XPaths.TYPE).send_keys("Fatura-Recibo")
    time.sleep(2)


def fill_acquirer(
    driver: WebDriver,
    *,
    country: str,
    client_name: str,
    client_id: str,
    use_nif: bool,
) -> None:
    find_xpath(driver, XPaths.COUNTRY).send_keys(country)
    id_xpath = XPaths.NIF_FIELD if use_nif else XPaths.PASSPORT_FIELD
    find_xpath(driver, id_xpath).send_keys(client_id)
    find_xpath(driver, XPaths.NAME).send_keys(client_name)


# ---------------------------------------------------------------------------
# "Adicionar Produtos" modal
# ---------------------------------------------------------------------------

def open_service_modal(driver: WebDriver) -> None:
    find_xpath(driver, XPaths.PAYMENT).click()
    find_xpath(driver, XPaths.ADD_SERVICE).click()
    time.sleep(2)


@dataclass(frozen=True)
class ServiceModalElements:
    type: WebElement
    type_ref: WebElement
    reference: WebElement
    description: WebElement
    unit: WebElement
    amount: WebElement
    iva: WebElement
    save: WebElement


def locate_service_modal(driver: WebDriver) -> ServiceModalElements:
    """
    Locate every modal element up front, while the modal is in its initial DOM
    state, BEFORE sending any keys.

    Filling the type / reference / unit fields reflows the modal's sibling
    <div> layout, which shifts the IVA dropdown away from its original
    div[11] position.  Selenium WebElement handles stay valid across reflows,
    so locating first and filling second is what keeps the IVA dropdown
    reachable.  Do NOT collapse this back into locate-and-fill-one-at-a-time.
    """
    return ServiceModalElements(
        type=find_xpath(driver, XPaths.MODAL_TYPE),
        type_ref=find_xpath(driver, XPaths.MODAL_TYPE_REF),
        reference=find_xpath(driver, XPaths.MODAL_REFERENCE),
        description=find_xpath(driver, XPaths.MODAL_DESCRIPTION),
        unit=find_xpath(driver, XPaths.MODAL_UNIT),
        amount=find_xpath(driver, XPaths.MODAL_AMOUNT),
        iva=find_xpath(driver, XPaths.MODAL_IVA),
        save=find_xpath(driver, XPaths.MODAL_SAVE),
    )


def fill_service_modal(
    modal: ServiceModalElements,
    *,
    type_value: str,
    type_ref: str,
    reference: str,
    description: str,
    unit: str,
    amount: str,
    iva: str,
) -> None:
    modal.type.send_keys(type_value)
    modal.type_ref.send_keys(type_ref)
    modal.reference.send_keys(reference)
    modal.description.send_keys(description)
    modal.unit.send_keys(unit)
    modal.amount.send_keys(amount)
    modal.iva.send_keys(iva)


def try_fill_motivo_isencao(
    driver: WebDriver,
    callback: ProgressCallback,
    motivo: str = "IVA - Regime de isenção - Artigo 53.º n.º 1 do CIVA",
) -> None:
    """
    Fill the "Motivo de isenção" dropdown that appears after selecting 0% IVA.

    Only exercised by Eva's 0% exemption flow.
    """
    try:
        find_xpath(driver, XPaths.MODAL_MOTIVO_ISENCAO).send_keys(motivo)
        time.sleep(1)
    except Exception as exc:
        callback(f"WARNING: Could not fill 'Motivo de isenção' dropdown: {exc}")


def capture_and_save_service_modal(
    driver: WebDriver,
    modal: ServiceModalElements,
    screenshot_buf: io.BytesIO,
) -> None:
    screenshot_buf.write(driver.get_screenshot_as_png())
    screenshot_buf.seek(0)
    modal.save.click()
    time.sleep(1)


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------

def finish_invoice(
    driver: WebDriver,
    callback: ProgressCallback,
    screenshot_buf: io.BytesIO,
    *,
    dry_run: bool,
) -> AutomationResult:
    if dry_run:
        callback("DRY RUN: skipping final submit buttons, pausing 5 minutes...")
        time.sleep(300)
        return AutomationResult(
            success=True,
            message="Dry run complete (invoice NOT submitted).",
            screenshot=screenshot_buf.getvalue() or None,
        )

    callback("Submitting the invoice (first button)...")
    js_click(driver, find_xpath(driver, XPaths.FIRST_EMITIR))
    time.sleep(2)

    callback("Submitting the invoice (second button)...")
    js_click(driver, find_xpath(driver, XPaths.SECOND_EMITIR))
    time.sleep(2)

    callback("Done.")
    return AutomationResult(
        success=True,
        message="Invoice issued successfully.",
        screenshot=screenshot_buf.getvalue() or None,
    )
