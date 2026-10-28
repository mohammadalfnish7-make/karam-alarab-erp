from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from domain.shared.domain_error import ValidationError

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata.google.com",
    }
)


def validate_webhook_url(url: str, *, allow_http_loopback: bool) -> str:
    """Validate a channel webhook URL; block SSRF targets (OWASP)."""
    raw = (url or "").strip()
    if not raw:
        raise ValidationError(
            "Webhook URL is required.",
            fields={"webhook_url": "Webhook URL is required."},
        )
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValidationError(
            "Webhook URL must include a host.",
            fields={"webhook_url": "Webhook URL must include a host."},
        )
    if host in _BLOCKED_HOSTNAMES and not (
        allow_http_loopback and host == "localhost"
    ):
        if host != "localhost":
            raise ValidationError(
                "Webhook URL host is not allowed.",
                fields={"webhook_url": "Webhook URL host is not allowed."},
            )
    if scheme == "https":
        pass
    elif scheme == "http" and allow_http_loopback:
        pass
    else:
        raise ValidationError(
            "Webhook URL must use https"
            + (" (http allowed for local loopback in non-production)." if allow_http_loopback else ".") ,
            fields={"webhook_url": "Webhook URL scheme is not allowed."},
        )

    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if scheme == "https" else 80))
    except socket.gaierror as exc:
        raise ValidationError(
            "Webhook URL host could not be resolved.",
            fields={"webhook_url": "Webhook URL host could not be resolved."},
        ) from exc

    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if _is_blocked_ip(ip, allow_http_loopback=allow_http_loopback and scheme == "http"):
            raise ValidationError(
                "Webhook URL must not target private or link-local addresses.",
                fields={"webhook_url": "Webhook URL target is not allowed."},
            )
    return raw


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, *, allow_http_loopback: bool) -> bool:
    if allow_http_loopback and ip.is_loopback:
        return False
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )
