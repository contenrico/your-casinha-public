"""Register Guests page – thin Streamlit UI layer."""

import pandas as pd
import streamlit as st

from src.casinha.automation.sef import fill_in_sef_form
from src.casinha.domain.columns import SEF_DISPLAY_COLS
from src.casinha.services.google_sheets import get_form
from src.casinha.services.records import append_records
from src.casinha.services.transforms import (
    clean_sheet,
    filter_on_checkin_date,
    filter_on_name,
)

st.title("Register New Guests")

# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------

if "sef_df" not in st.session_state:
    st.session_state.sef_df = pd.DataFrame()

# ---------------------------------------------------------------------------
# Step 1 – fetch & filter guest data
# ---------------------------------------------------------------------------

search_by_name = st.checkbox("Search by name")

first_name = last_name = ""
if search_by_name:
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("First name:")
    with col2:
        last_name = st.text_input("Last name:")
else:
    checkin_date = st.date_input(
        "Check-in date:", value=pd.to_datetime("today"), format="DD-MM-YYYY"
    )
    checkin_date_str = checkin_date.strftime("%d-%m-%Y")

if st.button("Get form responses"):
    with st.spinner("Fetching data from Google Sheets..."):
        try:
            get_form()
            clean_df = clean_sheet()

            if first_name or last_name:
                filtered = filter_on_name(clean_df, first_name, last_name)
            else:
                filtered = filter_on_checkin_date(clean_df, checkin_date_str)

            st.session_state.sef_df = filtered[SEF_DISPLAY_COLS]
        except Exception as exc:
            st.error(f"Failed to fetch data: {exc}")

st.session_state.sef_df = st.data_editor(
    st.session_state.sef_df, hide_index=True, key="sef_editor"
)

# ---------------------------------------------------------------------------
# Step 2 – register on SEF
# ---------------------------------------------------------------------------

if st.button("Register guests on SEF"):
    if st.session_state.sef_df.empty:
        st.warning("No guests to register. Please fetch form responses first.")
    else:
        progress_placeholder = st.empty()
        result = fill_in_sef_form(
            df=st.session_state.sef_df,
            callback=lambda msg: progress_placeholder.text(msg),
        )

        if result.success:
            try:
                append_records(st.session_state.sef_df)
            except FileNotFoundError as exc:
                st.warning(f"Guests registered but records not saved: {exc}")
            st.success(result.message)
        else:
            st.error(result.message)
