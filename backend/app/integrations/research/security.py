"""SSRF / URL safety controls for the Phase 7B page reader."""
from __future__ import annotations

import ipaddress
import socket
from typing import FrozenSet, Iterable, Optional, Sequence, Tuple
from urllib.parse import urlparse, urlunparse


DEFAULT_ALLOWED_SCHEMES = frozenset({"http", "https"})
DEFAULT_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
        "metadata",
        "instance-data",
    }
)
DEFAULT_BLOCKED_HOST_SUFFIXES = (".localhost", ".local", ".internal")
DEFAULT_MAX_REDIRECTS = 5
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_BYTES = 2_000_000  # 2 MB
DEFAULT_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "text/html",
        "application/xhtml+xml",
        "text/plain",
        "application/xml",
        "text/xml",
    }
)
DEFAULT_USER_AGENT = (
    "SaudiBusinessBot/7B (+https://saudi-business.local; governed source research; "
    "contact=ops@saudi-business.local)"
)


class UrlSecurityError(ValueError):
    """Raised when a URL fails SSRF / allowlist checks."""


def canonicalize_url(url: str) -> str:
    """Normalize scheme/host/path for cache keys (strip fragment, lowercase host)."""
    raw = (url or "").strip()
    if not raw:
        raise UrlSecurityError("empty URL")
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        raise UrlSecurityError("URL must include scheme and host")
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise UrlSecurityError("missing host")
    port = parsed.port
    netloc = f"{host}:{port}" if port else host
    path = parsed.path or "/"
    return urlunparse((scheme, netloc, path, "", parsed.query, ""))


def _is_private_ip(ip: ipaddress._BaseAddress) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def resolve_host_ips(hostname: str) -> Tuple[str, ...]:
    infos = socket.getaddrinfo(hostname, None)
    return tuple(sorted({info[4][0] for info in infos}))


def validate_url(
    url: str,
    *,
    allowed_schemes: FrozenSet[str] = DEFAULT_ALLOWED_SCHEMES,
    allowed_domains: Optional[Sequence[str]] = None,
    resolve_dns: bool = True,
) -> str:
    """Validate URL for fetching. Returns canonical URL on success."""
    canonical = canonicalize_url(url)
    parsed = urlparse(canonical)
    scheme = parsed.scheme.lower()
    if scheme not in allowed_schemes:
        raise UrlSecurityError(f"scheme not allowed: {scheme}")

    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise UrlSecurityError("missing host")
    if "@" in parsed.netloc:
        raise UrlSecurityError("userinfo not allowed in URL")
    if host in DEFAULT_BLOCKED_HOSTS or any(
        host.endswith(s) for s in DEFAULT_BLOCKED_HOST_SUFFIXES
    ):
        raise UrlSecurityError(f"blocked host: {host}")

    try:
        ip = ipaddress.ip_address(host)
        if _is_private_ip(ip):
            raise UrlSecurityError(f"private/reserved IP blocked: {host}")
    except ValueError:
        pass

    if allowed_domains:
        allow = [d.lower().rstrip(".") for d in allowed_domains]
        if not any(host == d or host.endswith("." + d) for d in allow):
            raise UrlSecurityError(f"host not in allowlist: {host}")

    if resolve_dns:
        try:
            ips = resolve_host_ips(host)
        except socket.gaierror as exc:
            raise UrlSecurityError(f"DNS resolution failed for {host}") from exc
        for addr in ips:
            if _is_private_ip(ipaddress.ip_address(addr)):
                raise UrlSecurityError(f"host resolves to private/reserved IP: {addr}")

    return canonical


def content_type_allowed(
    content_type: Optional[str],
    *,
    allowed: Iterable[str] = DEFAULT_ALLOWED_CONTENT_TYPES,
) -> bool:
    if not content_type:
        return False
    base = content_type.split(";", 1)[0].strip().lower()
    return base in {a.lower() for a in allowed}
