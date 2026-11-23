"""
File storage for uploaded invoices and warranty cards.

Supports two backends transparently:
  1. Cloud S3-compatible object storage (Cloudflare R2, Supabase Storage S3,
     AWS S3) via pure-stdlib AWS SigV4 signing + httpx — no heavy SDK needed.
     Stored references look like ``s3://invoices/<uuid>_bill.pdf`` and downloads
     use short-lived pre-signed URLs (never public).
  2. Local disk fallback under ``UPLOAD_DIR`` (default ``uploads/``) when cloud
     variables are unset.

Multi-file refs stored as ``ref1 | ref2`` are handled cleanly everywhere.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urlparse

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(25.0, connect=10.0)


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _upload_dir() -> Path:
    return Path(_env("UPLOAD_DIR") or "uploads")


def is_cloud_storage_configured() -> bool:
    return bool(
        _env("STORAGE_ENDPOINT_URL")
        and _env("STORAGE_BUCKET")
        and _env("STORAGE_ACCESS_KEY_ID")
        and _env("STORAGE_SECRET_ACCESS_KEY")
    )


def _sanitise_name(filename: str) -> str:
    name = Path(filename or "upload").name
    name = re.sub(r"[^\w.\-]", "_", name)
    return name[:160]


# ── AWS SigV4 helpers (pure stdlib) ──────────────────────────────────────────

def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(secret: str, date_stamp: str, region: str, service: str = "s3") -> bytes:
    k_date = _hmac_sha256(("AWS4" + secret).encode("utf-8"), date_stamp)
    k_region = _hmac_sha256(k_date, region)
    k_service = _hmac_sha256(k_region, service)
    return _hmac_sha256(k_service, "aws4_request")


def _object_url(key: str) -> tuple[str, str, str]:
    endpoint = _env("STORAGE_ENDPOINT_URL").rstrip("/")
    bucket = _env("STORAGE_BUCKET").strip("/")
    clean_key = key.lstrip("/")
    parsed = urlparse(endpoint)
    base_path = parsed.path.rstrip("/")
    uri_path = quote(f"{base_path}/{bucket}/{clean_key}", safe="/~-_.")
    return f"{parsed.scheme}://{parsed.netloc}{uri_path}", parsed.netloc, uri_path


def _sign_headers(
    method: str,
    host: str,
    uri_path: str,
    payload: bytes = b"",
    content_type: Optional[str] = None,
    now: Optional[datetime] = None,
) -> dict[str, str]:
    dt = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    amz_date = dt.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = dt.strftime("%Y%m%d")
    region = _env("STORAGE_REGION") or "auto"
    access_key = _env("STORAGE_ACCESS_KEY_ID")
    secret_key = _env("STORAGE_SECRET_ACCESS_KEY")

    payload_hash = hashlib.sha256(payload).hexdigest()
    hdrs = {
        "host": host,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
    }
    if content_type:
        hdrs["content-type"] = content_type

    sorted_keys = sorted(hdrs.keys())
    canonical_headers = "".join(f"{k}:{hdrs[k]}\n" for k in sorted_keys)
    signed_headers = ";".join(sorted_keys)
    canonical_request = "\n".join(
        [method.upper(), uri_path, "", canonical_headers, signed_headers, payload_hash]
    )
    scope = f"{date_stamp}/{region}/s3/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    signature = hmac.new(
        _signing_key(secret_key, date_stamp, region),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    out = {
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
        "Authorization": (
            f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        ),
    }
    if content_type:
        out["Content-Type"] = content_type
    return out


def presign_get_url(
    key: str,
    expires_in: int = 300,
    now: Optional[datetime] = None,
) -> str:
    """Return a short-lived SigV4 pre-signed GET URL for ``key``."""
    clean_key = key[5:] if key.startswith("s3://") else key
    full_url, host, uri_path = _object_url(clean_key)
    dt = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    amz_date = dt.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = dt.strftime("%Y%m%d")
    region = _env("STORAGE_REGION") or "auto"
    access_key = _env("STORAGE_ACCESS_KEY_ID")
    secret_key = _env("STORAGE_SECRET_ACCESS_KEY")
    scope = f"{date_stamp}/{region}/s3/aws4_request"

    params = [
        ("X-Amz-Algorithm", "AWS4-HMAC-SHA256"),
        ("X-Amz-Credential", quote(f"{access_key}/{scope}", safe="")),
        ("X-Amz-Date", amz_date),
        ("X-Amz-Expires", str(expires_in)),
        ("X-Amz-SignedHeaders", "host"),
    ]
    canonical_query = "&".join(f"{k}={v}" for k, v in sorted(params))
    canonical_request = "\n".join(
        ["GET", uri_path, canonical_query, f"host:{host}\n", "host", "UNSIGNED-PAYLOAD"]
    )
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    signature = hmac.new(
        _signing_key(secret_key, date_stamp, region),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{full_url}?{canonical_query}&X-Amz-Signature={signature}"


# ── Public operations ────────────────────────────────────────────────────────

def save_file(
    data: bytes,
    filename: str,
    content_type: str = "application/octet-stream",
    http: Optional[httpx.Client] = None,
) -> str:
    """Persist bytes to cloud object storage (if configured) or local disk."""
    safe_name = _sanitise_name(filename)
    unique = f"{uuid.uuid4().hex}_{safe_name}"

    if is_cloud_storage_configured():
        key = f"invoices/{unique}"
        url, host, uri_path = _object_url(key)
        headers = _sign_headers(
            "PUT",
            host,
            uri_path,
            payload=data,
            content_type=content_type or "application/octet-stream",
        )
        client = http or httpx.Client(timeout=_TIMEOUT)
        try:
            resp = client.put(url, content=data, headers=headers)
            resp.raise_for_status()
            logger.info("Uploaded %d bytes to object storage: %s", len(data), key)
            return f"s3://{key}"
        finally:
            if http is None:
                client.close()

    upload_dir = _upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_path = upload_dir / unique
    save_path.write_bytes(data)
    logger.info("Saved local upload: %s (%d bytes)", save_path, len(data))
    return str(save_path)


def _split_refs(file_ref: Optional[str]) -> list[str]:
    if not file_ref:
        return []
    return [part.strip() for part in str(file_ref).split("|") if part.strip()]


def delete_file(file_ref: Optional[str], http: Optional[httpx.Client] = None) -> None:
    """Best-effort deletion for both ``s3://`` cloud objects and local files."""
    for ref in _split_refs(file_ref):
        try:
            if ref.startswith("s3://"):
                if not is_cloud_storage_configured():
                    continue
                key = ref[5:]
                url, host, uri_path = _object_url(key)
                headers = _sign_headers("DELETE", host, uri_path)
                client = http or httpx.Client(timeout=_TIMEOUT)
                try:
                    resp = client.delete(url, headers=headers)
                    if resp.status_code not in (200, 204, 404):
                        logger.warning("Cloud storage DELETE %s returned %s", key, resp.status_code)
                finally:
                    if http is None:
                        client.close()
            else:
                path = Path(ref)
                if path.is_file():
                    path.unlink()
        except Exception as exc:  # noqa: BLE001 - deletion must never block DB cleanup
            logger.warning("Could not delete stored file %r: %s", ref, exc)


def get_download_url(file_ref: Optional[str], expires_in: int = 300) -> Optional[str]:
    """Return a pre-signed download URL for the primary stored cloud file, if any."""
    if not is_cloud_storage_configured():
        return None
    for ref in _split_refs(file_ref):
        if ref.startswith("s3://"):
            return presign_get_url(ref, expires_in=expires_in)
    return None


def resolve_local_file(file_ref: Optional[str]) -> Optional[Path]:
    """Return the first existing local upload file strictly inside UPLOAD_DIR."""
    upload_root = _upload_dir().resolve()
    for ref in _split_refs(file_ref):
        if ref.startswith("s3://"):
            continue
        try:
            candidate = Path(ref).resolve()
        except OSError:
            continue
        if candidate.is_relative_to(upload_root) and candidate.is_file():
            return candidate
    return None

