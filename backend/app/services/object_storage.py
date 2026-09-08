"""Private Cloudflare R2 storage for authenticated funding documents."""
from __future__ import annotations

import os
from functools import lru_cache

from fastapi import HTTPException


@lru_cache(maxsize=1)
def _client():
    required = {
        "R2_ACCOUNT_ID": os.getenv("R2_ACCOUNT_ID"),
        "R2_ACCESS_KEY_ID": os.getenv("R2_ACCESS_KEY_ID"),
        "R2_SECRET_ACCESS_KEY": os.getenv("R2_SECRET_ACCESS_KEY"),
        "R2_BUCKET_NAME": os.getenv("R2_BUCKET_NAME"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise HTTPException(503, "Document storage is not configured: " + ", ".join(missing))
    import boto3
    return boto3.client(
        "s3",
        region_name="auto",
        endpoint_url=f"https://{required['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=required["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=required["R2_SECRET_ACCESS_KEY"],
    )


def put_object(key: str, data: bytes, content_type: str) -> None:
    _client().put_object(Bucket=os.environ["R2_BUCKET_NAME"], Key=key, Body=data, ContentType=content_type)


def get_object(key: str) -> tuple[bytes, str]:
    try:
        result = _client().get_object(Bucket=os.environ["R2_BUCKET_NAME"], Key=key)
    except Exception as exc:
        raise HTTPException(502, "Unable to retrieve the stored document") from exc
    return result["Body"].read(), result.get("ContentType") or "application/octet-stream"


def delete_object(key: str) -> None:
    _client().delete_object(Bucket=os.environ["R2_BUCKET_NAME"], Key=key)
