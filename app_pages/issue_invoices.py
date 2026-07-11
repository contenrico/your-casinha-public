"""Issue Invoices page – thin Streamlit UI layer."""

import json

import pandas as pd
import streamlit as st

from app_pages.dev_controls import dev_dry_run, dev_headless, init_dev_controls, render_dev_control_panel
from src.casinha.automation.invoices import fill_in_invoice
from src.casinha.config import countries_mapping
from src.casinha.domain.columns import (
    CHECKIN_DATE,
    CHECKOUT_DATE,
    COUNTRY_OF_RESIDENCE,
    FIRST_NAME,
    INVOICE_DISPLAY_COLS,
    LAST_NAME,
    PASSPORT_NUMBER,
)
from src.casinha.services.gmail import get_emails
from src.casinha.services.records import get_latest
from src.casinha.services.storage import download_bytes, object_exists
from src.casinha.services.transforms import (
    filter_on_checkout_date,
    get_first_payout_before_date,
    parse_payout_emails,
)
from src.casinha.config import S3_KEY_EMAILS

st.title("Issue New Invoices")

init_dev_controls()

# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------

for key, default in [
    ("payout_df", pd.DataFrame()),
    ("clean_df", pd.DataFrame()),
    ("invoice_df", pd.DataFrame()),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------------------------------------------------------------------
# Step 1 – payout lookup
# ---------------------------------------------------------------------------


def populate_guest_details(checkout: str) -> None:
    """Fill invoice_df from clean_df for the given check-out date string."""
    st.session_state.invoice_df = pd.DataFrame()
    if not st.session_state.clean_df.empty:
        filtered = filter_on_checkout_date(st.session_state.clean_df, checkout)
        if not filtered.empty:
            st.session_state.invoice_df = filtered[INVOICE_DISPLAY_COLS].head(1)
    # Clear stale editor deltas so fresh data is shown cleanly.
    st.session_state.pop("invoice_editor", None)


checkout_date = st.date_input(
    "Check-out date:", value=pd.to_datetime("today"), format="DD-MM-YYYY", key="checkout_date_filter"
)
checkout_date_str = checkout_date.strftime("%d-%m-%Y")

if st.button("Get payout amounts"):
    with st.spinner("Fetching emails and guest records..."):
        try:
            latest = get_latest()
            st.session_state.clean_df = latest if latest is not None else pd.DataFrame()
            get_emails()
            emails_raw = json.loads(download_bytes(S3_KEY_EMAILS))
            st.session_state.payout_df = parse_payout_emails(emails_raw)
            # Also populate the guest detail fields below off the same date.
            populate_guest_details(checkout_date_str)
        except Exception as exc:
            st.error(f"Failed to fetch payout data: {exc}")

st.dataframe(st.session_state.payout_df, hide_index=True, use_container_width=True)

invoice_amount: float | None = None
if not st.session_state.payout_df.empty:
    raw_amount, _ = get_first_payout_before_date(
        st.session_state.payout_df.copy(), checkout_date_str
    )
    if raw_amount == "No payout found.":
        st.error("No payout found for this date.")
    else:
        invoice_amount = st.number_input(
            "Invoice amount based on selected check-out date:",
            value=float(raw_amount),
        )

# ---------------------------------------------------------------------------
# Step 2 – guest detail lookup / overwrite
# ---------------------------------------------------------------------------

if st.button("Fetch guest details"):
    populate_guest_details(checkout_date_str)

countries = countries_mapping()
countries_list = list(countries.keys())

inv = st.session_state.invoice_df

st.subheader("Details on the invoice:")

first_name = st.text_input(
    "First name:", value=inv[FIRST_NAME].values[0] if not inv.empty else ""
)
last_name = st.text_input(
    "Last name:", value=inv[LAST_NAME].values[0] if not inv.empty else ""
)
checkin_input = st.date_input(
    "Check-in date:",
    format="DD-MM-YYYY",
    value=pd.to_datetime(inv[CHECKIN_DATE].values[0], dayfirst=True) if not inv.empty else pd.to_datetime("today"),
    key="checkin_date_detail",
)
checkout_input = st.date_input(
    "Check-out date:",
    format="DD-MM-YYYY",
    value=pd.to_datetime(inv[CHECKOUT_DATE].values[0], dayfirst=True) if not inv.empty else pd.to_datetime("today"),
    key="checkout_date_detail",
)
invoice_date = st.date_input(
    "Invoice date:",
    format="DD-MM-YYYY",
    value=pd.to_datetime(checkout_date_str, dayfirst=True),
    key="invoice_date_detail",
)
passport = st.text_input(
    "Passport number:", value=inv[PASSPORT_NUMBER].values[0] if not inv.empty else ""
)
default_country_idx = (
    countries_list.index(inv[COUNTRY_OF_RESIDENCE].values[0])
    if not inv.empty and inv[COUNTRY_OF_RESIDENCE].values[0] in countries_list
    else 0
)
country = st.selectbox("Country of residence:", countries_list, index=default_country_idx)
nif: str | None = None
if country == "Portugal":
    nif = st.text_input("NIF:")

if st.button("Overwrite details"):
    st.session_state.invoice_df = pd.DataFrame(
        [
            {
                FIRST_NAME: first_name,
                LAST_NAME: last_name,
                CHECKIN_DATE: checkin_input.strftime("%d-%m-%Y"),
                CHECKOUT_DATE: checkout_input.strftime("%d-%m-%Y"),
                PASSPORT_NUMBER: passport,
                COUNTRY_OF_RESIDENCE: country,
            }
        ]
    )
    # Clear stale editor deltas so the overwritten data is shown cleanly.
    st.session_state.pop("invoice_editor", None)

# Transposed: field names become rows, guest values become a single column ("Guest 1").
# The base DataFrame is kept stable; edits are captured in a local variable.
_invoice_display = st.session_state.invoice_df.reset_index(drop=True).T.rename(
    columns=lambda i: f"Guest {i + 1}"
)
edited_invoice_df = st.data_editor(
    _invoice_display,
    use_container_width=True,
    height=38 + len(_invoice_display) * 35,
    key="invoice_editor",
).T.reset_index(drop=True)

# ---------------------------------------------------------------------------
# Step 3 – issue invoice
# ---------------------------------------------------------------------------

if st.button("Issue invoice", type="primary"):
    if invoice_amount is None:
        st.error("Please fetch payout amounts before issuing an invoice.")
    elif edited_invoice_df.empty:
        st.warning("No guest details available. Please fetch or enter guest details.")
    elif country == "Portugal" and nif and len(nif) not in (0, 9):
        st.error("Please enter a valid NIF (9 digits) or leave blank.")
    else:
        progress_placeholder = st.empty()
        result = fill_in_invoice(
            callback=lambda msg: progress_placeholder.text(msg),
            guest_df=edited_invoice_df,
            amount=invoice_amount,
            invoice_date=invoice_date,
            invoice_nif=nif or None,
            headless=dev_headless(),
            dry_run=dev_dry_run(),
        )

        if result.screenshot:
            st.image(result.screenshot, caption="Screenshot of the Invoice Submission")

        if result.success:
            st.success(result.message)
        else:
            st.error(result.message)

render_dev_control_panel()
