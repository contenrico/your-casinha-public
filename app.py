"""
Entry point for the Your Casinha admin dashboard.

Run with:
    streamlit run app.py
"""

import streamlit as st

from src.casinha.auth import check_password

st.set_page_config(
    page_title="Your Casinha",
    page_icon="🏠",
    layout="centered",
)

if not check_password():
    st.stop()

# Auth passed – define the app pages.
home_page = st.Page("app_pages/home.py", title="Home", icon="🏠", default=True)
register_page = st.Page("app_pages/register_guests.py", title="Register Guests", icon="🌍")
invoices_page = st.Page("app_pages/issue_invoices.py", title="Issue Invoices", icon="📈")

nav = st.navigation([home_page, register_page, invoices_page])
nav.run()
