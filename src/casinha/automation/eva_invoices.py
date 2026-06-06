"""
Portuguese tax portal (IRS) invoice automation for Eva.

Issues Fatura-Recibo invoices using Eva's credentials (EVA_NIF / EVA_SENHA).
All clients are Portuguese (NIF field), IVA is 0% exemption (Artigo 53.º),
and amounts are submitted as-is (no VAT stripping).
"""

from __future__ import annotations

import calendar
import io
import random
import time
from dataclasses import dataclass
from datetime import date
from typing import Callable

from selenium.webdriver.remote.webdriver import WebDriver

from ..config import eva_nif, eva_senha
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
    try_fill_motivo_isencao,
)

# ---------------------------------------------------------------------------
# Portuguese month names
# ---------------------------------------------------------------------------

PT_MONTHS = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


# ---------------------------------------------------------------------------
# Invoice data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EvaInvoice:
    client_name: str
    client_nif: str
    reference: str
    description: str
    unit: str          # e.g. "N/A - Não Aplicável" or "Unidade - Unidade"
    amount: float
    invoice_date: date


# ---------------------------------------------------------------------------
# Silvia's randomised service line items
# ---------------------------------------------------------------------------

# Plausible extra tasks for an Alojamento Local, picked at random on page load.
SILVIA_EXTRA_TASKS = [
    "1x Reposição de produtos de acolhimento e amenities",
    "1x Lavagem e tratamento de roupa de cama e toalhas",
    "1x Verificação e reposição de stock da cozinha",
    "1x Pequenas reparações e manutenção preventiva",
    "1x Limpeza profunda da cozinha e casas de banho",
    "1x Coordenação de check-in e check-out de hóspedes",
    "1x Gestão de resíduos e limpeza de áreas comuns",
    "1x Inspeção do apartamento e reporte de anomalias",
]


def default_silvia_items() -> list[str]:
    """Return randomised default service line items for Silvia's invoice."""
    cleanings = random.choice([8, 9, 10, 11])
    maintenance = random.choice([1, 2, 3])
    return [
        f"{cleanings}x Limpeza e preparação do apartamento após saídas de hóspedes",
        f"{maintenance}x Tarefas de manutenção",
        random.choice(SILVIA_EXTRA_TASKS),
    ]


# ---------------------------------------------------------------------------
# Default invoices factory
# ---------------------------------------------------------------------------

