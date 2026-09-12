"""Controlled competitor intelligence — evidence required, never invent."""

from __future__ import annotations

import re
from typing import Any

from ai_engine.research.market.schemas import CompetitorEvidence, EvidenceStatus

_NAME_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z0-9&.\-]+(?:\s+[A-Z][A-Za-z0-9&.\-]+){0,4})\b"
)

_STOP_NAMES = {
    "Saudi",
    "Arabia",
    "Kingdom",
    "GASTAT",
    "MISA",
    "Ministry",
    "Investment",
    "Statistics",
    "General",
    "Authority",
    "National",
    "Strategy",
    "Development",
    "Consumer",
    "Price",
    "Index",
    "Inflation",
    "March",
    "April",
    "January",
    "February",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
    "Quarter",
    "Annual",
    "Table",
    "Figure",
    "Page",
    "Home",
    "News",
    "English",
    "Arabic",
}


def _is_plausible_competitor_name(name: str) -> bool:
    parts = name.split()
    if len(name) < 3 or len(name) > 80:
        return False
    if name in _STOP_NAMES:
        return False
    if all(p in _STOP_NAMES for p in parts):
        return False
    return any(p not in _STOP_NAMES and len(p) > 2 for p in parts)


def extract_competitors_from_evidence(
    *,
    evidence_items: list[dict[str, Any]],
    geography: str = "Saudi Arabia",
    sector: str = "",
) -> list[CompetitorEvidence]:
    """
    Extract competitors only when sourced evidence exists.

    Never fabricates companies, market share, or pricing.
    """
    _ = sector
    found: list[CompetitorEvidence] = []
    seen: set[str] = set()

    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        text = str(
            item.get("statement")
            or item.get("content")
            or item.get("claim")
            or item.get("title")
            or ""
        ).strip()
        source_url = item.get("source_url") or item.get("url") or item.get("canonical_url")
        document_id = item.get("document_id") or item.get("source_id")
        chunk_id = item.get("chunk_id")
        source_key = item.get("source_key")
        explicit = str(item.get("competitor_name") or item.get("name") or "").strip()

        candidates: list[str] = []
        if explicit:
            candidates.append(explicit)
        elif source_url or document_id:
            lower = text.lower()
            if any(
                k in lower
                for k in ("competitor", "competes", "rival", "player", "company", "firm")
            ):
                for m in _NAME_PATTERN.finditer(text[:800]):
                    name = m.group(1).strip(" .,;:")
                    if _is_plausible_competitor_name(name):
                        candidates.append(name)

        for name in candidates:
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            if not source_url and not document_id:
                found.append(
                    CompetitorEvidence(
                        name=name,
                        source_url=None,
                        evidence_type="unsupported_mention",
                        geography=geography,
                        confidence=0.0,
                        evidence_reference="missing_source",
                        status="NOT_VERIFIED",
                        source_key=str(source_key) if source_key else None,
                    )
                )
                continue
            found.append(
                CompetitorEvidence(
                    name=name,
                    source_url=str(source_url) if source_url else None,
                    evidence_type="sourced_mention",
                    geography=geography,
                    confidence=0.55 if source_url else 0.45,
                    evidence_reference=str(
                        document_id or source_url or chunk_id or "sourced_text"
                    ),
                    status="VERIFIED" if source_url else "NOT_VERIFIED",
                    source_key=str(source_key) if source_key else None,
                    document_id=str(document_id) if document_id else None,
                    chunk_id=str(chunk_id) if chunk_id else None,
                )
            )

    return found


def research_competitors(
    *,
    business_idea: str,
    sector: str,
    geography: str = "Saudi Arabia",
    evidence_items: list[dict[str, Any]] | None = None,
) -> tuple[list[CompetitorEvidence], EvidenceStatus]:
    """
    Controlled competitor research.

    Without sourced evidence → NOT_FOUND (never invent).
    Mentions lacking URL → NOT_VERIFIED.
    URL/document reference → VERIFIED (sourced mention only).
    """
    _ = business_idea
    items = list(evidence_items or [])
    competitors = extract_competitors_from_evidence(
        evidence_items=items, geography=geography, sector=sector
    )
    named = [c for c in competitors if c.name]
    if not named:
        return (
            [
                CompetitorEvidence(
                    name="",
                    source_url=None,
                    evidence_type="none",
                    geography=geography,
                    confidence=0.0,
                    evidence_reference="no_sourced_competitor_evidence",
                    status="NOT_FOUND",
                )
            ],
            "NOT_FOUND",
        )
    if any(c.status == "VERIFIED" for c in named):
        return named, "VERIFIED"
    if any(c.status == "NOT_VERIFIED" for c in named):
        return named, "NOT_VERIFIED"
    return named, "PARTIAL"
