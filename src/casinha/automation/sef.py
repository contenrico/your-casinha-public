"""
SEF/SIBA portal automation.

Registers guests from a DataFrame into the Portuguese SIBA system.
"""

from __future__ import annotations

import time

import pandas as pd

from ..config import (
    SEF_URL,
    countries_mapping,
    nationalities_mapping,
    sef_chave,
    sef_estabelecimento,
    sef_uh,
)
from ..domain.columns import (
    CHECKIN_DATE,
    CHECKOUT_DATE,
    COUNTRY_OF_ISSUE,
    COUNTRY_OF_RESIDENCE,
    DATE_OF_BIRTH,
    FIRST_NAME,
    LAST_NAME,
    NATIONALITY,
    PASSPORT_NUMBER,
)
from .driver import (
    AutomationResult,
    ProgressCallback,
    find_id,
    find_xpath,
    js_click,
    make_driver,
)

# ---------------------------------------------------------------------------
# XPath / ID selectors
# ---------------------------------------------------------------------------

_ID_UH = "Conteudo_txtUH"
_ID_ESTABELECIMENTO = "Conteudo_txtEstabelecimento"
_ID_CHAVE = "Conteudo_txtChaveActivacao"
_ID_CONFIRM = "Conteudo_btnConfirmar"
_XPATH_ENTREGA = '//*[@id="myNavbar"]/ul[1]/li[1]/a'
_XPATH_BOLETINS = '//*[@id="myNavbar"]/ul[1]/li[1]/ul/li[1]/a'
_ID_NOVA_LISTA = "Conteudo_btnNovaLista"
_ID_EDIT_LISTA = "Conteudo_dg_btnSelect_0"
_ID_NOVA_BAL = "Conteudo_btnNovaBAL"
_ID_NOME = "Conteudo_txtNome"
_ID_DOB = "Conteudo_txtDataNascimento"
_ID_NATIONALITY = "Conteudo_lstNacionalidade"
_ID_COUNTRY_RES = "Conteudo_lstPaisResidencia"
_ID_PASSPORT = "Conteudo_txtNumPassaporteBI"
_ID_COUNTRY_ISSUE = "Conteudo_lstPaisEmissor"
_ID_CHECKIN = "Conteudo_txtDataEntrada"
_ID_CHECKOUT = "Conteudo_txtDataSaida"
_ID_SAVE = "Conteudo_btnActualizarBAL"
_ID_SEND = "Conteudo_btnEnviarLista"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fill_in_sef_form(df: pd.DataFrame, callback: ProgressCallback) -> AutomationResult:
    """
    Register every guest in *df* on the SIBA portal.

    *callback* is called with a progress string after each meaningful step.
    Returns an AutomationResult with success=True only if all guests were
    submitted without an unhandled exception.
    """
    countries = countries_mapping()
    nationalities = nationalities_mapping()

    driver = make_driver()
    try:
        callback("Opening the SEF website...")
        driver.get(SEF_URL)
        time.sleep(2)

        callback("Filling in the establishment details...")
        find_id(driver, _ID_UH).send_keys(sef_uh())
        find_id(driver, _ID_ESTABELECIMENTO).send_keys(sef_estabelecimento())
        find_id(driver, _ID_CHAVE).send_keys(sef_chave())
        js_click(driver, find_id(driver, _ID_CONFIRM))
        time.sleep(2)

        find_xpath(driver, _XPATH_ENTREGA).click()
        find_xpath(driver, _XPATH_BOLETINS).click()
        time.sleep(2)

        callback("Creating a new list...")
        find_id(driver, _ID_NOVA_LISTA).click()
        time.sleep(2)

        callback("Editing the list...")
        find_id(driver, _ID_EDIT_LISTA).click()
        time.sleep(2)

        try:
            callback("Trying to add new bulletin in case list already existed...")
            js_click(driver, find_id(driver, _ID_NOVA_BAL))
            callback("Added new bulletin.")
            time.sleep(2)
        except Exception as exc:
            callback(f"Skipped adding new bulletin. Error: {exc}")
            time.sleep(1)

        callback("Preparing to fill in guest details...")
        for _, row in df.iterrows():
            name = f"{row[FIRST_NAME]} {row[LAST_NAME]}"

            find_id(driver, _ID_NOME).send_keys(name)
            find_id(driver, _ID_DOB).send_keys(row[DATE_OF_BIRTH])
            find_id(driver, _ID_NATIONALITY).send_keys(countries[nationalities[row[NATIONALITY]]])
            find_id(driver, _ID_COUNTRY_RES).send_keys(countries[row[COUNTRY_OF_RESIDENCE]])
            find_id(driver, _ID_PASSPORT).send_keys(row[PASSPORT_NUMBER])
            find_id(driver, _ID_COUNTRY_ISSUE).send_keys(countries[row[COUNTRY_OF_ISSUE]])
            find_id(driver, _ID_CHECKIN).send_keys(row[CHECKIN_DATE])
            find_id(driver, _ID_CHECKOUT).send_keys(row[CHECKOUT_DATE])
            find_id(driver, _ID_SAVE).click()

            callback(f"Details for {name} saved. Proceeding to next guest...")
            time.sleep(3)

        callback("Finalizing and sending the list...")
        find_id(driver, _ID_SEND).click()
        time.sleep(3)

        callback("Done.")
        return AutomationResult(success=True, message="Guests registered successfully.")

    except Exception as exc:
        msg = f"SEF registration error: {exc}"
        callback(msg)
        return AutomationResult(success=False, message=msg)

    finally:
        driver.quit()
