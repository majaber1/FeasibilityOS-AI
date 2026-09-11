"""Archetype-bound catalogs for discovery, assumptions, risk, and finance.

Validation finding (2026-09-10): only saas_digital / real_estate / data_center had
question catalogs. Uber-like ride-hailing classified as `services` with an empty
catalog, so the LLM free-formed SaaS CAC/LTV questions. Downstream agents also
ignored archetype beyond a context string, and the financial fallback was
marketplace-only.

This module is the single source of truth for type-adaptive workflow binding.
"""
from __future__ import annotations

from typing import Any

# SaaS markers that must NOT appear in non-SaaS catalogs (CI / validation).
SAAS_MARKERS = (
    "cac",
    "ltv",
    "churn",
    "mrr",
    "arr",
    "subscription price",
    "customer acquisition cost",
    "lifetime value",
    "monthly recurring",
)

ARCHETYPE_QUESTIONS: dict[str, dict[str, list[str]]] = {
    "saas_digital": {
        "ar": [
            "ما سعر الاشتراك الشهري أو السنوي؟",
            "كم عدد العملاء المستهدفين في السنة الأولى؟",
            "ما تكلفة اكتساب العميل الواحد (CAC)؟",
            "ما نسبة التسرب الشهري المتوقعة (Churn)?",
            "ما التكلفة الشهرية للبنية التحتية والـ API؟",
            "ما حجم الفريق والتكلفة التشغيلية؟",
        ],
        "en": [
            "What is the monthly or annual subscription price?",
            "How many customers targeted in year 1?",
            "What is your expected Customer Acquisition Cost (CAC)?",
            "What is your expected monthly churn rate?",
            "What are your monthly infrastructure and API costs?",
            "What is your team size and operational cost?",
        ],
    },
    "real_estate": {
        "ar": [
            "هل الأرض مملوكة أم مستأجرة؟ وما مساحتها؟",
            "ما حالة الرخصة والتصاريح؟",
            "ما تكلفة البناء الإجمالية (BOQ)؟",
            "ما عدد الوحدات وأنواعها؟",
            "ما نسبة الإنجاز الحالية؟",
            "ما متوسط سعر البيع أو الإيجار المستهدف للوحدة؟",
        ],
        "en": [
            "Is the land owned or leased? What is the area?",
            "What is the license and permit status?",
            "What is the total construction cost (BOQ)?",
            "How many units and what types?",
            "What is the current completion percentage?",
            "What is the target sale or rent price per unit?",
        ],
    },
    "data_center": {
        "ar": [
            "ما سعة الطاقة الكهربائية (ميجاواط)؟",
            "ما Tier المستهدف (I/II/III/IV)؟",
            "ما PUE المستهدف؟",
            "ما سعة Rack الإجمالية؟",
            "ما نسبة الإشغال المستهدفة في السنة الأولى؟",
            "ما تكلفة الكيلوواط ساعة؟",
            "ما نموذج الإيراد (Colocation/Wholesale/Retail)?",
        ],
        "en": [
            "What is the power capacity (MW)?",
            "What Tier is targeted (I/II/III/IV)?",
            "What is the target PUE?",
            "What is total Rack capacity?",
            "What is target occupancy in year 1?",
            "What is the cost per kWh?",
            "What is the revenue model (Colocation/Wholesale/Retail)?",
        ],
    },
    "services": {
        "ar": [
            "ما نموذج الإيراد (عمولة، اشتراك تشغيلي، رسوم ثابتة)؟",
            "ما متوسط قيمة المعاملة أو الرحلة؟",
            "ما نسبة العمولة / take-rate المتوقعة؟",
            "ما حجم المعاملات أو الرحلات المستهدف شهرياً في السنة الأولى؟",
            "ما تكلفة اكتساب المزوّد أو السائق وتكلفة اكتساب العميل؟",
            "ما المتطلبات التنظيمية والتراخيص (مثل هيئة النقل)؟",
            "ما الاستثمار الأولي وتوزيع الميزانية (منتج، تسويق، تشغيل، امتثال)؟",
        ],
        "en": [
            "What is the revenue model (commission, operating subscription, fixed fees)?",
            "What is the average transaction or trip value?",
            "What commission / take-rate do you expect?",
            "What monthly transaction or ride volume is targeted in year 1?",
            "What are provider/driver acquisition cost and rider acquisition cost?",
            "What regulatory licenses are required (e.g. Transport General Authority)?",
            "What is the seed investment split (product, marketing, ops, compliance)?",
        ],
    },
    "retail": {
        "ar": [
            "ما موقع المتجر ومساحة البيع؟",
            "ما متوسط قيمة السلة وعدد الزيارات اليومية المتوقعة؟",
            "ما تكلفة المخزون الافتتاحي ودوران المخزون؟",
            "ما الإيجار السنوي وتكاليف التشغيل؟",
            "ما هامش الربح الإجمالي المستهدف؟",
            "ما خطة المبيعات عبر القنوات (متجر / أونلاين / جملة)؟",
        ],
        "en": [
            "What is the store location and selling floor area?",
            "What is expected average basket size and daily footfall?",
            "What is opening inventory cost and inventory turns?",
            "What are annual rent and operating costs?",
            "What is the target gross margin?",
            "What is the channel mix (store / online / wholesale)?",
        ],
    },
    "industrial": {
        "ar": [
            "ما الطاقة الإنتاجية السنوية المستهدفة؟",
            "ما تكلفة الآلات والتركيب (CAPEX الصناعي)؟",
            "ما تكلفة المواد الخام لكل وحدة؟",
            "ما تكلفة العمالة والطاقة لكل وحدة؟",
            "ما نسبة استغلال الطاقة المتوقعة؟",
            "ما شهادات الجودة والتراخيص الصناعية المطلوبة؟",
        ],
        "en": [
            "What is the target annual production capacity?",
            "What is machinery and installation CAPEX?",
            "What is raw material cost per unit?",
            "What are labor and energy costs per unit?",
            "What plant utilization rate do you expect?",
            "What quality certifications and industrial permits are required?",
        ],
    },
    "franchise": {
        "ar": [
            "ما رسوم الامتياز الأولية والإتاوة المستمرة؟",
            "ما متطلبات المساحة والموقع من مانح الامتياز؟",
            "ما تكلفة التأسيس والديكور والتجهيز؟",
            "ما المبيعات المتوقعة للوحدة في السنة الأولى؟",
            "ما مدة عقد الامتياز وشروط التجديد؟",
            "ما الدعم التشغيلي والتسويقي المقدم من المانح؟",
        ],
        "en": [
            "What are the initial franchise fee and ongoing royalty?",
            "What space and location requirements does the franchisor set?",
            "What are fit-out and equipment setup costs?",
            "What year-1 unit sales are expected?",
            "What is the franchise term and renewal conditions?",
            "What operating and marketing support does the franchisor provide?",
        ],
    },
}

