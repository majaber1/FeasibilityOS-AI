"""Research Planner — maps study gaps to Phase 8A live / blocked sources."""

from __future__ import annotations

from typing import Any

from ai_engine.research.schemas import ResearchPlan, ResearchSourceRef

# Phase 8A live governed sources (post MISA merge). Monsha'at is blocked.
PHASE8A_LIVE_SOURCES: dict[str, dict[str, Any]] = {
    "gastat": {
        "connector_id": "live.gastat",
        "gap_keywords": (
            "inflation",
            "cpi",
            "gdp",
            "unemployment",
            "labor",
            "population",
            "statistics",
            "indicator",
            "macro",
            "economic indicator",
            "consumer price",
        ),
    },
    "misa": {
        "connector_id": "live.misa",
        "gap_keywords": (
            "investment",
            "fdi",
            "foreign direct",
            "investor",
            "license",
            "misa",
            "inflow",
            "capital inflow",
            "investment climate",
        ),
    },
}

BLOCKED_SOURCES: dict[str, dict[str, Any]] = {
    "monshaat": {
        "connector_id": "live.monshaat",
        "reason": "BLOCKED_EXTERNAL_REACHABILITY",
        "gap_keywords": (
            "sme",
            "msme",
            "monshaat",
            "small business",
            "medium enterprise",
            "entrepreneur",
        ),
    },
}


def classify_gap(gap: str) -> list[str]:
    """Return source keys relevant to a gap string (may include blocked)."""
    text = (gap or "").lower()
    matched: list[str] = []
    for key, meta in PHASE8A_LIVE_SOURCES.items():
        if any(k in text for k in meta["gap_keywords"]):
            matched.append(key)
    for key, meta in BLOCKED_SOURCES.items():
        if any(k in text for k in meta["gap_keywords"]):
            matched.append(key)
    if not matched:
        matched = ["gastat", "misa"]
    return matched


def build_research_plan(
    *,
    study_id: str,
    gaps: list[str],
    queries: list[str] | None = None,
) -> ResearchPlan:
    source_keys: list[str] = []
    for gap in gaps:
        for key in classify_gap(gap):
            if key not in source_keys:
                source_keys.append(key)

    if not source_keys and not gaps:
        source_keys = ["gastat", "misa"]

    sources: list[ResearchSourceRef] = []
    for key in source_keys:
        if key in BLOCKED_SOURCES:
            meta = BLOCKED_SOURCES[key]
            sources.append(
                ResearchSourceRef(
                    source_key=key,
                    connector_id=str(meta["connector_id"]),
                    reason=f"Gap matched blocked source {key}",
                    status="blocked",
                    blocked=True,
                    block_reason=str(meta["reason"]),
                )
            )
        else:
            meta = PHASE8A_LIVE_SOURCES[key]
            sources.append(
                ResearchSourceRef(
                    source_key=key,
                    connector_id=str(meta["connector_id"]),
                    reason=f"Phase 8A live source for gaps: {', '.join(gaps) or 'default'}",
                    status="planned",
                    blocked=False,
                )
            )

    return ResearchPlan(
        study_id=study_id,
        gaps=list(gaps),
        sources=sources,
        queries=list(queries or gaps or ["Saudi Arabia macroeconomic indicators"]),
        status="planned",
    )


def extract_gaps_from_state(state: Any) -> list[str]:
    """Derive research gaps from study profile / structured answers / claims."""
    gaps: list[str] = []

    if isinstance(state, dict):
        profile = state.get("profile") or {}
        answers = state.get("structured_answers") or {}
        existing_claims = state.get("claims") or []
        if isinstance(profile, dict):
            sector = str(profile.get("sector") or "").strip()
            archetype = str(profile.get("archetype") or "").strip()
            missing = list(profile.get("missing_information") or [])
        else:
            sector = str(getattr(profile, "sector", "") or "").strip()
            archetype = str(getattr(profile, "archetype", "") or "").strip()
            missing = list(getattr(profile, "missing_information", None) or [])
    else:
        profile = getattr(state, "profile", None)
        answers = getattr(state, "structured_answers", None) or {}
        existing_claims = getattr(state, "claims", None) or []
        sector = str(getattr(profile, "sector", "") or "").strip() if profile else ""
        archetype = str(getattr(profile, "archetype", "") or "").strip() if profile else ""
        missing = list(getattr(profile, "missing_information", None) or []) if profile else []

    if sector:
        gaps.append(f"Sector market context for {sector} in Saudi Arabia")
    else:
        gaps.append("Saudi Arabia macroeconomic and investment context")

    if archetype and archetype != "unknown":
        gaps.append(f"Official indicators relevant to {archetype.replace('_', ' ')} ventures")

    city = ""
    if isinstance(answers, dict):
        city = str(answers.get("city") or answers.get("location") or "").strip()
    if city:
        gaps.append(f"Regional economic indicators relevant to {city}")

    for m in missing[:5]:
        if m:
            gaps.append(str(m))

    if not any(
        any(k in g.lower() for k in ("inflation", "gdp", "statistic", "labor", "cpi"))
        for g in gaps
    ):
        gaps.append("Official inflation / GDP / labor statistics for Saudi Arabia")
    if not any(any(k in g.lower() for k in ("investment", "fdi", "misa")) for g in gaps):
        gaps.append("Official FDI / investment climate indicators for Saudi Arabia")

    claim_types: list[str] = []
    for c in existing_claims:
        if isinstance(c, dict):
            claim_types.append(str(c.get("source_type") or ""))
        else:
            claim_types.append(str(getattr(c, "source_type", "") or ""))
    if claim_types and all(t == "ai_assumption" for t in claim_types):
        gaps.append(
            "Replace provisional ai_assumption with official source evidence where available"
        )

    return gaps
