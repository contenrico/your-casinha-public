"""
Pure pandas transformation functions.

None of these functions have side effects (no I/O, no Streamlit calls).
They accept and return DataFrames, making them trivially testable.
"""

import re
from datetime import datetime

import pandas as pd

from ..config import S3_KEY_FORM_RESPONSES, S3_BUCKET
from ..domain.columns import (
    CHECKIN_DATE,
    CHECKOUT_DATE,
    COLUMN_NO,
    DATE_OF_BIRTH,
    TIMESTAMP,
)
from .storage import download_bytes


# ---------------------------------------------------------------------------
# SEF / guest data
# ---------------------------------------------------------------------------

def clean_sheet(sheet_name: str = S3_KEY_FORM_RESPONSES) -> pd.DataFrame:
    """
    Download the raw form-responses CSV from S3 and return a tidy DataFrame
    with one row per guest, dates formatted as DD-MM-YYYY.
    """
    import io

    raw = download_bytes(sheet_name)
    df = pd.read_csv(io.BytesIO(raw)).drop(columns=["Unnamed: 0"], errors="ignore")

    melted = pd.melt(df, id_vars=[TIMESTAMP], var_name="Variable", value_name="Value")
    melted["Column_Name"] = melted["Variable"].str.split("_").str[0]
    melted["Column_No"] = melted["Variable"].str.split("_").str[-1]
    melted = melted[melted["Column_Name"] != "Number of guests"]
    melted = melted.drop(columns=["Variable"])

    pivoted = (
        melted.pivot(index=[TIMESTAMP, COLUMN_NO], columns="Column_Name", values="Value")
        .reset_index()
    )
    pivoted.columns.name = None
    pivoted = pivoted.dropna(subset=[CHECKIN_DATE]).reset_index(drop=True)

    for col, fmt in [(CHECKIN_DATE, "%m/%d/%Y"), (CHECKOUT_DATE, "%m/%d/%Y"), (DATE_OF_BIRTH, "%m/%d/%Y")]:
        pivoted[col] = pd.to_datetime(pivoted[col], format=fmt, errors="raise")

    pivoted = pivoted.sort_values(CHECKIN_DATE)

    for col in (CHECKIN_DATE, CHECKOUT_DATE, DATE_OF_BIRTH):
        pivoted[col] = pivoted[col].dt.strftime("%d-%m-%Y")

    pivoted = pivoted.fillna("").reset_index(drop=True)
    return pivoted


def filter_on_checkin_date(df: pd.DataFrame, date: str | None = None) -> pd.DataFrame:
    """Return rows whose check-in date matches *date* (DD-MM-YYYY). Defaults to today."""
    if not date:
        date = datetime.today().strftime("%d-%m-%Y")
    return df[df[CHECKIN_DATE] == date].sort_values(COLUMN_NO)


def filter_on_checkout_date(df: pd.DataFrame, date: str | None = None) -> pd.DataFrame:
    """Return rows whose check-out date matches *date* (DD-MM-YYYY). Defaults to today."""
    if not date:
        date = datetime.today().strftime("%d-%m-%Y")
    return df[df[CHECKOUT_DATE] == date]


def filter_on_name(
    df: pd.DataFrame,
    first_name: str = "",
    last_name: str = "",
) -> pd.DataFrame:
    """Filter by first name, last name, or both."""
    from ..domain.columns import FIRST_NAME, LAST_NAME

    if first_name and last_name:
        return df[(df[FIRST_NAME] == first_name) & (df[LAST_NAME] == last_name)]
    if first_name:
        return df[df[FIRST_NAME] == first_name]
    if last_name:
        return df[df[LAST_NAME] == last_name]
    return df


# ---------------------------------------------------------------------------
# Payout / invoice data
# ---------------------------------------------------------------------------

def parse_payout_emails(messages: list[dict]) -> pd.DataFrame:
    """
    Filter Airbnb payout messages and return a DataFrame with columns
    ['Date', 'Payout Amount'] sorted by date ascending.
    """
    airbnb_payouts = [
        m for m in messages
        if "sent" in m["Subject"].lower()
        and "payout" in m["Subject"].lower()
        and "airbnb" in m["From"].lower()
    ]

    dates, amounts = [], []
    for msg in airbnb_payouts:
        match = re.search(r"[\u20ac$£]\s?[,\d]+\.?\d*", msg["Subject"])
        amount = (
            match.group(0)
            .replace(",", "")
            .replace("\u20ac", "")
            .replace("$", "")
            .replace("£", "")
            .strip()
            if match
            else None
        )
        date = pd.to_datetime(
            datetime.strptime(msg["Date"], "%Y-%m-%dT%H:%M:%S").strftime("%d-%m-%Y"),
            format="%d-%m-%Y",
        )
        dates.append(date)
        amounts.append(amount)

    df = pd.DataFrame({"Date": dates, "Payout Amount": amounts})
    df = df.sort_values("Date")
    df["Date"] = df["Date"].dt.strftime("%d-%m-%Y")
    return df


def get_first_payout_before_date(
    payout_df: pd.DataFrame,
    cutoff: str | datetime | None = None,
) -> tuple[str, str]:
    """
    Return (payout_amount, payout_date) for the most recent payout on or before
    *cutoff*.  Returns ('No payout found.', 'No payout found.') when none exists.
    """
    if cutoff is None:
        cutoff = datetime.today().date()
    elif isinstance(cutoff, str):
        cutoff = pd.to_datetime(cutoff, dayfirst=True).date()

    df = payout_df.copy()
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True).dt.date
    df = df.sort_values("Date")
    filtered = df[df["Date"] <= cutoff]

    if filtered.empty:
        return "No payout found.", "No payout found."
    return str(filtered["Payout Amount"].iloc[-1]), str(filtered["Date"].iloc[-1])
