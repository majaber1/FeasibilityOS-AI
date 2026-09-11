"""Knowledge document quality scoring (Phase 6.1).

Scores are deterministic heuristics over extracted metadata + text.
They do not invent citations or change frozen engines.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


def score_document_quality(
    *,
    text: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    source: str = "upload",
    country: str = "SA",
) -> Dict[str, Any]:
    """Return quality score (0-100) with factor breakdown and reasons."""
    meta = dict(metadata or {})
    blob = (text or "").lower()
    reasons: List[str] = []

    # --- source reliability (0-1) ---
    source_l = (source or "upload").lower()
    if source_l in {"study_memory", "completed_study"}:
        source_reliability = 0.9
        reasons.append("Completed study memory (high trust)")
    elif source_l in {"verified", "official"}:
        source_reliability = 0.95
        reasons.append("Official / verified source")
    elif source_l in {"upload", "user_upload"}:
        source_reliability = 0.75
        reasons.append("Tenant-uploaded feasibility document")
    else:
        source_reliability = 0.6
        reasons.append(f"Source type: {source_l}")

    # --- document date / recency (0-1) ---
    year = meta.get("year")
    try:
        year_i = int(year) if year is not None else None
    except (TypeError, ValueError):
        year_i = None
    current = datetime.utcnow().year
    if year_i and 1990 <= year_i <= current + 1:
        age = max(0, current - year_i)
        document_recency = max(0.35, 1.0 - age * 0.08)
        if age <= 3:
            reasons.append(f"Recent document ({year_i})")
        else:
            reasons.append(f"Document year {year_i}")
    else:
        document_recency = 0.45
        reasons.append("Document date unknown")

    # --- completeness (0-1) ---
    completeness_points = 0
    checks = [
        ("project_type", meta.get("project_type")),
        ("sector", meta.get("sector")),
        ("capex", meta.get("capex")),
        ("opex", meta.get("opex")),
        ("assumptions", meta.get("assumptions")),
        ("outcome", meta.get("outcome")),
    ]
    for key, val in checks:
        if val:
            completeness_points += 1
    if len(blob) > 800:
        completeness_points += 1
    if any(k in blob for k in ("risk", "مخاطر", "sensitivity")):
        completeness_points += 1
    completeness = min(1.0, completeness_points / 8.0)
    if completeness >= 0.6:
        reasons.append("Structured metadata reasonably complete")

    # --- financial detail (0-1) ---
    fin = 0.2
    if meta.get("capex"):
        fin += 0.25
        reasons.append("Financial model / CAPEX available")
    if meta.get("opex"):
        fin += 0.15
    if any(k in blob for k in ("irr", "npv", "payback", "dcf", "cash flow", "roi")):
        fin += 0.2
        reasons.append("Financial metrics present in text")
    if any(k in blob for k in ("revenue", "إيراد", "ebitda")):
        fin += 0.1
    financial_detail = min(1.0, fin)

    # --- outcome availability (0-1) ---
    outcome = meta.get("outcome")
    if isinstance(outcome, dict) and outcome:
        outcome_availability = 0.9
        reasons.append("Has final decision / outcome")
    elif any(k in blob for k in ("go with", "defer", "no-go", "outcome:", "decision:", "توصية", "قرار")):
        outcome_availability = 0.7
        reasons.append("Decision language detected")
    else:
        outcome_availability = 0.25

    # --- geography bonus for KSA focus ---
    geo = 0.7
    if (country or "").upper() in {"SA", "KSA", "SAUDI"} or any(
        k in blob for k in ("saudi", "riyadh", "jeddah", "dammam", "neom", "السعودية", "الرياض")
    ):
        geo = 0.95
        reasons.append("Saudi project context")

    confidence = (
        0.22 * source_reliability
        + 0.15 * document_recency
        + 0.20 * completeness
        + 0.20 * financial_detail
        + 0.15 * outcome_availability
        + 0.08 * geo
    )
    score_pct = int(round(max(0.0, min(1.0, confidence)) * 100))

    return {
        "quality_score": score_pct,
        "quality_confidence": round(confidence, 3),
        "factors": {
            "source_reliability": round(source_reliability, 3),
            "document_recency": round(document_recency, 3),
            "completeness": round(completeness, 3),
            "financial_detail": round(financial_detail, 3),
            "outcome_availability": round(outcome_availability, 3),
            "geography_relevance": round(geo, 3),
        },
        "document_year": year_i,
        "reasons": reasons[:8],
    }
