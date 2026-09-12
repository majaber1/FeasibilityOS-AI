"""Safe page reader — HTTP/HTML only, no browser runtime.

Patterns inspired by source-first research readers (cache, cleanup, timeouts)
but re-implemented in Python for the FastAPI stack.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

import httpx

from .cache import BoundedTTLCache, CacheEntry, utcnow
from .content_cleaner import clean_html
from .security import (
    DEFAULT_ALLOWED_CONTENT_TYPES,
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_USER_AGENT,
    UrlSecurityError,
    canonicalize_url,
    content_type_allowed,
    validate_url,
)


class PageFetchError(RuntimeError):
    """Raised when a page cannot be fetched safely."""


@dataclass
class PageReadResult:
    requested_url: str
    final_url: str
    status_code: int
    content_type: str
    title: Optional[str]
    text: str
    html: str
    content_hash: str
    retrieved_at: datetime
    published_at_raw: Optional[str]
    from_cache: bool


_GLOBAL_CACHE = BoundedTTLCache(max_entries=128, ttl_seconds=3600)


def get_default_cache() -> BoundedTTLCache:
    return _GLOBAL_CACHE


class SafePageReader:
    """Governed HTTP page reader with SSRF controls + TTL cache."""

    def __init__(
        self,
        *,
        allowed_domains: Optional[Sequence[str]] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_bytes: int = DEFAULT_MAX_BYTES,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        user_agent: str = DEFAULT_USER_AGENT,
        cache: Optional[BoundedTTLCache] = None,
        resolve_dns: bool = True,
    ) -> None:
        self.allowed_domains = list(allowed_domains) if allowed_domains else None
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects
        self.user_agent = user_agent
        self.cache = cache if cache is not None else get_default_cache()
        self.resolve_dns = resolve_dns

    def read(self, url: str, *, use_cache: bool = True) -> PageReadResult:
        canonical = validate_url(
            url,
            allowed_domains=self.allowed_domains,
            resolve_dns=self.resolve_dns,
        )
        if use_cache:
            hit = self.cache.get(canonical)
            if hit is not None:
                return PageReadResult(
                    requested_url=canonical,
                    final_url=hit.final_url,
                    status_code=hit.status_code,
                    content_type=hit.content_type,
                    title=hit.title,
                    text=hit.text,
                    html=hit.html,
                    content_hash=hit.content_hash,
                    retrieved_at=hit.retrieved_at,
                    published_at_raw=hit.published_at_raw,
                    from_cache=True,
                )

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
            "Accept-Language": "en,ar;q=0.8",
        }

        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                follow_redirects=False,
                headers=headers,
            ) as client:
                current = canonical
                response = None
                for _ in range(self.max_redirects + 1):
                    current = validate_url(
                        current,
                        allowed_domains=self.allowed_domains,
                        resolve_dns=self.resolve_dns,
                    )
                    response = client.get(current)
                    if response.status_code in {301, 302, 303, 307, 308}:
                        loc = response.headers.get("location")
                        if not loc:
                            raise PageFetchError("redirect without Location header")
                        current = str(httpx.URL(current).join(loc))
                        continue
                    break
                else:
                    raise PageFetchError("too many redirects")

                assert response is not None
                if response.status_code >= 400:
                    raise PageFetchError(f"HTTP {response.status_code} for {current}")

                ctype = response.headers.get("content-type", "")
                if not content_type_allowed(ctype, allowed=DEFAULT_ALLOWED_CONTENT_TYPES):
                    raise PageFetchError(f"content-type not allowed: {ctype}")

                cl = response.headers.get("content-length")
                if cl is not None:
                    try:
                        if int(cl) > self.max_bytes:
                            raise PageFetchError("content-length exceeds max_bytes")
                    except ValueError:
                        pass

                raw = response.content
                if len(raw) > self.max_bytes:
                    raise PageFetchError("response exceeds max_bytes")
        except UrlSecurityError:
            raise
        except PageFetchError:
            raise
        except httpx.TimeoutException as exc:
            raise PageFetchError(f"timeout fetching {canonical}") from exc
        except httpx.HTTPError as exc:
            raise PageFetchError(f"HTTP error fetching {canonical}: {exc}") from exc

        try:
            html = raw.decode("utf-8")
        except UnicodeDecodeError:
            html = raw.decode("utf-8", errors="replace")

        text, title, published_raw = clean_html(html)
        if not text.strip():
            raise PageFetchError("no extractable text content")

        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        retrieved_at = utcnow()
        final_url = canonicalize_url(str(response.url)) if response is not None else canonical
        final_url = validate_url(
            final_url,
            allowed_domains=self.allowed_domains,
            resolve_dns=self.resolve_dns,
        )

        entry = CacheEntry(
            url=canonical,
            content_hash=content_hash,
            retrieved_at=retrieved_at,
            status_code=response.status_code,
            content_type=ctype.split(";", 1)[0].strip().lower(),
            final_url=final_url,
            title=title,
            text=text,
            html=html,
            published_at_raw=published_raw,
            expires_at_monotonic=time.monotonic() + self.cache.ttl_seconds,
        )
        if use_cache:
            self.cache.set(canonical, entry)

        return PageReadResult(
            requested_url=canonical,
            final_url=final_url,
            status_code=entry.status_code,
            content_type=entry.content_type,
            title=title,
            text=text,
            html=html,
            content_hash=content_hash,
            retrieved_at=retrieved_at,
            published_at_raw=published_raw,
            from_cache=False,
        )
