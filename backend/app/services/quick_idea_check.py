"""
Deterministic Quick Idea Check classifier (Entry 1: "لدي فكرة مشروع").

No AI, no invented percentages. A transparent, rule-based classification of
how ready a one-sentence idea is to proceed, based only on what the user
supplied and how much evidence/assumption coverage the study already has.
A later AI Advisor phase may add narrative explanation on top of this
output -- it must never replace this deterministic classification.
"""
from __future__ import annotations

from typing import Optional

STATUS_VALUES = ("PROMISING", "NEEDS_VALIDATION", "INSUFFICIENT_DATA", "HIGH_UNCERTAINTY")

# Deterministic bilingual keyword -> industry classification. Matches the
# Project.industry values already used across the app. First match wins.
# This is a coarse heuristic for routing/labeling only -- it is never
# presented as a verified sector determination.
_INDUSTRY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("education", ("حضانة", "روضة", "مدرسة", "تعليم", "تدريب", "nursery", "school", "education", "training")),
    ("healthcare", ("عيادة", "صحة", "طبي", "صيدلية", "clinic", "health", "medical", "pharmacy")),
    ("food", ("مطعم", "كافيه", "مقهى", "أطعمة", "restaurant", "cafe", "food", "catering")),
    ("retail", ("متجر", "محل", "بيع بالتجزئة", "retail", "store", "shop")),
    ("tourism", ("سياحة", "فندق", "ضيافة", "tourism", "hotel", "hospitality")),
    ("industrial", ("مصنع", "تصنيع", "صناعي", "factory", "manufacturing", "industrial")),
    ("technology", ("تطبيق", "برمجة", "تقنية", "منصة", "app", "software", "tech", "platform")),
]

# Coarse, non-authoritative regulatory-complexity hint per industry. A
# routing signal only -- actual licensing requirements come from the
# Licensing phase, sourced from official registries, never from this table.
_REGULATORY_COMPLEXITY_HINT = {
    "education": "higher",
    "healthcare": "higher",
    "food": "moderate",
    "industrial": "moderate",
    "tourism": "moderate",
    "retail": "lower",
    "technology": "lower",
}


def classify_industry(idea_text: str) -> Optional[str]:
    text = idea_text.lower()
    for industry, keywords in _INDUSTRY_KEYWORDS:
        if any(keyword.lower() in text for keyword in keywords):
            return industry
    return None


def regulatory_complexity_hint(industry: Optional[str]) -> str:
    return _REGULATORY_COMPLEXITY_HINT.get(industry or "", "unknown")


def missing_critical_fields(
    city: Optional[str], estimated_capital: Optional[float], customer_segment: Optional[str]
) -> list[str]:
    missing = []
    if not city:
        missing.append("city")
    if not estimated_capital or estimated_capital <= 0:
        missing.append("estimated_capital")
    if not customer_segment:
        missing.append("customer_segment")
    return missing


def classify_status(missing_fields: list[str], evidence_count: int, assumption_count: int) -> str:
    if missing_fields:
        return "INSUFFICIENT_DATA"
    if evidence_count == 0:
        return "HIGH_UNCERTAINTY"
    if assumption_count == 0:
        return "NEEDS_VALIDATION"
    return "PROMISING"


def recommended_next_step(status: str, missing_fields: list[str], evidence_count: int) -> str:
    if missing_fields:
        return "Provide the missing fields: " + ", ".join(missing_fields)
    if evidence_count == 0:
        return "Add at least one Saudi evidence source to the study before proceeding."
    if status == "NEEDS_VALIDATION":
        return "Record explicit assumptions (rent, capacity, pricing) before running the financial model."
    return "Proceed to the financial model and scenarios."


def build_check(
    *,
    idea_text: str,
    city: Optional[str],
    region: Optional[str],
    estimated_capital: Optional[float],
    customer_segment: Optional[str],
    goal: Optional[str],
    is_existing_business: bool,
    evidence_count: int,
    assumption_count: int,
) -> dict:
    industry = classify_industry(idea_text)
    missing = missing_critical_fields(city, estimated_capital, customer_segment)
    known = [
        name
        for name, value in (
            ("city", city),
            ("region", region),
            ("estimated_capital", estimated_capital),
            ("customer_segment", customer_segment),
            ("goal", goal),
        )
        if value
    ]
    status = classify_status(missing, evidence_count, assumption_count)
    uncertainties = list(missing)
    if evidence_count == 0:
        uncertainties.append("no market evidence attached yet")
    if assumption_count == 0:
        uncertainties.append("no explicit assumptions recorded yet")

    return {
        "status": status,
        "industry_guess": industry,
        "regulatory_complexity_hint": regulatory_complexity_hint(industry),
        "known_fields": known,
        "missing_fields": missing,
        "evidence_coverage": evidence_count,
        "assumption_coverage": assumption_count,
        "main_uncertainties": uncertainties,
        "recommended_next_step": recommended_next_step(status, missing, evidence_count),
    }
