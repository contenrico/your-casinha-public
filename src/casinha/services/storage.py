"""AWS S3 helpers."""

import boto3

from ..config import S3_BUCKET

s3 = boto3.client("s3")


def object_exists(key: str, bucket: str = S3_BUCKET) -> bool:
    """Return True if *key* exists in *bucket*."""
    response = s3.list_objects_v2(Bucket=bucket, Prefix=key)
    return any(obj["Key"] == key for obj in response.get("Contents", []))


def download_bytes(key: str, bucket: str = S3_BUCKET) -> bytes:
    """Download *key* from *bucket* and return its raw bytes."""
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()


def upload_bytes(key: str, body: bytes | str, bucket: str = S3_BUCKET) -> None:
    """Upload *body* to *key* in *bucket*."""
    s3.put_object(Bucket=bucket, Key=key, Body=body)
