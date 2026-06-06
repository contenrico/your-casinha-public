"""Eva's Invoices page – issue Fatura-Recibo invoices on behalf of Eva."""

from __future__ import annotations

import calendar
import random
from datetime import date, datetime

import streamlit as st

from app_pages.dev_controls import dev_dry_run, dev_headless, init_dev_controls, render_dev_control_panel
from src.casinha.automation.driver import AutomationResult
from src.casinha.automation.eva_invoices import (
    EvaInvoice,
    PT_MONTHS,
    SILVIA_EXTRA_TASKS,
    default_eva_invoices,
    default_silvia_items,
    issue_eva_invoices,
)
DEFAULT_UNIT = "N/A - Não Aplicável"


def _invoice_to_dict(inv: EvaInvoice, *, iid: int, is_silvia: bool) -> dict:
    """Convert an EvaInvoice default into a mutable session-state dict."""
    return {
        "id": iid,
        "is_silvia": is_silvia,
        "client_name": inv.client_name,
        "client_nif": inv.client_nif,
        "reference": inv.reference,
        "description": inv.description,
        "unit": inv.unit,
        "amount": inv.amount,
        "invoice_date": inv.invoice_date,
    }


def _blank_invoice(*, iid: int, reference: str, invoice_date: date) -> dict:
    """Create an empty invoice row for a user-added invoice."""
    return {
        "id": iid,
        "is_silvia": False,
        "client_name": "",
        "client_nif": "",
        "reference": reference,
        "description": "",
        "unit": DEFAULT_UNIT,
        "amount": 0.01,
        "invoice_date": invoice_date,
    }


def _silvia_amount_hint() -> tuple[float, float]:
    """Return (sum of invoices 1–3, suggested amount for Silvia)."""
    fixed_sum = sum(
        float(st.session_state.get(f"eva_amount_{inv['id']}", inv["amount"]))
        for inv in st.session_state.eva_invoices[:3]
    )
    target = st.session_state.eva_target_total
    return fixed_sum, target - fixed_sum


st.title("Eva's Invoices")

init_dev_controls()

# ---------------------------------------------------------------------------
# Session-state initialisation (runs only once per session)
# ---------------------------------------------------------------------------

today = datetime.today()
prev_month = today.month - 1 or 12
prev_year = today.year if today.month > 1 else today.year - 1

if "eva_target_total" not in st.session_state:
    st.session_state.eva_target_total = random.choice([930, 940, 950, 960, 970, 980])

if "silvia_items" not in st.session_state:
    st.session_state.silvia_items = [
        {"id": i, "text": text} for i, text in enumerate(default_silvia_items())
    ]
    st.session_state.silvia_next_id = len(st.session_state.silvia_items)

if "eva_invoices" not in st.session_state:
    _silvia_desc = "\n".join(item["text"] for item in st.session_state.silvia_items)
    _fixed_sum = sum(
        inv.amount
        for inv in default_eva_invoices(
            year=prev_year,
            month=prev_month,
            silvia_amount=0.0,
            silvia_description=_silvia_desc,
        )[:3]
    )
    _silvia_default = st.session_state.eva_target_total - _fixed_sum
    _defaults = default_eva_invoices(
        year=prev_year,
        month=prev_month,
        silvia_amount=_silvia_default,
        silvia_description=_silvia_desc,
    )
    # Silvia is the last default invoice and owns the dynamic line-item editor.
    st.session_state.eva_invoices = [
        _invoice_to_dict(inv, iid=i, is_silvia=(i == len(_defaults) - 1))
        for i, inv in enumerate(_defaults)
    ]
    st.session_state.eva_next_invoice_id = len(_defaults)

# Apply a pending Silvia line-item shuffle before any widgets are instantiated
# (a widget's session-state value cannot be changed once its widget exists).
_pending_shuffle = st.session_state.pop("silvia_shuffle_pending", None)
if _pending_shuffle is not None:
    for _item in st.session_state.silvia_items:
        if _item["id"] == _pending_shuffle:
            _new_text = random.choice(SILVIA_EXTRA_TASKS)
            _item["text"] = _new_text
            st.session_state[f"silvia_item_{_pending_shuffle}"] = _new_text
            break

# ---------------------------------------------------------------------------
# Month-year selector
# ---------------------------------------------------------------------------

st.subheader("Billing period")

col_month, col_year = st.columns([2, 1])
with col_month:
    month_names = list(PT_MONTHS.values())
    selected_month_name = st.selectbox(
        "Month:",
        options=month_names,
        index=prev_month - 1,
        key="eva_month",
    )
with col_year:
    selected_year = st.number_input(
        "Year:",
        min_value=2020,
        max_value=2100,
        value=prev_year,
        step=1,
        key="eva_year",
    )

