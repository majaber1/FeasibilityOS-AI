"""Monsha'at live SourceConnector — official Monsha'at domains only.

Retrieval priority:
1. Official Real-Time Open Data API (pservices.monshaat.gov.sa)
2. Official Monsha'at report / document URL
3. Official public HTML page (best-effort)

Reuses Phase 7B SSRF / allowlist controls. Never invents dates, statistics,
sector classification, or authority.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from app.integrations.research.page_reader import PageFetchError, SafePageReader
from app.integrations.research.security import (
    UrlSecurityError,
    canonicalize_url,
    validate_url,
)

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

MONSHAAT_ALLOWED_DOMAINS: tuple[str, ...] = (
    "monshaat.gov.sa",
    "www.monshaat.gov.sa",
    "pservices.monshaat.gov.sa",
)

MONSHAAT_HOME_EN = "https://www.monshaat.gov.sa/en"

# Official Real-Time Open Data API pattern published by Monsha'at.
MONSHAAT_API_HOST = "pservices.monshaat.gov.sa"
MONSHAAT_API_PATH = "/BI/TaskService/OpenData/EnterprisesStatistics"
DEFAULT_MONSHAAT_API_QUERIES: tuple[tuple[int, int], ...] = (
    (2023, 4),
    (2024, 1),
)

# Optional official HTML report fixtures (best-effort when site is reachable).
DEFAULT_MONSHAAT_URLS: tuple[str, ...] = (
    "https://www.monshaat.gov.sa/en/monshaat-reports",
    "https://www.monshaat.gov.sa/en/node/274250",
)

_JSON_CONTENT_TYPES = frozenset(
    {
        "application/json",
        "text/json",
        "application/problem+json",
        "text/plain",  # some gateways return JSON as text/plain
    }
)


def build_enterprises_statistics_url(
    year: int,
    quarter: int,
    *,
    pagination_index: int = 1,
    records_per_page: int = 50,
) -> str:
    """Build the official Monsha'at EnterprisesStatistics Open Data API URL."""
    if year < 2000 or year > 2100:
        raise ValueError(f"year out of plausible range: {year}")
    if quarter not in {1, 2, 3, 4}:
        raise ValueError(f"quarter must be 1-4, got {quarter}")
    if pagination_index < 1:
        raise ValueError("pagination_index must be >= 1")
    if records_per_page < 1 or records_per_page > 1000:
        raise ValueError("records_per_page must be 1..1000")
    qs = urlencode(
        {
            "paginationIndex": str(pagination_index),
            "recordsPerPage": str(records_per_page),
        }
    )
    return (
        f"https://{MONSHAAT_API_HOST}{MONSHAAT_API_PATH}/"
        f"{int(year)}/{int(quarter)}?{qs}"
    )


