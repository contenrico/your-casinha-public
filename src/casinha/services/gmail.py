"""Gmail service: fetches Airbnb payout emails and saves them to S3."""

import base64
import json
import pickle
import re
from datetime import datetime
from io import StringIO

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ..config import (
    S3_BUCKET,
    S3_CREDS_GMAIL,
    S3_KEY_EMAILS,
    S3_TOKEN_GMAIL,
    SCOPES_GMAIL,
)
from .storage import download_bytes, object_exists, upload_bytes


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_credentials(creds_name: str = S3_CREDS_GMAIL, token_name: str = S3_TOKEN_GMAIL):
    """Load OAuth credentials from S3, refreshing or re-authenticating as needed."""
    if not object_exists(creds_name):
        raise Exception(f"{creds_name} does not exist in S3 bucket '{S3_BUCKET}'.")

    creds = None
    if object_exists(token_name):
        creds = pickle.loads(download_bytes(token_name))

    try:
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                creds_data = json.loads(download_bytes(creds_name))
                flow = InstalledAppFlow.from_client_config(creds_data, SCOPES_GMAIL)
                creds = flow.run_local_server(port=0)
            upload_bytes(token_name, pickle.dumps(creds))
    except RefreshError:
        creds_data = json.loads(download_bytes(creds_name))
        flow = InstalledAppFlow.from_client_config(creds_data, SCOPES_GMAIL)
        creds = flow.run_local_server(port=0)
        upload_bytes(token_name, pickle.dumps(creds))

    return creds


def _get_message_body(msg: dict) -> str | None:
    """Extract plain-text body from a Gmail message dict."""
    if "parts" in msg["payload"]:
        for part in msg["payload"]["parts"]:
            if part["mimeType"] == "text/plain" and "data" in part["body"]:
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_emails(
    emails_name: str = S3_KEY_EMAILS,
) -> str:
    """
    Fetch all Gmail messages, serialise to JSON, upload to S3, and return the
    S3 URI.  If emails were already fetched today, skips the API call.

    Returns:
        S3 URI string.
    """
    update_time_key = f"{emails_name}_update_time.txt"
    today_str = datetime.today().strftime("%Y-%m-%d")

    if object_exists(emails_name) and object_exists(update_time_key):
        cached_date = download_bytes(update_time_key).decode("utf-8")
        if cached_date == today_str:
            return f"s3://{S3_BUCKET}/{emails_name}"

    creds = _load_credentials()
    service = build("gmail", "v1", credentials=creds)
    result = service.users().messages().list(userId="me").execute()

    messages = []
    for msg in result.get("messages", []):
        msg_data = service.users().messages().get(userId="me", id=msg["id"]).execute()
        body = _get_message_body(msg_data)
        if not body:
            continue

        headers = msg_data["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), None)
        sender = next((h["value"] for h in headers if h["name"] == "From"), None)
        date_str = next((h["value"] for h in headers if h["name"] == "Date"), None)

        date_match = re.search(r"\d{1,2} \w{3} \d{4} \d{2}:\d{2}:\d{2}", date_str or "")
        if not date_match:
            continue

        received_date = datetime.strptime(date_match.group(0), "%d %b %Y %H:%M:%S")
        messages.append(
            {
                "Subject": subject,
                "From": sender,
                "Date": received_date.isoformat(),
                "Message": body,
            }
        )

    buf = StringIO()
    json.dump(messages, buf, default=str, indent=2)
    upload_bytes(emails_name, buf.getvalue())
    upload_bytes(update_time_key, today_str)

    return f"s3://{S3_BUCKET}/{emails_name}"