selected_month = month_names.index(selected_month_name) + 1
last_day_of_month = calendar.monthrange(selected_year, selected_month)[1]
default_invoice_date = date(selected_year, selected_month, last_day_of_month)
default_reference = f"Limpeza doméstica - {selected_month_name} {selected_year}"

# ---------------------------------------------------------------------------
# Invoice editors (dynamic – add / remove whole invoices)
# ---------------------------------------------------------------------------

st.subheader("Invoices")

select_col, deselect_col, _ = st.columns([1, 1, 4])
if select_col.button("Select all", key="eva_select_all"):
    for inv in st.session_state.eva_invoices:
        st.session_state[f"eva_selected_{inv['id']}"] = True
    st.rerun()
if deselect_col.button("Deselect all", key="eva_deselect_all"):
    for inv in st.session_state.eva_invoices:
        st.session_state[f"eva_selected_{inv['id']}"] = False
    st.rerun()

invoice_configs: list[dict] = []
remove_invoice_id: int | None = None

for position, invoice in enumerate(st.session_state.eva_invoices):
    iid = invoice["id"]
    title = invoice["client_name"].strip() or "New invoice"
    with st.expander(f"Invoice {position + 1} – {title}", expanded=True):
        head_check, head_title, head_remove = st.columns([0.08, 0.72, 0.20])
        with head_check:
            selected = st.checkbox(
                "Include",
                value=True,
                key=f"eva_selected_{iid}",
                label_visibility="collapsed",
            )
        with head_title:
            st.markdown(f"**{'✅ Selected' if selected else '⬜ Deselected'}**")
        with head_remove:
            if st.button("🗑️ Remove", key=f"eva_remove_{iid}"):
                remove_invoice_id = iid

        c1, c2 = st.columns(2)
        with c1:
            client_name = st.text_input(
                "Client name:",
                value=invoice["client_name"],
                key=f"eva_name_{iid}",
            )
            client_nif = st.text_input(
                "Client NIF:",
                value=invoice["client_nif"],
                key=f"eva_nif_{iid}",
            )
            if invoice["is_silvia"]:
                _, silvia_suggested = _silvia_amount_hint()
                amount_label = f"Amount (€), suggested: {silvia_suggested:.2f}"
            else:
                amount_label = "Amount (€):"
            amount = st.number_input(
                amount_label,
                value=float(invoice["amount"]),
                min_value=0.01,
                step=10.0,
                format="%.2f",
                key=f"eva_amount_{iid}",
            )
        with c2:
            reference = st.text_input(
                "Reference:",
                value=invoice["reference"],
                key=f"eva_ref_{iid}",
            )
            unit = st.text_input(
                "Unit:",
                value=invoice["unit"],
                key=f"eva_unit_{iid}",
            )
            inv_date = st.date_input(
                "Invoice date:",
                value=invoice["invoice_date"],
                format="DD-MM-YYYY",
                key=f"eva_date_{iid}",
            )

        if invoice["is_silvia"]:
            st.markdown("**Service line items:**")
            remove_item_id: int | None = None
            for item in st.session_state.silvia_items:
                line_col, shuffle_col, btn_col = st.columns([0.84, 0.08, 0.08])
                item["text"] = line_col.text_input(
                    "Line item",
                    value=item["text"],
                    key=f"silvia_item_{item['id']}",
                    label_visibility="collapsed",
                )
                if shuffle_col.button(
                    "🎲", key=f"silvia_shuffle_{item['id']}", help="Pick another random task"
                ):
                    # Defer the overwrite: the widget for this key is already
                    # instantiated this run, so apply it before widgets render next run.
                    st.session_state.silvia_shuffle_pending = item["id"]
                    st.rerun()
                if btn_col.button("✖", key=f"silvia_rm_{item['id']}", help="Remove item"):
                    remove_item_id = item["id"]
            if remove_item_id is not None:
                st.session_state.silvia_items = [
                    it for it in st.session_state.silvia_items if it["id"] != remove_item_id
                ]
                st.rerun()
            if st.button("➕ Add line item", key="silvia_add_item"):
                st.session_state.silvia_items.append(
                    {"id": st.session_state.silvia_next_id, "text": ""}
                )
                st.session_state.silvia_next_id += 1
                st.rerun()
            description = "\n".join(
                it["text"] for it in st.session_state.silvia_items if it["text"].strip()
            )
        else:
            description = st.text_area(
                "Description:",
                value=invoice["description"],
                key=f"eva_desc_{iid}",
                height=80,
            )

        invoice_configs.append(
            {
                "selected": selected,
                "client_name": client_name,
                "client_nif": client_nif,
                "reference": reference,
                "description": description,
                "unit": unit,
                "amount": amount,
                "invoice_date": inv_date,
            }
        )

