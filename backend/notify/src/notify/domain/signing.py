from __future__ import annotations

import hashlib
import hmac


def sign_webhook_body(*, secret: str, event_id: str, timestamp: str, body: bytes) -> str:
    """Standard Webhooks–style HMAC-SHA256 over id.timestamp.body."""
    signed = f"{event_id}.{timestamp}.".encode() + body
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"v1={digest}"


def verify_webhook_signature(
    *,
    secrets: list[str],
    event_id: str,
    timestamp: str,
    body: bytes,
    header: str,
) -> bool:
    """True if header matches any secret (constant-time)."""
    if not header.startswith("v1="):
        return False
    for secret in secrets:
        if not secret:
            continue
        expected = sign_webhook_body(
            secret=secret, event_id=event_id, timestamp=timestamp, body=body
        )
        if hmac.compare_digest(expected, header):
            return True
    return False
