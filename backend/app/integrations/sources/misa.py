"""MISA live SourceConnector — official misa.gov.sa pages only.

Reuses Phase 7B SafePageReader / SSRF controls. No undocumented API is assumed.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse

from app.integrations.research.page_reader import PageFetchError, SafePageReader
from app.integrations.research.security import UrlSecurityError, canonicalize_url

from .base import ConnectorHealth, ConnectorStatus, SourceConnector
from .schemas import (
    AuthorityType,
    Provenance,
    SourceDocument,
    SourceType,
    VerificationEligibility,
)
from .validation import compute_content_hash
from .gastat import parse_explicit_date

MISA_ALLOWED_DOMAINS: tuple[str, ...] = (
    "misa.gov.sa",
    "www.misa.gov.sa",
)

MISA_HOME_EN = "https://misa.gov.sa/"

# Default live fixtures for acceptance (official public pages).
DEFAULT_MISA_URLS: tuple[str, ...] = (
    "https://misa.gov.sa/activities/national-investment-strategy/",
    "https://misa.gov.sa/activities/investment-development/",
)


def _stable_source_id(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    path = urlparse(url).path.rstrip("/").split("/")[-1] or "page"
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", path)[:40]
    return f"misa-{safe}-{digest}"


def _infer_language(url: str, text: str) -> str:
    if "/ar/" in url or url.rstrip("/").endswith("/ar"):
        return "ar"
    if re.search(r"[\u0600-\u06FF]", text or ""):
        return "ar"
    return "en"


class MisaConnector(SourceConnector):
    """Live connector for MISA — Ministry of Investment official public pages."""

    CONNECTOR_ID = "live.misa"
    REGISTRY_KEY = "misa"

    def __init__(
        self,
        *,
        enabled: bool = True,
        reader: Optional[SafePageReader] = None,
        default_urls: Optional[Sequence[str]] = None,
    ) -> None:
        self._enabled = enabled
        self._reader = reader or SafePageReader(
            allowed_domains=MISA_ALLOWED_DOMAINS,
            timeout_seconds=30.0,
        )
        self._default_urls = (
            list(default_urls) if default_urls is not None else list(DEFAULT_MISA_URLS)
        )

    @property
    def connector_id(self) -> str:
        return self.CONNECTOR_ID

    @property
    def source_metadata(self) -> Dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "registry_key": self.REGISTRY_KEY,
            "name": "MISA — Ministry of Investment",
            "source_type": SourceType.MARKET_REPORT.value,
            "authority_type": AuthorityType.OFFICIAL_PRIMARY.value,
            "base_url": "https://misa.gov.sa",
            "allowed_domains": list(MISA_ALLOWED_DOMAINS),
            "country": "SA",
            "live": True,
            "api": None,
            "retrieval": "official_public_html",
            "purpose": "investment_intelligence",
            "supported_sectors": ['investment', 'sector_attractiveness', 'foreign_investment'],
            "languages": ["ar", "en"],
        }

    def health(self) -> ConnectorHealth:
        if not self._enabled:
            return ConnectorHealth(
                status=ConnectorStatus.DISABLED,
                checked_at=datetime.now(timezone.utc),
                detail="MISA connector disabled",
            )
        try:
            page = self._reader.read(MISA_HOME_EN, use_cache=True)
            ok = page.status_code == 200 and bool(page.text.strip())
            return ConnectorHealth(
                status=ConnectorStatus.HEALTHY if ok else ConnectorStatus.DEGRADED,
                checked_at=datetime.now(timezone.utc),
                detail="MISA home reachable" if ok else "MISA home returned empty body",
                metadata={"final_url": page.final_url, "from_cache": page.from_cache},
            )
        except (PageFetchError, UrlSecurityError) as exc:
            return ConnectorHealth(
                status=ConnectorStatus.UNAVAILABLE,
                checked_at=datetime.now(timezone.utc),
                detail=str(exc)[:500],
            )

    def fetch(self, *, query: Optional[str] = None, **kwargs: Any) -> List[Dict[str, Any]]:
        if not self._enabled:
            return []

        urls: List[str] = []
        url = kwargs.get("url")
        urls_kw = kwargs.get("urls")
        if url:
            urls.append(str(url))
        if urls_kw:
            urls.extend(str(u) for u in urls_kw)
        if not urls:
            q = (query or "").strip().lower()
            if q:
                for u in self._default_urls:
                    try:
                        page = self._reader.read(u, use_cache=True)
                    except (PageFetchError, UrlSecurityError):
                        continue
                    blob = f"{page.title or ''} {page.text[:3000]}".lower()
                    if q in blob or any(tok in blob for tok in q.split() if len(tok) > 3):
                        urls.append(u)
                if not urls:
                    return []
            else:
                urls = list(self._default_urls)

        raws: List[Dict[str, Any]] = []
        for u in urls:
            try:
                canonical = canonicalize_url(u)
                page = self._reader.read(canonical, use_cache=True)
            except (PageFetchError, UrlSecurityError) as exc:
                raws.append(
                    {
                        "id": _stable_source_id(u),
                        "error": str(exc),
                        "url": u,
                        "failed": True,
                    }
                )
                continue
            raws.append(
                {
                    "id": _stable_source_id(page.final_url),
                    "title": page.title,
                    "content": page.text,
                    "url": page.final_url,
                    "requested_url": page.requested_url,
                    "retrieved_at": page.retrieved_at.isoformat(),
                    "published_at_raw": page.published_at_raw,
                    "content_type": page.content_type,
                    "content_hash": page.content_hash,
                    "from_cache": page.from_cache,
                    "language": _infer_language(page.final_url, page.text),
                    # Never invent sector/category.
                    "sector": None,
                    "failed": False,
                }
            )
        return raws

    def normalize(self, raw: Dict[str, Any]) -> SourceDocument:
        if raw.get("failed"):
            now = datetime.now(timezone.utc)
            return SourceDocument(
                source_id=str(raw.get("id") or "misa-failed"),
                source_name="MISA",
                source_type=SourceType.MARKET_REPORT,
                authority_type=AuthorityType.OFFICIAL_PRIMARY,
                content="fetch failed",
                retrieved_at=now,
                provenance=Provenance(
                    connector_id=self.connector_id,
                    original_url=raw.get("url"),
                    retrieval_method="http_html",
                    retrieved_at=now,
                    registry_key=self.REGISTRY_KEY,
                ),
                verification_eligibility=VerificationEligibility.NOT_ELIGIBLE,
                metadata={"error": raw.get("error"), "failed": True},
            )

        retrieved_raw = raw.get("retrieved_at")
        if isinstance(retrieved_raw, datetime):
            retrieved_at = retrieved_raw
        elif isinstance(retrieved_raw, str) and retrieved_raw.strip():
            retrieved_at = datetime.fromisoformat(retrieved_raw.replace("Z", "+00:00"))
        else:
            retrieved_at = datetime.now(timezone.utc)

        content = str(raw.get("content") or "").strip()
        url = raw.get("url")
        published_at = parse_explicit_date(raw.get("published_at_raw"))
        language = raw.get("language") or _infer_language(str(url or ""), content)
        sector = raw.get("sector") if isinstance(raw.get("sector"), str) else None
        content_hash = raw.get("content_hash") or compute_content_hash(content)

        confidence = 0.85 if published_at is not None else 0.7
        if not url:
            confidence = 0.4

        return SourceDocument(
            source_id=str(raw.get("id") or _stable_source_id(str(url or "unknown"))),
            source_name="MISA — Ministry of Investment",
            source_type=SourceType.MARKET_REPORT,
            authority_type=AuthorityType.OFFICIAL_PRIMARY,
            url=url,
            canonical_url=url,
            title=raw.get("title"),
            content=content,
            published_at=published_at,
            retrieved_at=retrieved_at,
            country="SA",
            sector=sector,
            language=language,
            languages=[language],
            sectors=[sector] if sector else [],
            document_type="official_publication",
            content_type=raw.get("content_type") or "text/html",
            source_authority_score=0.9,
            source_quality_score=0.8 if published_at else 0.65,
            confidence=confidence,
            content_hash=content_hash,
            provenance=Provenance(
                connector_id=self.connector_id,
                original_url=url,
                retrieval_method="http_html",
                retrieved_at=retrieved_at,
                registry_key=self.REGISTRY_KEY,
            ),
            metadata={
                "live": True,
                "from_cache": bool(raw.get("from_cache")),
                "published_at_raw": raw.get("published_at_raw"),
                "requested_url": raw.get("requested_url"),
                "purpose": "investment_intelligence",
            },
            verification_eligibility=VerificationEligibility.ELIGIBLE,
        )

    def retrieve(self, *, query: Optional[str] = None, **kwargs: Any) -> List[SourceDocument]:
        """fetch → normalize → validate; drop failed/allowlist-rejected payloads."""
        docs: List[SourceDocument] = []
        for raw in self.fetch(query=query, **kwargs):
            if raw.get("failed"):
                continue
            doc = self.normalize(raw)
            if (doc.metadata or {}).get("failed"):
                continue
            ok, _errors = self.validate_provenance(doc)
            if ok:
                docs.append(doc)
        return docs

    def fetch_url(self, url: str) -> SourceDocument:
        """Fetch a single official URL into a validated SourceDocument."""
        raws = self.fetch(url=url)
        if raws and raws[0].get("failed"):
            err = raws[0].get("error") or "MISA fetch failed"
            low = str(err).lower()
            if "allowlist" in low or "blocked" in low or "ssrf" in low or "private" in low:
                raise UrlSecurityError(str(err))
            raise PageFetchError(str(err))
        docs = self.retrieve(url=url)
        if not docs:
            raise PageFetchError(
                f"MISA fetch produced no valid SourceDocument for {url}"
            )
        return docs[0]