# Required assumption keys the assumptions agent must cover for each archetype.
ARCHETYPE_ASSUMPTION_KEYS: dict[str, list[str]] = {
    "saas_digital": [
        "monthly_subscription_price",
        "year1_customers",
        "cac",
        "monthly_churn",
        "monthly_infra_cost",
        "monthly_opex",
        "initial_investment",
    ],
    "real_estate": [
        "land_cost",
        "construction_boq",
        "unit_count",
        "asp_per_unit",
        "annual_absorption_units",
        "sales_period_years",
        "initial_investment",
    ],
    "data_center": [
        "it_load_mw",
        "price_per_kw_month",
        "year1_occupancy",
        "pue",
        "power_tariff_per_kwh",
        "annual_opex",
        "initial_investment",
    ],
    "services": [
        "average_trip_value",
        "take_rate",
        "monthly_rides_year1",
        "driver_acquisition_cost",
        "promo_burn_pct",
        "monthly_fixed_opex",
        "initial_investment",
    ],
    "retail": [
        "avg_basket_size",
        "daily_transactions",
        "gross_margin",
        "annual_rent",
        "inventory_investment",
        "monthly_opex",
        "initial_investment",
    ],
    "industrial": [
        "annual_capacity_units",
        "utilization_rate",
        "price_per_unit",
        "variable_cost_per_unit",
        "fixed_annual_opex",
        "machinery_capex",
        "initial_investment",
    ],
    "franchise": [
        "franchise_fee",
        "royalty_rate",
        "fitout_cost",
        "year1_sales",
        "gross_margin",
        "monthly_opex",
        "initial_investment",
    ],
}

# Risk themes the risk agent must prioritize (not SaaS-generic).
ARCHETYPE_RISK_THEMES: dict[str, list[str]] = {
    "saas_digital": [
        "churn and retention",
        "CAC payback",
        "product-market fit",
        "cloud cost overrun",
        "data protection (PDPL)",
    ],
    "real_estate": [
        "absorption / sell-through",
        "construction cost inflation",
        "permit and Wafi delays",
        "mortgage rate shock",
        "off-plan default risk",
    ],
    "data_center": [
        "grid interconnection delay",
        "power tariff changes",
        "hyperscaler self-build competition",
        "PUE / cooling failure",
        "ESG and water constraints",
    ],
    "services": [
        "regulatory licensing (TGA / sector)",
        "supply-side acquisition (drivers/providers)",
        "subsidy / price wars",
        "safety and insurance",
        "unit economics and cash runway",
    ],
    "retail": [
        "footfall shortfall",
        "inventory obsolescence",
        "rent escalation",
        "shrinkage",
        "e-commerce competition",
    ],
    "industrial": [
        "utilization below plan",
        "raw material price volatility",
        "export / logistics disruption",
        "quality compliance",
        "energy cost spikes",
    ],
    "franchise": [
        "franchisor policy change",
        "territory cannibalization",
        "royalty burden",
        "brand reputation events",
        "fit-out overrun",
    ],
}

RECOMMENDED_MODEL: dict[str, str] = {
    "saas_digital": "saas_v1",
    "real_estate": "real_estate_v1",
    "data_center": "data_center_v1",
    "services": "marketplace_services_v1",
    "retail": "retail_v1",
    "industrial": "industrial_v1",
    "franchise": "franchise_v1",
    "unknown": "general_v1",
}


def questions_for(archetype: str, lang: str = "en") -> list[str]:
    return list(ARCHETYPE_QUESTIONS.get(archetype, {}).get(lang, []))


def assumption_keys_for(archetype: str) -> list[str]:
    return list(ARCHETYPE_ASSUMPTION_KEYS.get(archetype, ARCHETYPE_ASSUMPTION_KEYS.get("services", [])))


def risk_themes_for(archetype: str) -> list[str]:
    return list(ARCHETYPE_RISK_THEMES.get(archetype, []))


def recommended_model_for(archetype: str) -> str:
    return RECOMMENDED_MODEL.get(archetype, "general_v1")


def saas_marker_hits(texts: list[str]) -> list[str]:
    hits: list[str] = []
    for t in texts:
        low = (t or "").lower()
        for m in SAAS_MARKERS:
            if m in low:
                hits.append(f"{m} :: {t[:160]}")
    return hits


def assumption_prompt_block(archetype: str, lang: str = "en") -> str:
    keys = assumption_keys_for(archetype)
    if not keys:
        return ""
    key_lines = "\n".join(f"- {k}" for k in keys)
    if lang == "ar":
        return (
            f"\n\nهذا المشروع من نوع ({archetype}). يجب أن تغطي الافتراضات هذه المفاتيح "
            f"(أسماء المفاتيح بالإنجليزية كما هي):\n{key_lines}\n"
            "لا تستخدم افتراضات SaaS (CAC/LTV/Churn/MRR) إلا إذا كان النوع saas_digital."
        )
    return (
        f"\n\nThis project archetype is ({archetype}). Assumptions MUST cover these keys "
        f"(use these exact key names where possible):\n{key_lines}\n"
        "Do NOT use SaaS assumptions (CAC/LTV/Churn/MRR) unless archetype is saas_digital."
    )


def risk_prompt_block(archetype: str, lang: str = "en") -> str:
    themes = risk_themes_for(archetype)
    if not themes:
        return ""
    lines = "\n".join(f"- {t}" for t in themes)
    if lang == "ar":
        return f"\n\nركّز مخاطر هذا المشروع ({archetype}) على:\n{lines}\n"
    return f"\n\nPrioritize risks for archetype ({archetype}):\n{lines}\n"


def discovery_prompt_hardening(lang: str = "en") -> str:
    """Extra system rules appended to discovery to prevent SaaS bleed."""
    if lang == "ar":
        return (
            "\n\nقاعدة إضافية: اسأل فقط أسئلة مناسبة لنوع المشروع. "
            "للعقارات: أرض/BOQ/سعر الوحدة/الامتصاص. "
            "لمراكز البيانات: ميغاواط/PUE/سعر الكيلوواط. "
            "للخدمات/المنصات السوقية: قيمة المعاملة/العمولة/حجم المعاملات/تراخيص القطاع. "
            "لا تسأل عن CAC أو LTV أو Churn أو الاشتراك الشهري إلا لمشاريع SaaS الرقمية."
        )
    return (
        "\n\nAdditional rule: ask ONLY questions appropriate to this project type. "
        "Real estate: land/BOQ/ASP/absorption. "
        "Data center: MW/PUE/kW pricing. "
        "Services/marketplaces: trip or transaction value/take-rate/volume/sector licenses. "
        "Do NOT ask about CAC, LTV, Churn, or subscription pricing unless the project is digital SaaS."
    )


def catalog_snapshot() -> dict[str, Any]:
    return {
        "archetypes_with_questions": sorted(ARCHETYPE_QUESTIONS.keys()),
        "assumption_key_sets": {k: v for k, v in ARCHETYPE_ASSUMPTION_KEYS.items()},
        "risk_themes": {k: v for k, v in ARCHETYPE_RISK_THEMES.items()},
        "recommended_models": dict(RECOMMENDED_MODEL),
    }
