"""
Antar — Stratus Object Storage Service
===========================================
Catalyst Stratus = S3-style object storage (buckets/objects, pre-signed URLs).
NOT a mountable filesystem. Used for: PDF exports (Phase 6), Second Brain .npz
snapshots (Phase 4 consolidation), pre-generated demo artifacts (Phase 7).

API VERIFIED against zcatalyst-sdk==1.0.1:
  app.stratus().bucket(name).put_object(key, body, options)
  app.stratus().bucket(name).get_object(key, options)
  app.stratus().bucket(name).generate_presigned_url(key, url_action='GET'|'PUT', expiry_in_sec)
  app.stratus().head_bucket(name)
"""

from __future__ import annotations

from app.core.catalyst import get_app
from app.core.settings import settings


def _bucket(req=None):
    return get_app(req).stratus().bucket(settings.STRATUS_BUCKET_NAME)


def upload(key: str, body: bytes | str, content_type: str | None = None, req=None):
    """
    Upload an object. `key` is the path within the bucket, e.g. 'reports/SES123.pdf'.
    Returns True / PutObjectRes on success.
    """
    options = {"content_type": content_type} if content_type else None  # [VERIFY] option key name
    return _bucket(req).put_object(key, body, options)


def download(key: str, req=None) -> bytes:
    """Download an object's bytes."""
    return _bucket(req).get_object(key)


def presigned_get_url(key: str, expiry_seconds: int = 3600, req=None) -> str:
    """
    Pre-signed GET URL (so the browser can fetch a private object directly).
    Used to hand a PDF download link back to the chat UI.
    """
    res = _bucket(req).generate_presigned_url(key, url_action="GET", expiry_in_sec=str(expiry_seconds))
    # res is Dict[str, str]; [VERIFY] exact key ('signature' / 'url') on first run.
    return res.get("signature") or res.get("url") or next(iter(res.values()))


def presigned_put_url(key: str, expiry_seconds: int = 3600, req=None) -> str:
    """Pre-signed PUT URL (for direct browser uploads, if ever needed)."""
    res = _bucket(req).generate_presigned_url(key, url_action="PUT", expiry_in_sec=str(expiry_seconds))
    return res.get("signature") or res.get("url") or next(iter(res.values()))


def bucket_exists(req=None) -> bool:
    """Health/setup check — does the configured bucket exist?"""
    return get_app(req).stratus().head_bucket(settings.STRATUS_BUCKET_NAME, throw_err=False)


def round_trip_smoke() -> dict:
    """
    Phase 1, Step 1.8 smoke test: upload → download → presign a tiny object.
    Run from a standalone script once credentials are set. Returns a report dict.
    """
    key = "_smoke/hello.txt"
    payload = b"Antar stratus round-trip ok"
    report = {"bucket": settings.STRATUS_BUCKET_NAME}
    report["exists"] = bucket_exists()
    report["uploaded"] = bool(upload(key, payload, "text/plain"))
    report["downloaded_ok"] = download(key) == payload
    report["presigned_url"] = presigned_get_url(key, 600)
    return report
