from __future__ import annotations

import json

_SIGNATURES: dict[str, bytes] = {
    "application/pdf": b"%PDF-",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8\xff",
}


def normalize_content_type(value: str) -> str:
    """Drop parameters such as charset and compare types in lowercase."""
    return value.split(";", 1)[0].strip().lower()


def content_matches_type(content_type: str, data: bytes) -> bool:
    """True when the bytes match the declared allow-listed type."""
    signature = _SIGNATURES.get(content_type)
    if signature is not None:
        return data.startswith(signature)
    if content_type == "text/plain":
        return b"\x00" not in data and _is_utf8(data)
    if content_type == "application/json":
        if b"\x00" in data or not _is_utf8(data):
            return False
        try:
            json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            return False
        return True
    return False


def _is_utf8(data: bytes) -> bool:
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True