# Apply a pending removal (after the loop so widget state stays consistent).
if remove_invoice_id is not None:
    st.session_state.eva_invoices = [
        inv for inv in st.session_state.eva_invoices if inv["id"] != remove_invoice_id
    ]
    st.rerun()

if st.button("➕ Add invoice"):
    st.session_state.eva_invoices.append(
        _blank_invoice(
            iid=st.session_state.eva_next_invoice_id,
            reference=default_reference,
            invoice_date=default_invoice_date,
        )
    )
    st.session_state.eva_next_invoice_id += 1
    st.rerun()

# ---------------------------------------------------------------------------
# Target total info (Silvia's suggested amount from invoices 1–3)
# ---------------------------------------------------------------------------

fixed_amounts_sum, silvia_suggested = _silvia_amount_hint()
target_total = st.session_state.eva_target_total

st.caption(
    f"Random target total: **{target_total} €** — "
    f"Silvia's suggested amount: **{silvia_suggested:.2f} €** "
    f"({target_total} − {fixed_amounts_sum:.2f})"
)

# ---------------------------------------------------------------------------
# Selection summary
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Summary – invoices to be submitted")

selected_cfgs = [
    (position, cfg) for position, cfg in enumerate(invoice_configs) if cfg["selected"]
]

if not selected_cfgs:
    st.warning("No invoices selected. Tick at least one invoice to submit.")
else:
    summary_lines = [
        f"- **{cfg['client_name'] or '(no name)'}** — {cfg['amount']:.2f} € "
        f"(NIF {cfg['client_nif'] or '—'}, {cfg['invoice_date'].strftime('%d-%m-%Y')})"
        for _, cfg in selected_cfgs
    ]
    st.markdown("\n".join(summary_lines))
    total = sum(cfg["amount"] for _, cfg in selected_cfgs)
    st.markdown(f"**{len(selected_cfgs)} invoice(s) selected — total {total:.2f} €**")

# ---------------------------------------------------------------------------
# Validation and submission
# ---------------------------------------------------------------------------

if st.button("Submit selected invoices", type="primary"):
    errors: list[str] = []
    selected_invoices: list[EvaInvoice] = []

    for position, cfg in enumerate(invoice_configs):
        if not cfg["selected"]:
            continue
        label = f"Invoice {position + 1} ({cfg['client_name'].strip() or 'unnamed'})"
        nif = cfg["client_nif"].strip()
        if len(nif) != 9 or not nif.isdigit():
            errors.append(f"{label}: NIF must be exactly 9 digits (got '{nif}').")
        if cfg["amount"] <= 0:
            errors.append(f"{label}: Amount must be greater than 0.")
        if not cfg["client_name"].strip():
            errors.append(f"{label}: Client name cannot be empty.")
        if not cfg["description"].strip():
            errors.append(f"{label}: Description cannot be empty.")
        if not errors:
            selected_invoices.append(
                EvaInvoice(
                    client_name=cfg["client_name"].strip(),
                    client_nif=nif,
                    reference=cfg["reference"].strip(),
                    description=cfg["description"].strip(),
                    unit=cfg["unit"].strip(),
                    amount=cfg["amount"],
                    invoice_date=cfg["invoice_date"],
                )
            )

    if errors:
        for err in errors:
            st.error(err)
    elif not selected_invoices:
        st.warning("No invoices selected. Tick at least one invoice to submit.")
    else:
        progress_placeholder = st.empty()
        st.info(f"Submitting {len(selected_invoices)} invoice(s)…")
        st.subheader("Results")
        results_container = st.container()

        def _show_invoice_result(invoice: EvaInvoice, result: AutomationResult) -> None:
            with results_container:
                if result.success:
                    st.success(f"**{invoice.client_name}** — {result.message}")
                else:
                    st.error(f"**{invoice.client_name}** — {result.message}")
                if result.screenshot:
                    st.image(
                        result.screenshot,
                        caption=f"Screenshot – {invoice.client_name}",
                    )

        results = issue_eva_invoices(
            callback=lambda msg: progress_placeholder.text(msg),
            invoices=selected_invoices,
            headless=dev_headless(),
            dry_run=dev_dry_run(),
            on_result=_show_invoice_result,
        )

        progress_placeholder.empty()
        succeeded = sum(1 for _, result in results if result.success)
        if succeeded == len(results):
            st.success(f"All {len(results)} invoice(s) submitted successfully.")
        else:
            st.warning(f"Finished: {succeeded}/{len(results)} invoice(s) succeeded.")

render_dev_control_panel()
