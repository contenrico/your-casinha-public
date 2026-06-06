"""
Guest records store: reads and writes the cumulative records.json in S3.

The file is a JSON array of dicts, each with keys:
  - "incr": list of records added in that batch (incremental)
  - "cum":  cumulative list of all records up to that batch
"""

import json

import pandas as pd

from ..config import S3_BUCKET, S3_KEY_RECORDS
from .storage import download_bytes, object_exists, upload_bytes


def get_latest(records_key: str = S3_KEY_RECORDS) -> pd.DataFrame | None:
    """Return the most recent cumulative guest DataFrame, or None if not found."""
    if not object_exists(records_key):
        return None

    records = json.loads(download_bytes(records_key))
    return pd.DataFrame(records[-1]["cum"])


def append_records(new_df: pd.DataFrame, records_key: str = S3_KEY_RECORDS) -> None:
    """
    Append *new_df* to the cumulative records stored in S3.

    Raises:
        FileNotFoundError: if records.json does not exist in S3.
    """
    if not object_exists(records_key):
        raise FileNotFoundError(
            f"'{records_key}' not found in S3 bucket '{S3_BUCKET}'. "
            "Create the file before writing records."
        )

    records = json.loads(download_bytes(records_key))
    previous_cum = pd.DataFrame(records[-1]["cum"])
    cumulative = pd.concat([previous_cum, new_df]).drop_duplicates().reset_index(drop=True)

    records.append(
        {
            "incr": new_df.to_dict("records"),
            "cum": cumulative.to_dict("records"),
        }
    )
    upload_bytes(records_key, json.dumps(records))