def _stable_source_id(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    path = urlparse(url).path.rstrip("/").split("/")[-1] or "page"
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", path)[:40]
    return f"monshaat-{safe}-{digest}"


def _infer_language(url: str, text: str) -> str:
    if "/ar/" in url or url.rstrip("/").endswith("/ar"):
        return "ar"
    if re.search(r"[\u0600-\u06FF]", text or ""):
        return "ar"
    return "en"


def _json_to_text(payload: Any) -> str:
    """Deterministic text representation of an official API payload. No summarization."""
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _extract_explicit_year_quarter(payload: Any) -> Tuple[Optional[int], Optional[int]]:
    """Pull year/quarter only when explicitly present in the payload. Never invent."""
    if not isinstance(payload, dict):
        return None, None
    year = None
    quarter = None
    for yk in ("Year", "year", "YEAR", "FiscalYear", "fiscalYear"):
        if yk in payload and payload[yk] is not None:
            try:
                year = int(payload[yk])
            except (TypeError, ValueError):
                year = None
            break
    for qk in ("Quarter", "quarter", "QUARTER", "Qtr", "qtr"):
        if qk in payload and payload[qk] is not None:
            try:
                quarter = int(payload[qk])
            except (TypeError, ValueError):
                quarter = None
            break
    return year, quarter


class MonshaatConnector(SourceConnector):
    """Live connector for Monsha'at official Open Data API + public pages."""

    CONNECTOR_ID = "live.monshaat"
    REGISTRY_KEY = "monshaat"

    def __init__(
        self,
        *,
        enabled: bool = True,
        reader: Optional[SafePageReader] = None,
        default_urls: Optional[Sequence[str]] = None,
        default_api_queries: Optional[Sequence[Tuple[int, int]]] = None,
        api_timeout_seconds: float = 20.0,
        api_max_bytes: int = 2_000_000,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._enabled = enabled
        self._reader = reader or SafePageReader(
            allowed_domains=MONSHAAT_ALLOWED_DOMAINS,
            timeout_seconds=15.0,
        )
        self._default_urls = (
            list(default_urls) if default_urls is not None else list(DEFAULT_MONSHAAT_URLS)
        )
        self._default_api_queries = (
            list(default_api_queries)
            if default_api_queries is not None
            else list(DEFAULT_MONSHAAT_API_QUERIES)
        )
        self._api_timeout_seconds = api_timeout_seconds
        self._api_max_bytes = api_max_bytes
        self._http_client = http_client

    @property
    def connector_id(self) -> str:
        return self.CONNECTOR_ID

    @property
    def source_metadata(self) -> Dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "registry_key": self.REGISTRY_KEY,
            "name": "Monsha'at — Small & Medium Enterprises General Authority",
            "source_type": SourceType.OPEN_DATA.value,
            "authority_type": AuthorityType.OFFICIAL_PRIMARY.value,
            "base_url": "https://monshaat.gov.sa",
            "allowed_domains": list(MONSHAAT_ALLOWED_DOMAINS),
            "country": "SA",
            "live": True,
            "api": {
                "host": MONSHAAT_API_HOST,
                "path": MONSHAAT_API_PATH,
                "pattern": (
                    f"https://{MONSHAAT_API_HOST}{MONSHAAT_API_PATH}/"
                    "{Year}/{Quarter}?paginationIndex={PageIndex}&recordsPerPage={PageSize}"
                ),
            },
            "retrieval": "official_api_preferred",
            "purpose": "sme_market_intelligence",
            "supported_sectors": ["sme", "entrepreneurship", "business_environment"],
            "languages": ["ar", "en"],
        }

    # ------------------------------------------------------------------ health
    def _probe_api(self) -> Tuple[bool, str]:
        year, quarter = self._default_api_queries[0]
        url = build_enterprises_statistics_url(year, quarter, records_per_page=1)
        try:
            raw = self._fetch_api_url(url)
            if raw.get("failed"):
                return False, str(raw.get("error") or "api probe failed")
            return True, f"API reachable ({year}Q{quarter})"
        except Exception as exc:  # noqa: BLE001 — probe must never raise
            return False, str(exc)[:400]

    def _probe_html(self) -> Tuple[bool, str]:
        try:
            page = self._reader.read(MONSHAAT_HOME_EN, use_cache=True)
            ok = page.status_code == 200 and bool(page.text.strip())
            return (
                ok,
                "HTML home reachable" if ok else "HTML home returned empty body",
            )
        except (PageFetchError, UrlSecurityError) as exc:
            return False, str(exc)[:400]

    def health(self) -> ConnectorHealth:
        if not self._enabled:
            return ConnectorHealth(
                status=ConnectorStatus.DISABLED,
                checked_at=datetime.now(timezone.utc),
                detail="MONSHAAT connector disabled",
            )

        api_ok, api_detail = self._probe_api()
        html_ok, html_detail = self._probe_html()
        meta = {
            "api_ok": api_ok,
            "api_detail": api_detail,
            "html_ok": html_ok,
            "html_detail": html_detail,
        }

        if api_ok and html_ok:
            status = ConnectorStatus.HEALTHY
            detail = "API and HTML retrieval paths reachable"
        elif api_ok or html_ok:
            status = ConnectorStatus.DEGRADED
            detail = (
                f"partial: api={'ok' if api_ok else 'fail'} "
                f"({api_detail}); html={'ok' if html_ok else 'fail'} ({html_detail})"
            )
        else:
            status = ConnectorStatus.UNAVAILABLE
            detail = f"all paths failed: api={api_detail}; html={html_detail}"

        return ConnectorHealth(
            status=status,
            checked_at=datetime.now(timezone.utc),
            detail=detail,
            metadata=meta,
        )

    # -------------------------------------------------------------- API fetch
    def _fetch_api_url(self, url: str) -> Dict[str, Any]:
        """Fetch one official API URL with Phase 7B SSRF controls."""
        try:
            canonical = validate_url(
                url,
                allowed_domains=MONSHAAT_ALLOWED_DOMAINS,
                resolve_dns=True,
            )
        except UrlSecurityError as exc:
            return {
                "id": _stable_source_id(url),
                "error": str(exc),
                "url": url,
                "failed": True,
                "retrieval_method": "official_api",
            }

        parsed = urlparse(canonical)
        parts = [p for p in parsed.path.split("/") if p]
        year: Optional[int] = None
        quarter: Optional[int] = None
        if len(parts) >= 2:
            try:
                year = int(parts[-2])
                quarter = int(parts[-1])
            except ValueError:
                year = None
                quarter = None

        query_params = {
            k: (v[0] if isinstance(v, list) else v)
            for k, v in parse_qs(parsed.query).items()
        }

        headers = {
            "Accept": "application/json",
            "User-Agent": (
                "SaudiBusinessBot/7C1 (+https://saudi-business.local; "
                "governed Monsha'at Open Data; contact=ops@saudi-business.local)"
            ),
        }

        try:
            client = self._http_client
            owns_client = client is None
            if owns_client:
                client = httpx.Client(
                    timeout=self._api_timeout_seconds,
                    follow_redirects=False,
                )
            assert client is not None
            try:
                current = canonical
                response = None
                for _ in range(5):
                    current = validate_url(
                        current,
                        allowed_domains=MONSHAAT_ALLOWED_DOMAINS,
                        resolve_dns=True,
                    )
                    response = client.get(current, headers=headers)
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

                ctype = (
                    (response.headers.get("content-type") or "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )
                if ctype and ctype not in _JSON_CONTENT_TYPES:
                    raise PageFetchError(f"content-type not allowed for API: {ctype}")

                cl = response.headers.get("content-length")
                if cl is not None:
                    try:
                        if int(cl) > self._api_max_bytes:
                            raise PageFetchError("content-length exceeds max_bytes")
                    except ValueError:
                        pass

                raw_bytes = response.content
                if len(raw_bytes) > self._api_max_bytes:
                    raise PageFetchError("response exceeds max_bytes")

                try:
                    payload = response.json()
                except Exception as exc:  # noqa: BLE001
                    raise PageFetchError(f"response is not valid JSON: {exc}") from exc

                final_url = validate_url(
                    canonicalize_url(str(response.url)),
                    allowed_domains=MONSHAAT_ALLOWED_DOMAINS,
                    resolve_dns=True,
                )
            finally:
                if owns_client:
                    client.close()
        except UrlSecurityError as exc:
            return {
                "id": _stable_source_id(url),
                "error": str(exc),
                "url": url,
                "failed": True,
                "retrieval_method": "official_api",
                "year": year,
                "quarter": quarter,
                "query_params": query_params,
            }
        except (PageFetchError, httpx.HTTPError, httpx.TimeoutException) as exc:
            return {
                "id": _stable_source_id(url),
                "error": str(exc),
                "url": url,
                "failed": True,
                "retrieval_method": "official_api",
                "year": year,
                "quarter": quarter,
                "query_params": query_params,
            }

        content = _json_to_text(payload).strip()
        content_hash = compute_content_hash(content)
        retrieved_at = datetime.now(timezone.utc)
        payload_year, payload_quarter = _extract_explicit_year_quarter(payload)

        title_bits = ["Monsha'at Enterprises Statistics"]
        if year is not None:
            title_bits.append(str(year))
        if quarter is not None:
            title_bits.append(f"Q{quarter}")

        return {
            "id": _stable_source_id(final_url),
            "title": " — ".join(title_bits),
            "content": content,
            "url": final_url,
            "requested_url": canonical,
            "retrieved_at": retrieved_at.isoformat(),
            "published_at_raw": None,  # never invent publication date
            "content_type": ctype or "application/json",
            "content_hash": content_hash,
            "from_cache": False,
            "language": "ar" if re.search(r"[\u0600-\u06FF]", content) else "en",
            "sector": None,  # never invent sector
            "failed": False,
            "retrieval_method": "official_api",
            "year": year,
            "quarter": quarter,
            "payload_year": payload_year,
            "payload_quarter": payload_quarter,
            "query_params": query_params,
            "record_identity": {
                "endpoint": MONSHAAT_API_PATH,
                "year": year,
                "quarter": quarter,
                "paginationIndex": query_params.get("paginationIndex"),
                "recordsPerPage": query_params.get("recordsPerPage"),
            },
        }

    def fetch_api(
        self,
        *,
        year: Optional[int] = None,
        quarter: Optional[int] = None,
        years_quarters: Optional[Sequence[Tuple[int, int]]] = None,
        pagination_index: int = 1,
        records_per_page: int = 50,
        url: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch official Open Data API payloads (priority path)."""
        if not self._enabled:
            return []

        urls: List[str] = []
        if url:
            urls.append(str(url))
        else:
            pairs: List[Tuple[int, int]] = []
            if years_quarters:
                pairs.extend((int(y), int(q)) for y, q in years_quarters)
            elif year is not None and quarter is not None:
                pairs.append((int(year), int(quarter)))
            else:
                pairs.extend(self._default_api_queries)
            for y, q in pairs:
                urls.append(
                    build_enterprises_statistics_url(
                        y,
                        q,
                        pagination_index=pagination_index,
                        records_per_page=records_per_page,
                    )
                )

        return [self._fetch_api_url(u) for u in urls]

    # ------------------------------------------------------------- HTML fetch
    def _fetch_html_urls(
        self,
        *,
        query: Optional[str] = None,
        url: Optional[str] = None,
        urls: Optional[Sequence[str]] = None,
    ) -> List[Dict[str, Any]]:
        selected: List[str] = []
        if url:
            selected.append(str(url))
        if urls:
            selected.extend(str(u) for u in urls)
        if not selected:
            q = (query or "").strip().lower()
            if q:
                for u in self._default_urls:
                    try:
                        page = self._reader.read(u, use_cache=True)
                    except (PageFetchError, UrlSecurityError):
                        continue
                    blob = f"{page.title or ''} {page.text[:3000]}".lower()
                    if q in blob or any(tok in blob for tok in q.split() if len(tok) > 3):
                        selected.append(u)
                if not selected:
                    return []
            else:
                selected = list(self._default_urls)

        raws: List[Dict[str, Any]] = []
        for u in selected:
            try:
                canonical = canonicalize_url(u)
                validate_url(
                    canonical,
                    allowed_domains=MONSHAAT_ALLOWED_DOMAINS,
                    resolve_dns=True,
                )
                page = self._reader.read(canonical, use_cache=True)
            except (PageFetchError, UrlSecurityError) as exc:
                raws.append(
                    {
                        "id": _stable_source_id(u),
                        "error": str(exc),
                        "url": u,
                        "failed": True,
                        "retrieval_method": "http_html",
                    }
                )
                continue
            content = (page.text or "").strip()
            raws.append(
                {
                    "id": _stable_source_id(page.final_url),
                    "title": page.title,
                    "content": content,
                    "url": page.final_url,
                    "requested_url": page.requested_url,
                    "retrieved_at": page.retrieved_at.isoformat(),
                    "published_at_raw": page.published_at_raw,
                    "content_type": page.content_type,
                    "content_hash": compute_content_hash(content),
                    "from_cache": page.from_cache,
                    "language": _infer_language(page.final_url, content),
                    "sector": None,
                    "failed": False,
                    "retrieval_method": "http_html",
                }
            )
        return raws

    def fetch(self, *, query: Optional[str] = None, **kwargs: Any) -> List[Dict[str, Any]]:
        """Priority: official API → explicit HTML URL(s) → default HTML fixtures."""
        if not self._enabled:
            return []

        mode = (kwargs.get("mode") or "").strip().lower()
        explicit_url = kwargs.get("url")
        is_api_url = bool(
            explicit_url and "pservices.monshaat.gov.sa" in str(explicit_url)
        )

        if mode == "html":
            return self._fetch_html_urls(
                query=query,
                url=kwargs.get("url"),
                urls=kwargs.get("urls"),
            )
        if (
            mode == "api"
            or kwargs.get("year")
            or kwargs.get("years_quarters")
            or is_api_url
        ):
            return self.fetch_api(
                year=kwargs.get("year"),
                quarter=kwargs.get("quarter"),
                years_quarters=kwargs.get("years_quarters"),
                pagination_index=int(kwargs.get("pagination_index") or 1),
                records_per_page=int(kwargs.get("records_per_page") or 50),
                url=kwargs.get("url"),
            )

        # Default: try official API first; if all fail, fall back to HTML.
        api_raws = self.fetch_api()
        if any(not r.get("failed") for r in api_raws):
            return [r for r in api_raws if not r.get("failed")]

        html_raws = self._fetch_html_urls(
            query=query, url=kwargs.get("url"), urls=kwargs.get("urls")
        )
        if any(not r.get("failed") for r in html_raws):
            return [r for r in html_raws if not r.get("failed")]

        return api_raws + html_raws

    def normalize(self, raw: Dict[str, Any]) -> SourceDocument:
        retrieval_method = str(raw.get("retrieval_method") or "http_html")
        if raw.get("failed"):
            now = datetime.now(timezone.utc)
            return SourceDocument(
                source_id=str(raw.get("id") or "monshaat-failed"),
                source_name="MONSHAAT",
                source_type=SourceType.OPEN_DATA
                if retrieval_method == "official_api"
                else SourceType.MARKET_REPORT,
                authority_type=AuthorityType.OFFICIAL_PRIMARY,
                content="fetch failed",
                retrieved_at=now,
                provenance=Provenance(
                    connector_id=self.connector_id,
                    original_url=raw.get("url"),
                    retrieval_method=retrieval_method,
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
        content_hash = compute_content_hash(content)

        confidence = (
            0.9
            if retrieval_method == "official_api"
            else (0.85 if published_at else 0.7)
        )
        if not url:
            confidence = 0.4

        source_type = (
            SourceType.OPEN_DATA
            if retrieval_method == "official_api"
            else SourceType.MARKET_REPORT
        )

        metadata: Dict[str, Any] = {
            "live": True,
            "from_cache": bool(raw.get("from_cache")),
            "published_at_raw": raw.get("published_at_raw"),
            "requested_url": raw.get("requested_url"),
            "purpose": "sme_market_intelligence",
            "retrieval_method": retrieval_method,
        }
        if retrieval_method == "official_api":
            metadata.update(
                {
                    "year": raw.get("year"),
                    "quarter": raw.get("quarter"),
                    "query_params": raw.get("query_params"),
                    "record_identity": raw.get("record_identity"),
                    "payload_year": raw.get("payload_year"),
                    "payload_quarter": raw.get("payload_quarter"),
                }
            )

        return SourceDocument(
            source_id=str(raw.get("id") or _stable_source_id(str(url or "unknown"))),
            source_name="Monsha'at — Small & Medium Enterprises General Authority",
            source_type=source_type,
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
            document_type=(
                "official_open_data"
                if retrieval_method == "official_api"
                else "official_publication"
            ),
            content_type=raw.get("content_type")
            or (
                "application/json"
                if retrieval_method == "official_api"
                else "text/html"
            ),
            source_authority_score=0.9,
            source_quality_score=(
                0.85
                if retrieval_method == "official_api"
                else (0.8 if published_at else 0.65)
            ),
            confidence=confidence,
            content_hash=content_hash,
            provenance=Provenance(
                connector_id=self.connector_id,
                original_url=url,
                retrieval_method=retrieval_method,
                retrieved_at=retrieved_at,
                registry_key=self.REGISTRY_KEY,
            ),
            metadata=metadata,
            verification_eligibility=VerificationEligibility.ELIGIBLE,
        )

    def retrieve(self, *, query: Optional[str] = None, **kwargs: Any) -> List[SourceDocument]:
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
        """Fetch a single official URL (API or HTML) into a validated SourceDocument."""
        mode = "api" if "pservices.monshaat.gov.sa" in url else "html"
        raws = self.fetch(mode=mode, url=url)
        if raws and raws[0].get("failed"):
            err = raws[0].get("error") or "MONSHAAT fetch failed"
            low = str(err).lower()
            if "allowlist" in low or "blocked" in low or "ssrf" in low or "private" in low:
                raise UrlSecurityError(str(err))
            raise PageFetchError(str(err))
        docs = self.retrieve(mode=mode, url=url)
        if not docs:
            raise PageFetchError(
                f"MONSHAAT fetch produced no valid SourceDocument for {url}"
            )
        return docs[0]
