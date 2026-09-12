"""Phase 8B market research service — Research → Evidence → Knowledge → Insight."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from ai_engine.research.market.competitor import research_competitors
from ai_engine.research.market.market_signal import research_market_signals
from ai_engine.research.market.planner import (
    build_market_plan,
    extract_market_context_from_state,
)
from ai_engine.research.market.pricing_signal import research_pricing_signals
from ai_engine.research.market.regulation import build_regulation_framework
from ai_engine.research.market.schemas import (
    EvidenceStatus,
    MarketInsight,
    MarketResearchResult,
)
from ai_engine.research.schemas import ResearchClaim

logger = logging.getLogger(__name__)

_MARKET_CACHE: dict[str, MarketResearchResult] = {}


def _make_cache_key(
    *,
    study_id: str,
    business_idea: str,
    sector: str,
    geography: str,
    research_types: list[str],
    evidence_fingerprint: str,
) -> str:
    raw = "|".join(
        [
            study_id,
            business_idea,
            sector,
            geography,
            ",".join(research_types),
            evidence_fingerprint,
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fingerprint_evidence(items: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for it in items:
        parts.append(
            f"{it.get('source_key')}:{it.get('document_id')}:{it.get('source_url')}:"
            f"{str(it.get('statement') or '')[:80]}"
        )
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def evidence_items_from_research_claims(claims: list[Any]) -> list[dict[str, Any]]:
    """Normalize ResearchClaim / Claim / dict into evidence item dicts."""
    items: list[dict[str, Any]] = []
    for c in claims or []:
        if isinstance(c, ResearchClaim):
            items.append(
                {
                    "statement": c.statement,
                    "source_type": c.source_type,
                    "source_url": c.source_url,
                    "source_key": c.source_key,
                    "document_id": c.document_id,
                    "chunk_id": c.chunk_id,
                    "origin": c.origin,
                    "confidence": c.confidence,
                }
            )
        elif isinstance(c, dict):
            items.append(dict(c))
        else:
            items.append(
                {
                    "statement": str(getattr(c, "statement", "") or ""),
                    "source_type": getattr(c, "source_type", None),
                    "source_url": getattr(c, "source_url", None),
                    "source_key": getattr(c, "source_key", None),
                    "document_id": getattr(c, "document_id", None),
                    "chunk_id": getattr(c, "chunk_id", None),
                    "origin": getattr(c, "origin", None),
                    "confidence": getattr(c, "confidence", 0.0),
                }
            )
    return items


def market_result_to_research_claims(
    result: MarketResearchResult,
) -> list[ResearchClaim]:
    """Map verified market insights into ResearchClaim for Evidence Pack merge."""
    claims: list[ResearchClaim] = []
    for insight in result.insights:
        # Only merge evidence-backed insights into study claims.
        # Placeholders / NOT_FOUND stay in market_research payload for transparency.
        if insight.status not in {"VERIFIED", "CONFLICT"}:
            continue
        source_type = "official" if insight.status == "VERIFIED" else "document"
        if insight.source_key not in {"gastat", "misa"} and insight.status == "VERIFIED":
            source_type = "document"
        claims.append(
            ResearchClaim(
                statement=insight.insight,
                source_type=source_type,  # type: ignore[arg-type]
                source_url=insight.official_url,
                confidence=float(insight.confidence),
                metric_key=insight.research_type,
                source_key=insight.source_key,
                document_id=insight.document_id,
                chunk_id=insight.chunk_id,
                origin="market_research",
            )
        )
    return claims


def _build_insights(result: MarketResearchResult) -> list[MarketInsight]:
    insights: list[MarketInsight] = []

    for c in result.competitors:
        if not c.name and c.status == "NOT_FOUND":
            insights.append(
                MarketInsight(
                    insight="No sourced competitor evidence found (NOT_FOUND).",
                    research_type="COMPETITOR",
                    source="none",
                    official_url=None,
                    evidence_reference=c.evidence_reference,
                    confidence=0.0,
                    status="NOT_FOUND",
                )
            )
            continue
        if not c.name:
            continue
        insights.append(
            MarketInsight(
                insight=f"Competitor mention: {c.name} ({c.status})",
                research_type="COMPETITOR",
                source=c.source_key or "evidence",
                official_url=c.source_url,
                evidence_reference=c.evidence_reference,
                confidence=c.confidence,
                status=c.status,
                source_key=c.source_key,
                document_id=c.document_id,
                chunk_id=c.chunk_id,
            )
        )

    for s in result.market_signals:
        insights.append(
            MarketInsight(
                insight=f"{s.metric}={s.value}" + (f" ({s.period})" if s.period else ""),
                research_type="SECTOR_SIGNAL",
                source=s.source,
                official_url=s.source_url,
                evidence_reference=s.evidence_reference,
                confidence=s.confidence,
                status=s.status,
                source_key=s.source_key,
                document_id=s.document_id,
                chunk_id=s.chunk_id,
            )
        )

    for p in result.pricing_signals:
        if p.status == "NOT_FOUND" or p.price is None:
            insights.append(
                MarketInsight(
                    insight="Pricing evidence not found (NOT_FOUND).",
                    research_type="PRICING",
                    source="none",
                    official_url=None,
                    evidence_reference=p.evidence_reference,
                    confidence=0.0,
                    status="NOT_FOUND",
                )
            )
            continue
        insights.append(
            MarketInsight(
                insight=f"Price signal: {p.item} = {p.price} {p.currency or ''}".strip(),
                research_type="PRICING",
                source=p.source_key or "evidence",
                official_url=p.source_url,
                evidence_reference=p.evidence_reference,
                confidence=p.confidence,
                status=p.status,
                source_key=p.source_key,
                document_id=p.document_id,
                chunk_id=p.chunk_id,
            )
        )

    for r in result.regulation_signals:
        insights.append(
            MarketInsight(
                insight=f"{r.authority}: {r.requirement}",
                research_type="REGULATION",
                source=r.source_key or r.authority,
                official_url=r.source_url,
                evidence_reference=r.source_reference,
                confidence=r.confidence,
                status=r.status,
                source_key=r.source_key,
            )
        )

    for conflict in result.conflicts:
        insights.append(
            MarketInsight(
                insight=(
                    f"Conflict on {conflict.get('metric')} "
                    f"({conflict.get('period')}): values {conflict.get('values')}"
                ),
                research_type="SECTOR_SIGNAL",
                source=",".join(conflict.get("sources") or []),
                official_url=None,
                evidence_reference=";".join(conflict.get("evidence_references") or []),
                confidence=0.4,
                status="CONFLICT",
            )
        )

    return insights


def _overall_status(result: MarketResearchResult) -> EvidenceStatus:
    if result.conflicts:
        return "CONFLICT"
    statuses = [i.status for i in result.insights]
    if not statuses:
        return "NOT_FOUND"
    if any(s == "VERIFIED" for s in statuses) and any(
        s in {"NOT_FOUND", "PARTIAL", "NOT_VERIFIED"} for s in statuses
    ):
        return "PARTIAL"
    if all(s == "NOT_FOUND" for s in statuses):
        return "NOT_FOUND"
    if any(s == "VERIFIED" for s in statuses):
        return "VERIFIED"
    if any(s == "PARTIAL" for s in statuses):
        return "PARTIAL"
    return "NOT_VERIFIED"


def execute_market_research(
    *,
    study_id: str,
    business_idea: str = "",
    sector: str = "",
    geography: str = "Saudi Arabia",
    gaps: list[str] | None = None,
    evidence_items: list[dict[str, Any]] | None = None,
    use_cache: bool = True,
) -> MarketResearchResult:
    """
    Controlled market research over already-approved evidence (GASTAT/MISA/etc).

    Does not open arbitrary URLs. Does not invent competitors, prices, or market size.
    """
    started = time.perf_counter()
    plan = build_market_plan(
        study_id=study_id,
        business_idea=business_idea,
        sector=sector,
        geography=geography,
        gaps=gaps,
    )
    items = list(evidence_items or [])
    fp = _fingerprint_evidence(items)
    key = _make_cache_key(
        study_id=study_id,
        business_idea=business_idea,
        sector=sector,
        geography=geography,
        research_types=list(plan.research_types),
        evidence_fingerprint=fp,
    )
    if use_cache and key in _MARKET_CACHE:
        cached = _MARKET_CACHE[key]
        cached.cache_hits = int(cached.cache_hits or 0) + 1
        return cached

    attempts: list[dict[str, Any]] = [
        {
            "step": "plan",
            "research_types": list(plan.research_types),
            "selected_sources": list(plan.selected_sources),
            "placeholder_sources": list(plan.placeholder_sources),
        }
    ]

    competitors = []
    market_signals = []
    pricing_signals = []
    regulation_signals = []
    conflicts: list[dict[str, Any]] = []

    if "COMPETITOR" in plan.research_types:
        competitors, c_status = research_competitors(
            business_idea=business_idea,
            sector=sector,
            geography=geography,
            evidence_items=items,
        )
        attempts.append(
            {"step": "competitors", "status": c_status, "count": len(competitors)}
        )

    if any(t in plan.research_types for t in ("SECTOR_SIGNAL", "MARKET_SIZE")):
        market_signals, conflicts, m_status = research_market_signals(items)
        attempts.append(
            {
                "step": "market_signals",
                "status": m_status,
                "count": len(market_signals),
                "conflicts": len(conflicts),
            }
        )

    if "PRICING" in plan.research_types:
        pricing_signals, p_status = research_pricing_signals(items)
        attempts.append(
            {"step": "pricing", "status": p_status, "count": len(pricing_signals)}
        )

    if "REGULATION" in plan.research_types:
        regulation_signals, r_status = build_regulation_framework(
            sector=sector, evidence_items=items
        )
        attempts.append(
            {
                "step": "regulation",
                "status": r_status,
                "count": len(regulation_signals),
            }
        )

    result = MarketResearchResult(
        plan=plan,
        status="PARTIAL",
        competitors=competitors,
        market_signals=market_signals,
        pricing_signals=pricing_signals,
        regulation_signals=regulation_signals,
        conflicts=conflicts,
        attempts=attempts,
        knowledge_hits=sum(
            1 for i in items if i.get("from_knowledge") or i.get("document_id")
        ),
        live_fetches=sum(
            1
            for i in items
            if i.get("source_key") in {"gastat", "misa"} and i.get("source_url")
        ),
        duration_ms=0.0,
    )
    result.insights = _build_insights(result)
    result.status = _overall_status(result)
    result.duration_ms = (time.perf_counter() - started) * 1000.0

    if use_cache:
        _MARKET_CACHE[key] = result
    return result


def execute_market_research_from_state(
    state: Any,
    *,
    research_claims: list[Any] | None = None,
    use_cache: bool = True,
) -> MarketResearchResult:
    ctx = extract_market_context_from_state(state)
    items = evidence_items_from_research_claims(research_claims or [])
    existing = getattr(state, "claims", None)
    if existing is None and isinstance(state, dict):
        existing = state.get("claims")
    if existing:
        items.extend(evidence_items_from_research_claims(list(existing)))
    return execute_market_research(
        study_id=str(ctx["study_id"]),
        business_idea=str(ctx["business_idea"]),
        sector=str(ctx["sector"]),
        geography=str(ctx["geography"]),
        gaps=list(ctx["gaps"]),
        evidence_items=items,
        use_cache=use_cache,
    )


def clear_market_cache() -> None:
    _MARKET_CACHE.clear()
