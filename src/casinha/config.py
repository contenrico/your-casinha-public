"""
Central configuration module.

All constants and credential lookups live here.  Pages and services
import from this module rather than hard-coding values inline.

Secrets are read from the .env file / environment variables first, with
st.secrets as a fallback when deployed on Streamlit Cloud.
"""

import json
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the repo root (two levels up from this file: src/casinha/config.py)
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# ---------------------------------------------------------------------------
# Helpers: secret resolution
# ---------------------------------------------------------------------------

def _secret(key: str, *, section: str | None = None) -> str:
    """
    Return a secret value.

    Lookup order:
    1. os.environ[key]  — covers .env loaded above and any exported env vars
    2. st.secrets[key]  — fallback for Streamlit Cloud deployments

    Raises KeyError if the value is not found anywhere.
    """
    value = os.environ.get(key)
    if value is not None:
        return value

    try:
        import streamlit as st  # noqa: PLC0415

        if section:
            return st.secrets[section][key]
        return st.secrets[key]
    except Exception:
        pass

    raise KeyError(
        f"Secret '{key}' not found in environment variables or st.secrets. "
        "Add it to the .env file (local) or Streamlit Cloud secrets."
    )


# ---------------------------------------------------------------------------
# AWS / S3
# ---------------------------------------------------------------------------

S3_BUCKET = "your-casinha"

# ---------------------------------------------------------------------------
# Google APIs
# ---------------------------------------------------------------------------

SPREADSHEET_ID = "1XNzUH6ydpDt0apgL-a7wuxgxNgRRKMsNwKPpJ74ejbk"
SPREADSHEET_RANGE = "Form Responses 1!A1:BP10000"

SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SCOPES_GMAIL = ["https://www.googleapis.com/auth/gmail.readonly"]

S3_CREDS_SHEET = "credentials_sheet.json"
S3_CREDS_GMAIL = "credentials_gmail.json"
S3_TOKEN_GMAIL = "gmail_token.pickle"
S3_TOKEN_SHEET = "sheet_token.json"

S3_KEY_FORM_RESPONSES = "form_responses.csv"
S3_KEY_EMAILS = "emails.json"
S3_KEY_RECORDS = "records.json"

# ---------------------------------------------------------------------------
# SEF / SIBA portal
# ---------------------------------------------------------------------------

SEF_URL = "https://siba.ssi.gov.pt/s/FB.aspx?ReturnUrl=%2fs%2fau%2fDefault.aspx"

def sef_uh() -> str:
    return _secret("SEF_UH")

def sef_estabelecimento() -> str:
    return _secret("SEF_ESTABELECIMENTO")

def sef_chave() -> str:
    return _secret("SEF_CHAVE")

# ---------------------------------------------------------------------------
# Portuguese tax portal (IRS / invoices)
# ---------------------------------------------------------------------------

INVOICE_URL = "https://irs.portaldasfinancas.gov.pt/recibos/portal/emitir/emitirfaturaV2"
VAT_RATE = 0.06
AL_NUMBER = "138454/AL"
AL_ADDRESS = "RUA DE MARVILA N 54 R/C E 1950-199 LISBOA"

def pdf_nif() -> str:
    return _secret("PDF_NIF")

def pdf_senha() -> str:
    return _secret("PDF_SENHA")

def eva_nif() -> str:
    return _secret("EVA_NIF")

def eva_senha() -> str:
    return _secret("EVA_SENHA")

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def app_password() -> str:
    return _secret("password")

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def environment() -> str:
    """Return the current environment ("dev"/"prod"), defaulting to "prod"."""
    try:
        return _secret("ENVIRONMENT").strip().lower()
    except KeyError:
        return "prod"

# ---------------------------------------------------------------------------
# Parameter file loader (countries / nationalities mappings)
# ---------------------------------------------------------------------------

_PARAMS_DIR = Path(__file__).parent.parent.parent / "parameters"


@lru_cache(maxsize=None)
def countries_mapping() -> dict[str, str]:
    with open(_PARAMS_DIR / "countries_mapping.json", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=None)
def nationalities_mapping() -> dict[str, str]:
    with open(_PARAMS_DIR / "nationalities_mapping.json", encoding="utf-8") as fh:
        return json.load(fh)
