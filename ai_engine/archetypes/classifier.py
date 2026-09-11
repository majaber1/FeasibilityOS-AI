"""Mandatory project archetype classification (deterministic + LLM-assistable)."""
from __future__ import annotations

import re
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

    # Strong SaaS signals win early so phrases like "not real estate" do not hijack.
    # Ignore negated mentions ("not a saas", "not saas").
    t_saas = re.sub(r"\bnot\s+(a\s+)?(saas|subscription)\b", " ", t)
    strong_saas = (
        "saas", "subscription", " arr", " mrr", "churn", " cac", " ltv",
        "b2b software", "software platform", "api product", "crm software",
        "اشتراك", "برمجيات كخدمة",
    )
    # Word-ish checks: require saas/subscription as tokens after negation scrub.
    if re.search(r"\b(saas|subscription|arr|mrr|churn|cac|ltv)\b", t_saas) or any(
        k in t_saas for k in ("b2b software", "software platform", "api product", "crm software", "اشتراك", "برمجيات كخدمة")
    ):
        return "saas_digital"

    # Professional / managed services before DC / industrial so phrases like
    # "not a data center" or "SOC services" never hijack into data_center.
    services_kw = (
        "uber", "careem", "ride", "hailing", "ride-hailing", "rideshare", "taxi",
        "driver", "take rate", "take-rate", "marketplace", "delivery platform",
        "خدمة", "توصيل", "سائق", "مشاوير",
        "consulting", "consultancy", "cybersecurity", "cyber security",
        "professional services", "managed services", "managed security",
        "retainer", "advisory", "services company", "service business",
        "agency", "soc ", " mssp", "penetration test", "استشارات", "خدمات مهنية",
        "billable consultants", "managed soc",
    )
    if any(k in t for k in services_kw):
        return "services"

    # Ignore negated DC mentions ("not a data center", "ليس مركز بيانات").
    t_dc = re.sub(
        r"\bnot\s+(a\s+)?(data[\s\-]?center|datacenter|colo(?:cation)?)\b",
        " ",
        t,
    )
    t_dc = re.sub(r"ليس\s+(مركز\s*بيانات)", " ", t_dc)
    dc_kw = (
        "data center", "datacenter", "مركز بيانات", "rack", "racks", "ميجاواط", "mw ",
        "pue", "colocation", "colo", "hyperscaler", "tier iii", "tier 3", "power capacity",
    )
    if any(k in t_dc for k in dc_kw):
        return "data_center"

    re_kw = (
        "residential", "real estate", "سكني", "عقار", "مجمع", "وحدات", "villas",
        "construction", "بناء", "compound", "مجمع سكني", "boq", "land cost", "wafi",
        "off-plan", "gated", "apartment", "apartments",
    )
    if any(k in t for k in re_kw):
        return "real_estate"

    industrial_kw = (
        "factory", "manufacturing", "industrial", "مصنع", "تصنيع",
        "production capacity", "raw material", "machinery", "plant utilization",
        "food plant", "manufacturing plant", "production plant",
    )
    if any(k in t for k in industrial_kw):
        return "industrial"
    # Arabic "production" alone is industrial-leaning when not already services.
    if "إنتاج" in t and not any(k in t for k in ("خدمة", "استشارات")):
        return "industrial"

    retail_kw = (
        "retail", "store", "shop", "trading", "تجزئة", "متجر", "inventory",
        "point of sale", "sku", "wholesale trading",
    )
    if any(k in t for k in retail_kw):
        return "retail"

    saas_kw = (
        "saas", "subscription", "arr", "mrr", "churn", "b2b software",
        "اشتراك", "برمجيات كخدمة", "software platform", "whatsapp ai",
        "crm software", "api product", "ai compliance", "compliance platform",
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
