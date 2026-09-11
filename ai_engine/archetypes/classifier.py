"""Mandatory project archetype classification (deterministic + LLM-assistable)."""
from __future__ import annotations

from typing import Any

SUPPORTED_ARCHETYPES = (
    "saas_digital",
    "real_estate",
    "data_center",
    "industrial",
    "retail",
    "services",
    "other",
)

ARCHETYPE_LABELS: dict[str, dict[str, str]] = {
    "saas_digital": {"en": "SaaS / Digital Platform", "ar": "برمجيات / منصة رقمية"},
    "real_estate": {"en": "Real Estate Development", "ar": "تطوير عقاري"},
    "data_center": {"en": "Data Center / Infrastructure", "ar": "مركز بيانات / بنية تحتية"},
    "industrial": {"en": "Industrial / Manufacturing", "ar": "صناعي / تصنيع"},
    "retail": {"en": "Retail / Trading", "ar": "تجزئة / تجارة"},
    "services": {"en": "Service Business", "ar": "أعمال خدمية"},
    "other": {"en": "Other", "ar": "أخرى"},
}


def classify_archetype(text: str) -> str:
    """Keyword heuristic to stabilize golden scenarios when LLM is unavailable."""
    t = (text or "").lower()

    dc_kw = (
        "data center", "datacenter", "مركز بيانات", "rack", "racks", "ميجاواط", "mw ",
        "pue", "colocation", "colo", "hyperscaler", "tier iii", "tier 3", "power capacity",
    )
    if any(k in t for k in dc_kw):
        return "data_center"

    re_kw = (
        "residential", "real estate", "سكني", "عقار", "مجمع", "وحدات", "villas",
        "construction", "بناء", "compound", "مجمع سكني", "boq", "land cost", "wafi",
        "off-plan", "gated",
    )
    if any(k in t for k in re_kw):
        return "real_estate"

    industrial_kw = (
        "factory", "manufacturing", "industrial", "مصنع", "تصنيع", "إنتاج",
        "production capacity", "raw material", "utilization", "machinery",
    )
    if any(k in t for k in industrial_kw):
        return "industrial"

    retail_kw = (
        "retail", "store", "shop", "trading", "تجزئة", "متجر", "inventory",
        "point of sale", "sku", "wholesale trading",
    )
    if any(k in t for k in retail_kw):
        return "retail"

    # Ride-hailing / marketplace mobility → services (NOT pure SaaS subscription)
    services_kw = (
        "uber", "careem", "ride", "hailing", "ride-hailing", "rideshare", "taxi",
        "driver", "take rate", "take-rate", "marketplace", "delivery platform",
        "خدمة", "توصيل", "سائق", "مشاوير",
    )
    if any(k in t for k in services_kw):
        return "services"

    saas_kw = (
        "saas", "subscription", "arr", "mrr", "churn", "b2b software",
        "اشتراك", "برمجيات كخدمة", "software platform", "whatsapp ai",
        "crm software", "api product",
    )
    if any(k in t for k in saas_kw):
        return "saas_digital"

    return "other"


def normalize_archetype(value: str | None) -> str:
    raw = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "saas": "saas_digital",
        "saas_digital": "saas_digital",
        "digital": "saas_digital",
        "digital_platform": "saas_digital",
        "realestate": "real_estate",
        "real_estate": "real_estate",
        "property": "real_estate",
        "datacenter": "data_center",
        "data_center": "data_center",
        "infrastructure": "data_center",
        "manufacturing": "industrial",
        "industrial": "industrial",
        "retail": "retail",
        "trading": "retail",
        "service": "services",
        "services": "services",
        "service_business": "services",
        "franchise": "other",
        "unknown": "other",
        "other": "other",
    }
    mapped = aliases.get(raw, raw)
    return mapped if mapped in SUPPORTED_ARCHETYPES else "other"


def classification_payload(language: str = "en") -> list[dict[str, Any]]:
    lang = "ar" if language == "ar" else "en"
    return [
        {"id": key, "label": ARCHETYPE_LABELS[key][lang], "label_en": ARCHETYPE_LABELS[key]["en"]}
        for key in SUPPORTED_ARCHETYPES
    ]
