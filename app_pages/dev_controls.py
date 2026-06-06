"""Shared dev-mode controls for automation pages."""

from __future__ import annotations

import streamlit as st

from src.casinha.config import environment


def is_dev_mode() -> bool:
    return environment() == "dev"


def init_dev_controls() -> None:
    """Set dev checkbox defaults on first load (both ticked)."""
    if not is_dev_mode():
        return
    st.session_state.setdefault("dev_disable_headless", True)
    st.session_state.setdefault("dev_dry_run", True)


def dev_headless() -> bool:
    """Return headless flag for automation (False in dev when browser visible)."""
    if not is_dev_mode():
        return True
    init_dev_controls()
    return not st.session_state.dev_disable_headless


def dev_dry_run() -> bool:
    """Return dry-run flag for automation."""
    if not is_dev_mode():
        return False
    init_dev_controls()
    return st.session_state.dev_dry_run


def render_dev_control_panel() -> None:
    if not is_dev_mode():
        return
    init_dev_controls()
    with st.expander("🛠️ Dev control panel", expanded=True):
        st.checkbox(
            "Disable headless mode (show the browser window)",
            key="dev_disable_headless",
        )
        st.checkbox(
            "Dry run: fill the form but skip final submit (pause 5 min instead)",
            key="dev_dry_run",
        )
