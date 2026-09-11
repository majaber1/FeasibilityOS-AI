"""Archetype-specific assumption schemas.

Each field defines a structured input type. SaaS-only metrics (CAC/churn/ARR/MRR)
are restricted to saas_digital and must never appear on RE/DC/industrial/retail.
"""
from __future__ import annotations

from typing import Any


# Keys that must NEVER appear on non-SaaS studies.
SAAS_LEAKAGE_KEYS = frozenset(
    {
        "cac",
        "churn",
        "arr",
        "mrr",
        "ltv",
        "saas_pricing",
        "subscription_price",
        "monthly_churn",
        "customer_acquisition_cost",
        "annual_recurring_revenue",
        "monthly_recurring_revenue",
        "churn_rate",
        "saas_customers",
    }
)


def _f(
    key: str,
    *,
    label_en: str,
    label_ar: str,
    input_type: str,
    unit: str | None = None,
    required: bool = True,
    options_en: list[str] | None = None,
    options_ar: list[str] | None = None,
    description_en: str = "",
    description_ar: str = "",
) -> dict[str, Any]:
    return {
        "key": key,
        "label_en": label_en,
        "label_ar": label_ar,
        "input_type": input_type,  # yes_no | single_select | multi_select | number | currency | percent | text
        "unit": unit,
        "required": required,
        "options_en": options_en or [],
        "options_ar": options_ar or [],
        "description_en": description_en,
        "description_ar": description_ar,
    }


SAAS_SCHEMA = [
    _f("target_customers", label_en="Target customers (year 1)", label_ar="العملاء المستهدفون (سنة 1)", input_type="number", unit="customers"),
    _f("pricing", label_en="Subscription / pricing", label_ar="التسعير / الاشتراك", input_type="currency", unit="SAR"),
    _f("arr", label_en="ARR", label_ar="الإيراد السنوي المتكرر (ARR)", input_type="currency", unit="SAR"),
    _f("mrr", label_en="MRR", label_ar="الإيراد الشهري المتكرر (MRR)", input_type="currency", unit="SAR", required=False),
    _f("cac", label_en="CAC", label_ar="تكلفة اكتساب العميل (CAC)", input_type="currency", unit="SAR"),
    _f("churn", label_en="Monthly churn", label_ar="نسبة التسرب الشهرية", input_type="percent", unit="%"),
    _f("ltv", label_en="LTV", label_ar="قيمة العميل مدى الحياة (LTV)", input_type="currency", unit="SAR", required=False),
    _f(
        "acquisition_channels",
        label_en="Acquisition channels",
        label_ar="قنوات الاكتساب",
        input_type="multi_select",
        options_en=["Paid ads", "Organic", "Partners", "Sales team", "Other"],
        options_ar=["إعلانات مدفوعة", "عضوي", "شركاء", "فريق مبيعات", "أخرى"],
    ),
]

REAL_ESTATE_SCHEMA = [
    _f("land_cost", label_en="Land cost", label_ar="تكلفة الأرض", input_type="currency", unit="SAR"),
    _f("construction_boq", label_en="Construction BOQ / hard cost", label_ar="تكلفة البناء (BOQ)", input_type="currency", unit="SAR"),
    _f("units", label_en="Number of units", label_ar="عدد الوحدات", input_type="number", unit="units"),
    _f("selling_price", label_en="Average selling price / unit", label_ar="متوسط سعر البيع للوحدة", input_type="currency", unit="SAR"),
    _f("absorption_rate", label_en="Absorption (units / year)", label_ar="معدل الامتصاص (وحدات/سنة)", input_type="number", unit="units/year"),
    _f(
        "financing",
        label_en="Financing structure",
        label_ar="هيكل التمويل",
        input_type="single_select",
        options_en=["All equity", "Bank construction loan", "Mixed (equity + debt)", "Off-plan / Wafi collections"],
        options_ar=["ملكية كاملة", "تمويل بنكي للبناء", "مختلط (ملكية + دين)", "بيع على الخارطة / وافي"],
    ),
    _f("loan_to_cost", label_en="Loan-to-cost (if debt)", label_ar="نسبة القرض إلى التكلفة", input_type="percent", unit="%", required=False),
]

DATA_CENTER_SCHEMA = [
    _f("mw_capacity", label_en="IT capacity (MW)", label_ar="سعة الطاقة (ميجاواط)", input_type="number", unit="MW"),
    _f("rack_count", label_en="Rack count", label_ar="عدد الرفوف", input_type="number", unit="racks"),
    _f("pue", label_en="Target PUE", label_ar="PUE المستهدف", input_type="number", unit="ratio"),
    _f("power_cost", label_en="Power cost", label_ar="تكلفة الطاقة", input_type="currency", unit="SAR/kWh"),
    _f("occupancy", label_en="Year-1 occupancy", label_ar="نسبة الإشغال سنة 1", input_type="percent", unit="%"),
    _f("pricing_per_kw", label_en="Pricing per kW / month", label_ar="التسعير لكل كيلوواط شهرياً", input_type="currency", unit="SAR/kW/mo"),
    _f(
        "tier",
        label_en="Target Tier",
        label_ar="المستوى المستهدف",
        input_type="single_select",
        options_en=["Tier I", "Tier II", "Tier III", "Tier IV"],
        options_ar=["Tier I", "Tier II", "Tier III", "Tier IV"],
        required=False,
    ),
]

