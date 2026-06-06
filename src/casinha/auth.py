"""Authentication helpers for the Streamlit app."""

import hmac

import streamlit as st

from .config import app_password


def check_password() -> bool:
    """
    Render a password input and return True once the correct password is entered.

    The result is persisted in st.session_state["password_correct"] so that
    subsequent reruns (e.g. page navigation) do not re-prompt.
    """

    def _verify():
        if hmac.compare_digest(st.session_state["password"], app_password()):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input("Password", type="password", on_change=_verify, key="password")
    if "password_correct" in st.session_state:
        st.error("Incorrect password.")
    return False


def require_auth() -> None:
    """
    Stop execution with an error message if the user is not authenticated.

    Call this at the top of any page that should be protected.  With
    st.navigation the auth gate in app.py already prevents unauthenticated
    users from reaching pages, but this acts as an explicit guard in case
    a page is imported directly during development.
    """
    if not st.session_state.get("password_correct", False):
        st.error("Please enter your password on the Home page.")
        st.stop()
