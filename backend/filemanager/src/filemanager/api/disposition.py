from __future__ import annotations

from urllib.parse import quote

_ASCII_UNSAFE = {'"', "\\"}


def content_disposition(display_name: str) -> str:
    """Attachment header with an ASCII fallback and an RFC 6266 UTF-8 name."""
    ascii_name = "".join(
        ch if 32 <= ord(ch) < 127 and ch not in _ASCII_UNSAFE else "_" for ch in display_name
    )
    ascii_name = ascii_name.strip(" .") or "download"
    encoded = quote(display_name, safe="")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded}"
