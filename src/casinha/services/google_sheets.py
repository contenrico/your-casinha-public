"""Google Sheets service: fetches guest form responses and saves them to S3."""

import json
from io import StringIO

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config import (
    S3_CREDS_SHEET,
    S3_KEY_FORM_RESPONSES,
    SCOPES_SHEETS,
    SPREADSHEET_ID,
    SPREADSHEET_RANGE,
    S3_BUCKET,
)
from .storage import download_bytes, object_exists, upload_bytes


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_unique_columns(raw_columns: list[str]) -> list[str]:
    """Append _{n} suffix to duplicate column names (mirrors the original logic)."""
    seen: dict[str, int] = {}
    result = []
    for col in raw_columns:
        seen[col] = seen.get(col, 0) + 1
        result.append(f"{col}_{seen[col]}")
    return result


def _sheet_values_to_csv(values: list[list]) -> str:
    """Convert raw Sheets API values to a CSV string with de-duped column names."""
    unique_cols = _make_unique_columns(values[0])
    df = pd.DataFrame(values[1:], columns=unique_cols)
    buf = StringIO()
    df.to_csv(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_form(
    creds_name: str = S3_CREDS_SHEET,
    sheet_name: str = S3_KEY_FORM_RESPONSES,
) -> str:
    """
    Fetch the guest form spreadsheet using a service-account credential stored
    in S3, convert it to CSV, upload the result to S3, and return the S3 URI.

    Raises:
        Exception: if the credentials file is missing from S3.
        HttpError: if the Sheets API call fails.
    """
    if not object_exists(creds_name):
        raise Exception(f"{creds_name} does not exist in S3 bucket '{S3_BUCKET}'.")

    creds_data = json.loads(download_bytes(creds_name))
    creds = service_account.Credentials.from_service_account_info(
        creds_data, scopes=SCOPES_SHEETS
    )

    try:
        service = build("sheets", "v4", credentials=creds)
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=SPREADSHEET_RANGE)
            .execute()
        )
    except HttpError as err:
        raise RuntimeError(f"Sheets API error: {err}") from err

    values = result.get("values", [])
    if not values:
        raise RuntimeError("No data returned from the spreadsheet.")

    csv_content = _sheet_values_to_csv(values)
    upload_bytes(sheet_name, csv_content)

    return f"s3://{S3_BUCKET}/{sheet_name}"
