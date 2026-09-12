"""Market Research Planner — classify needs and select governed sources only."""

from __future__ import annotations

from typing import Any  # noqa: F401 — used by extract_market_context_from_state

from ai_engine.research.market.schemas import (
    ALL_MARKET_SOURCES,
    LIVE_MARKET_SOURCES,
    PLACEHOLDER_MARKET_SOURCES,
    MarketResearchPlan,
    ResearchType,
)

_TYPE_KEYWORDS: dict[ResearchType, tuple[str, ...]] = {
    "COMPETITOR": (
        "competitor",
        "competition",
        "rival",
        "players",
        "who competes",
        "competitive",
        "market players",
    ),
    "MARKET_SIZE": (
        "market size",
        "tam",
        "sam",
        "som",
        "market value",
        "market volume",
        "addressable market",
    ),
    "PRICING": (
        "pricing",
        "price",
        "fee",
        "tariff",
        "arpu",
        "subscription fee",
        "cost to customer",
    ),
    "REGULATION": (
        "regulation",
        "regulatory",
        "license",
        "compliance",
        "law",
        "authority",
        "permit",
        "sama",
        "zatca",
        "nca",
    ),
    "SECTOR_SIGNAL": (
        "sector",
        "industry",
        "trend",
        "indicator",
        "growth",
        "gdp",
        "inflation",
        "fdi",
        "investment climate",
        "economic",
    ),
}

_SOURCE_FOR_TYPE: dict[ResearchType, tuple[str, ...]] = {
    "COMPETITOR": (),  # no live competitor connector — evidence-only / NOT_FOUND
    "MARKET_SIZE": ("gastat", "misa"),
    "PRICING": (),  # official pages / user evidence only — no guessed prices
    "REGULATION": ("sama", "zatca", "nca"),  # placeholders only in 8B
    "SECTOR_SIGNAL": ("gastat", "misa"),
}


def classify_research_types(*texts: str) -> list[ResearchType]:
    """Return ordered research types matching free-text gaps / idea / sector."""
    blob = " ".join(t for t in texts if t).lower()
    matched: list[ResearchType] = []
    for rtype, keywords in _TYPE_KEYWORDS.items():
        if any(k in blob for k in keywords):
            matched.append(rtype)
    if not matched:
        # Default controlled set for Saudi market studies
        matched = ["SECTOR_SIGNAL", "COMPETITOR", "MARKET_SIZE"]
    # Preserve order, unique
    seen: set[str] = set()
    out: list[ResearchType] = []
    for t in matched:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def select_sources(research_types: list[ResearchType]) -> tuple[list[str], list[str]]:
    """
    Select governed sources only.

    Returns (live_or_selected, placeholders_noted).
    Never invents arbitrary URLs. Never enables Monsha'at.
    """
    selected: list[str] = []
    placeholders: list[str] = []
    for rtype in research_types:
        for key in _SOURCE_FOR_TYPE.get(rtype, ()):
            if key in PLACEHOLDER_MARKET_SOURCES:
                if key not in placeholders:
                    placeholders.append(key)
            elif key in LIVE_MARKET_SOURCES:
                if key not in selected:
                    selected.append(key)
            elif key in ALL_MARKET_SOURCES and key not in selected:
                selected.append(key)
    # Sector/market research always prefers live official stats when no source matched
    if not selected and any(t in {"SECTOR_SIGNAL", "MARKET_SIZE"} for t in research_types):
        selected = list(LIVE_MARKET_SOURCES)
    return selected, placeholders


def build_market_plan(
    *,
    study_id: str,
    business_idea: str = "",
    sector: str = "",
    geography: str = "Saudi Arabia",
    gaps: list[str] | None = None,
    extra_queries: list[str] | None = None,
) -> MarketResearchPlan:
    gap_text = " ".join(gaps or [])
    types = classify_research_types(business_idea, sector, geography, gap_text)
    selected, placeholders = select_sources(types)

    queries: list[str] = []
    if sector:
        queries.append(f"{sector} sector indicators {geography}")
    if business_idea:
        queries.append(f"{business_idea} market context {geography}")
    for g in gaps or []:
        if g and g not in queries:
            queries.append(g)
    for q in extra_queries or []:
        if q and q not in queries:
            queries.append(q)
    if not queries:
        queries.append(f"Official market and investment indicators for {geography}")

    reasons: list[str] = [
        f"Research types: {', '.join(types)}",
        f"Live sources: {', '.join(selected) or 'none'}",
    ]
    if placeholders:
        reasons.append(
            f"Placeholder authorities (not connected): {', '.join(placeholders)}"
        )
    if "COMPETITOR" in types:
        reasons.append(
            "Competitor intelligence requires sourced evidence; never invents names"
        )
    if "PRICING" in types:
        reasons.append("Pricing requires official/user evidence; no LLM price guesses")

    return MarketResearchPlan(
        study_id=study_id,
        business_idea=business_idea or "",
        sector=sector or "",
        geography=geography or "Saudi Arabia",
        research_types=types,
        selected_sources=selected,
        placeholder_sources=placeholders,
        queries=queries,
        reasons=reasons,
    )


def extract_market_context_from_state(state: Any) -> dict[str, Any]:
    """Derive business idea / sector / geography / gaps from StudyState-like object."""
    if isinstance(state, dict):
        profile = state.get("profile") or {}
        answers = state.get("structured_answers") or {}
        study_id = str(state.get("study_id") or "unknown")
        gaps = list(state.get("missing_information") or [])
        if isinstance(profile, dict):
            sector = str(profile.get("sector") or "")
            missing = list(profile.get("missing_information") or [])
            idea = str(
                profile.get("decision_goal")
                or answers.get("business_idea")
                or answers.get("idea")
                or sector
                or ""
            )
        else:
            sector = str(getattr(profile, "sector", "") or "")
            missing = list(getattr(profile, "missing_information", None) or [])
            idea = str(
                getattr(profile, "decision_goal", "")
                or (answers.get("business_idea") if isinstance(answers, dict) else "")
                or sector
            )
        gaps = gaps or missing
    else:
        profile = getattr(state, "profile", None)
        answers = getattr(state, "structured_answers", None) or {}
        study_id = str(getattr(state, "study_id", None) or "unknown")
        sector = str(getattr(profile, "sector", "") or "") if profile else ""
        missing = (
            list(getattr(profile, "missing_information", None) or []) if profile else []
        )
        idea = str(
            (getattr(profile, "decision_goal", "") if profile else "")
            or (answers.get("business_idea") if isinstance(answers, dict) else "")
            or sector
        )
        gaps = missing

    geography = "Saudi Arabia"
    if isinstance(answers, dict):
        city = str(answers.get("city") or answers.get("location") or "").strip()
        if city:
            geography = f"{city}, Saudi Arabia"

    return {
        "study_id": study_id,
        "business_idea": idea,
        "sector": sector,
        "geography": geography,
        "gaps": [str(g) for g in gaps if g],
    }