INDUSTRIAL_SCHEMA = [
    _f("production_capacity", label_en="Annual production capacity", label_ar="الطاقة الإنتاجية السنوية", input_type="number", unit="units/year"),
    _f("raw_material_cost", label_en="Raw material cost / unit", label_ar="تكلفة المواد الخام للوحدة", input_type="currency", unit="SAR"),
    _f("unit_cost", label_en="Fully loaded unit cost", label_ar="تكلفة الوحدة الكاملة", input_type="currency", unit="SAR"),
    _f("selling_price", label_en="Selling price / unit", label_ar="سعر البيع للوحدة", input_type="currency", unit="SAR"),
    _f("utilization", label_en="Plant utilization", label_ar="نسبة التشغيل", input_type="percent", unit="%"),
    _f("capex_machinery", label_en="Machinery / plant CAPEX", label_ar="النفقات الرأسمالية للآلات", input_type="currency", unit="SAR"),
]

RETAIL_SCHEMA = [
    _f("store_count", label_en="Number of stores / outlets", label_ar="عدد الفروع", input_type="number", unit="stores"),
    _f("avg_ticket", label_en="Average ticket size", label_ar="متوسط قيمة الفاتورة", input_type="currency", unit="SAR"),
    _f("monthly_transactions", label_en="Monthly transactions / store", label_ar="المعاملات الشهرية لكل فرع", input_type="number"),
    _f("gross_margin", label_en="Gross margin", label_ar="هامش الربح الإجمالي", input_type="percent", unit="%"),
    _f("inventory_turns", label_en="Inventory turns / year", label_ar="دوران المخزون سنوياً", input_type="number", required=False),
    _f("rent_or_lease", label_en="Monthly rent / lease", label_ar="الإيجار الشهري", input_type="currency", unit="SAR"),
]

# Mobility / marketplace services (Uber-like) — NOT SaaS subscription metrics
SERVICES_SCHEMA = [
    _f("take_rate", label_en="Take rate / commission", label_ar="نسبة العمولة (Take rate)", input_type="percent", unit="%"),
    _f("monthly_trips", label_en="Monthly trips (year 1)", label_ar="الرحلات الشهرية (سنة 1)", input_type="number", unit="trips"),
    _f("drivers", label_en="Active drivers / supply units", label_ar="السائقون / وحدات التوريد النشطة", input_type="number"),
    _f("driver_cac", label_en="Driver / supply acquisition cost", label_ar="تكلفة اكتساب السائق", input_type="currency", unit="SAR"),
    _f("avg_trip_value", label_en="Average trip / order value", label_ar="متوسط قيمة الرحلة", input_type="currency", unit="SAR"),
    _f("monthly_fixed_opex", label_en="Monthly fixed opex", label_ar="التكاليف التشغيلية الثابتة شهرياً", input_type="currency", unit="SAR"),
    _f("initial_investment", label_en="Initial investment", label_ar="الاستثمار الأولي", input_type="currency", unit="SAR"),
]

OTHER_SCHEMA = [
    _f("revenue_year1", label_en="Expected year-1 revenue", label_ar="إيراد السنة الأولى المتوقع", input_type="currency", unit="SAR"),
    _f("opex_year1", label_en="Expected year-1 opex", label_ar="تكاليف التشغيل سنة 1", input_type="currency", unit="SAR"),
    _f("initial_investment", label_en="Initial investment", label_ar="الاستثمار الأولي", input_type="currency", unit="SAR"),
    _f(
        "revenue_model",
        label_en="Primary revenue model",
        label_ar="نموذج الإيراد الأساسي",
        input_type="single_select",
        options_en=["Product sales", "Services", "Usage fees", "Mixed", "Other"],
        options_ar=["بيع منتجات", "خدمات", "رسوم استخدام", "مختلط", "أخرى"],
    ),
    _f("gross_margin", label_en="Gross margin", label_ar="هامش الربح الإجمالي", input_type="percent", unit="%", required=False),
]


ASSUMPTION_SCHEMAS: dict[str, list[dict[str, Any]]] = {
    "saas_digital": SAAS_SCHEMA,
    "real_estate": REAL_ESTATE_SCHEMA,
    "data_center": DATA_CENTER_SCHEMA,
    "industrial": INDUSTRIAL_SCHEMA,
    "retail": RETAIL_SCHEMA,
    "services": SERVICES_SCHEMA,
    "other": OTHER_SCHEMA,
}


def get_assumption_schema(archetype: str) -> list[dict[str, Any]]:
    from .classifier import normalize_archetype

    return list(ASSUMPTION_SCHEMAS.get(normalize_archetype(archetype), OTHER_SCHEMA))


def schema_keys_for(archetype: str) -> set[str]:
    return {f["key"] for f in get_assumption_schema(archetype)}


def assert_no_saas_leakage(archetype: str, keys: list[str] | set[str]) -> list[str]:
    """Return leaked SaaS keys found on a non-SaaS archetype (empty = clean)."""
    from .classifier import normalize_archetype

    arch = normalize_archetype(archetype)
    if arch == "saas_digital":
        return []
    # driver_cac is services-specific, not SaaS CAC
    banned = set(SAAS_LEAKAGE_KEYS)
    return sorted({k for k in keys if k.lower() in banned or k.lower().replace("-", "_") in banned})