def default_eva_invoices(
    year: int,
    month: int,
    silvia_amount: float,
    silvia_description: str | None = None,
) -> list[EvaInvoice]:
    """Return the four pre-filled Eva invoices for the given period."""
    month_label = PT_MONTHS[month]
    last_day = calendar.monthrange(year, month)[1]
    inv_date = date(year, month, last_day)

    cleaning_ref = f"Limpeza doméstica - {month_label} {year}"
    cleaning_desc = "Serviço de limpeza doméstica (2 prestações no mês)"
    al_ref = f"Limpeza, preparação e apoio operacional de AL - {month_label} {year}"
    if silvia_description is None:
        silvia_description = "\n".join(default_silvia_items())

    return [
        EvaInvoice(
            client_name="Luis Miguel Monteiro Pereira Rebola",
            client_nif="222747293",
            reference=cleaning_ref,
            description=cleaning_desc,
            unit="N/A - Não Aplicável",
            amount=80.00,
            invoice_date=inv_date,
        ),
        EvaInvoice(
            client_name="CONDOMINIO DO PREDIO SITO NA RUA FRANCISCO MANTERO LOTE B",
            client_nif="900996226",
            reference=cleaning_ref,
            description=cleaning_desc,
            unit="N/A - Não Aplicável",
            amount=80.00,
            invoice_date=inv_date,
        ),
        EvaInvoice(
            client_name="Condominio Marvila Plaza",
            client_nif="902237187",
            reference=cleaning_ref,
            description=cleaning_desc,
            unit="N/A - Não Aplicável",
            amount=65.00,
            invoice_date=inv_date,
        ),
        EvaInvoice(
            client_name="Silvia Pau",
            client_nif="292907885",
            reference=al_ref,
            description=silvia_description,
            unit="N/A - Não Aplicável",
            amount=silvia_amount,
            invoice_date=inv_date,
        ),
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_amount(amount: float) -> str:
    """Format a float to a two-decimal string (no VAT stripping)."""
    return f"{amount:.2f}"


def _issue_eva_invoice(
    driver: WebDriver,
    screenshot_buf: io.BytesIO,
    callback: ProgressCallback,
    *,
    invoice: EvaInvoice,
    dry_run: bool,
) -> AutomationResult:
    date_str = invoice.invoice_date.strftime("%Y-%m-%d")

    login_irs(driver, callback, nif=eva_nif(), senha=eva_senha())
    fill_operation_details(driver, callback, date_str)

    callback("Filling in client details...")
    fill_acquirer(
        driver,
        country="Portugal",
        client_name=invoice.client_name,
        client_id=invoice.client_nif,
        use_nif=True,
    )

    open_service_modal(driver)
    callback("Filling in service details...")
    modal = locate_service_modal(driver)

    fill_service_modal(
        modal,
        type_value="Serviço",
        type_ref="Outro",
        reference=invoice.reference,
        description=invoice.description,
        unit=invoice.unit,
        amount=_fmt_amount(invoice.amount),
        iva="0%",
    )

    callback("Selecting 0% IVA exemption (Artigo 53.º)...")
    time.sleep(1)
    try_fill_motivo_isencao(driver, callback)

    capture_and_save_service_modal(driver, modal, screenshot_buf)
    return finish_invoice(driver, callback, screenshot_buf, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Single-invoice automation
# ---------------------------------------------------------------------------

def fill_in_eva_invoice(
    callback: ProgressCallback,
    invoice: EvaInvoice,
    *,
    headless: bool = True,
    dry_run: bool = False,
) -> AutomationResult:
    """
    Issue a single Fatura-Recibo on the IRS portal using Eva's credentials.

    Uses 0% IVA exemption (Artigo 53.º n.º 1 do CIVA). Amount is submitted
    as-is (no VAT stripping). Always issues to Portuguese clients (NIF field).

    Args:
        headless: Run Chrome headless. Set False (dev) to watch the browser.
        dry_run:  When True, fills the form but does NOT click the two final
                  submit buttons; instead pauses 5 minutes so the populated
                  form can be inspected.
    """
    return run_invoice_session(
        callback,
        headless=headless,
        run=lambda driver, screenshot_buf: _issue_eva_invoice(
            driver,
            screenshot_buf,
            callback,
            invoice=invoice,
            dry_run=dry_run,
        ),
    )


# ---------------------------------------------------------------------------
# Batch submission
# ---------------------------------------------------------------------------

InvoiceResultCallback = Callable[[EvaInvoice, AutomationResult], None]


def issue_eva_invoices(
    callback: ProgressCallback,
    invoices: list[EvaInvoice],
    *,
    headless: bool = True,
    dry_run: bool = False,
    on_result: InvoiceResultCallback | None = None,
) -> list[tuple[EvaInvoice, AutomationResult]]:
    """
    Submit every invoice in *invoices*, continuing even when one fails.

    Each invoice opens its own fresh browser session so a failure does not
    leave the driver in a broken state for subsequent invoices.

    ``headless`` and ``dry_run`` are forwarded to ``fill_in_eva_invoice``.
    ``on_result`` is called immediately after each invoice completes.
    """
    results: list[tuple[EvaInvoice, AutomationResult]] = []
    for i, invoice in enumerate(invoices, start=1):
        callback(f"--- Invoice {i}/{len(invoices)}: {invoice.client_name} ---")
        try:
            result = fill_in_eva_invoice(
                callback, invoice, headless=headless, dry_run=dry_run
            )
        except Exception as exc:
            result = AutomationResult(
                success=False,
                message=f"Unexpected error: {exc}",
                screenshot=None,
            )
        results.append((invoice, result))
        if on_result is not None:
            on_result(invoice, result)
    return results
