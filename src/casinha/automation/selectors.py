"""
Shared XPath selectors for the Portuguese IRS portal (Fatura-Recibo flow).

Both the standard Airbnb invoice flow (``invoices.py``) and Eva's invoice flow
(``eva_invoices.py``) drive the same portal pages, so the selectors live here to
avoid duplication. Import the ``XPaths`` namespace and reference its attributes,
e.g. ``find_xpath(driver, XPaths.NIF_TAB)``.
"""

from __future__ import annotations


class XPaths:
    """Namespace of XPath selectors for the IRS Fatura-Recibo portal."""

    # -- Login -------------------------------------------------------------
    NIF_TAB = '//*[@id="radix-:r0:-trigger-N"]'
    NIF_INPUT = (
        '/html/body/div/div/main/div[1]/div[3]/div[1]/div[3]/form/div[1]/div[2]/div/input'
    )
    SENHA_INPUT = (
        '/html/body/div/div/main/div[1]/div[3]/div[1]/div[3]/form/div[2]/div[2]/div/input'
    )
    SUBMIT_LOGIN = '//*[@id="radix-:r0:-content-N"]/form/button'
    CONTINUE_LOGIN = '/html/body/div/div/div[1]/div/div[3]/button[1]'

    # -- Operation / acquirer details -------------------------------------
    DATE = (
        '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2'
        '/div[1]/div[2]/div/dados-de-operacao-v2/div/div[3]/div[3]/div[1]/lf-date/div/div[1]/input'
    )
    TYPE = (
        '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2'
        '/div[1]/div[2]/div/dados-de-operacao-v2/div/div[3]/div[3]/div[2]/lf-dropdown/div/select'
    )
    COUNTRY = (
        '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2'
        '/div[1]/div[2]/div/dados-adquirente-v2/div[1]/div[2]/div[1]/div[1]/lf-dropdown/div/select'
    )
    PASSPORT_FIELD = (
        '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2'
        '/div[1]/div[2]/div/dados-adquirente-v2/div[1]/div[2]/div[1]/div[2]/lf-text/div/input'
    )
    NIF_FIELD = (
        '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2'
        '/div[1]/div[2]/div/dados-adquirente-v2/div[1]/div[2]/div[1]/div[2]/lf-nif/div/input'
    )
    NAME = (
        '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2'
        '/div[1]/div[2]/div/dados-adquirente-v2/div[1]/div[2]/div[2]/div/lf-text/div/input'
    )
    PAYMENT = '//*[@id="motivoEmissao"]/div/div/pf-radio/div/div[1]/label/input'
    ADD_SERVICE = '//*[@id="Bens&ServicosFT"]/div/div/table/tfoot/tr/td/button'

    # -- "Adicionar Produtos" modal ---------------------------------------
    MODAL_TYPE = (
        '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[4]/div[1]/lf-dropdown/div/select'
    )
    MODAL_TYPE_REF = (
        '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[4]/div[2]/lf-dropdown/div/select'
    )
    MODAL_REFERENCE = (
        '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[5]/div/lf-text/div/input'
    )
    MODAL_DESCRIPTION = (
        '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[6]/div/lf-textarea/div/textarea'
    )
    MODAL_UNIT = (
        '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[8]/div[2]/lf-dropdown/div/select'
    )
    MODAL_AMOUNT = (
        '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div[1]/div/div[2]/div/div[9]/div[1]/div[1]/input'
    )
    MODAL_IVA = (
        '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div[1]/div/div[2]/div/div[11]/div/lf-dropdown/div/select'
    )
    # After selecting 0% IVA, a second dropdown for "Motivo de isenção" appears
    # inside div[11] (only exercised by Eva's 0% exemption flow).
    MODAL_MOTIVO_ISENCAO = (
        '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div[1]/div/div[2]/div/div[12]/div[2]/lf-dropdown/div/select'
    )
    MODAL_SAVE = (
        '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[3]/button[2]'
    )

    # -- Submission buttons -----------------------------------------------
    FIRST_EMITIR = (
        '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2'
        '/div[1]/div[1]/div[1]/div[1]/div[2]/button'
    )
    SECOND_EMITIR = (
        '//*[@id="confirmarEmissaoModal"]/confirmar-emissao/div/div/div[3]/button[2]'
    )
