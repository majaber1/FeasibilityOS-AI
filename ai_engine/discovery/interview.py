"""Discovery interview model: consultant-style questions per archetype.

Question object shape (API / UI):
  id, category, question, explanation, answer_type, options, required, allow_ai_estimate

answer_type values:
  YES_NO | SELECT | MULTI_SELECT | NUMBER | CURRENCY | PERCENTAGE | TEXT
"""
from __future__ import annotations

from typing import Any

from ai_engine.archetypes.questions import get_structured_questions

ANSWER_TYPES = frozenset(
    {
        "YES_NO",
        "SELECT",
        "MULTI_SELECT",
        "NUMBER",
        "CURRENCY",
        "PERCENTAGE",
        "TEXT",
    }
)

# Map legacy / schema question_type → Discovery Advisor answer_type
_TYPE_MAP = {
    "YES_NO": "YES_NO",
    "SINGLE_SELECT": "SELECT",
    "SELECT": "SELECT",
    "MULTI_SELECT": "MULTI_SELECT",
    "NUMBER": "NUMBER",
    "CURRENCY": "CURRENCY",
    "PERCENTAGE": "PERCENTAGE",
    "SHORT_TEXT": "TEXT",
    "LONG_TEXT": "TEXT",
    "TEXT": "TEXT",
    "DATE": "TEXT",
    "FILE_UPLOAD": "TEXT",
}

# Category + "why this matters" packs keyed by field id (schema keys).
# Covers required Discovery Advisor topics without changing assumption schemas.
_FIELD_META: dict[str, dict[str, str]] = {
    # SaaS
    "target_customers": {
        "category": "customers",
        "explanation_en": "Year-1 customer volume anchors ARR and CAC payback.",
        "explanation_ar": "حجم العملاء في السنة الأولى يحدد الإيراد المتكرر وفترة استرداد CAC.",
    },
    "pricing": {
        "category": "pricing",
        "explanation_en": "Subscription price drives unit economics and willingness-to-pay checks.",
        "explanation_ar": "سعر الاشتراك يقود اقتصاد الوحدة واختبارات الاستعداد للدفع.",
    },
    "arr": {
        "category": "arr_model",
        "explanation_en": "ARR is the core SaaS growth and valuation signal.",
        "explanation_ar": "الإيراد السنوي المتكرر هو مؤشر النمو والتقييم الأساسي لـ SaaS.",
    },
    "mrr": {
        "category": "arr_model",
        "explanation_en": "MRR helps validate the ARR trajectory month by month.",
        "explanation_ar": "الإيراد الشهري المتكرر يساعد على التحقق من مسار ARR شهرياً.",
    },
    "cac": {
        "category": "cac",
        "explanation_en": "Customer acquisition cost must stay sustainable vs LTV.",
        "explanation_ar": "تكلفة اكتساب العميل يجب أن تبقى مستدامة مقابل قيمة العميل.",
    },
    "churn": {
        "category": "retention",
        "explanation_en": "Churn / retention determines whether growth compounds or leaks.",
        "explanation_ar": "التسرب / الاحتفاظ يحدد إن كان النمو يتراكم أو يتسرب.",
    },
    "ltv": {
        "category": "retention",
        "explanation_en": "Lifetime value shows whether CAC investment pays back.",
        "explanation_ar": "قيمة العميل مدى الحياة تُظهر إن كان استثمار CAC يسترد.",
    },
    "acquisition_channels": {
        "category": "compliance",
        "explanation_en": "Channels and go-to-market constraints shape scalable growth.",
        "explanation_ar": "القنوات وقيود الدخول للسوق تشكل قابلية التوسع.",
    },
    # Professional services
    "consultants_headcount": {
        "category": "consultants",
        "explanation_en": "Headcount sets delivery capacity and cost base.",
        "explanation_ar": "عدد الموظفين يحدد طاقة التسليم وقاعدة التكلفة.",
    },
    "utilization_rate": {
        "category": "utilization",
        "explanation_en": "Billable utilization links people to realized revenue.",
        "explanation_ar": "نسبة الاستخدام القابلة للفوترة تربط الأشخاص بالإيراد المحقق.",
    },
    "active_contracts": {
        "category": "contracts",
        "explanation_en": "Active contracts / clients anchor near-term revenue visibility.",
        "explanation_ar": "العقود / العملاء النشطون يرسّخون وضوح الإيراد القريب.",
    },
    "monthly_recurring_contracts": {
        "category": "contracts",
        "explanation_en": "Recurring retainers stabilize cash flow for managed services.",
        "explanation_ar": "عقود الاحتفاظ المتكررة تثبت التدفق النقدي للخدمات المُدارة.",
    },
    "delivery_cost_monthly": {
        "category": "delivery_cost",
        "explanation_en": "Delivery cost is the main lever on services margins.",
        "explanation_ar": "تكلفة التسليم هي الرافعة الرئيسية لهامش الخدمات.",
    },
    "gross_margin": {
        "category": "margins",
        "explanation_en": "Gross margin shows whether the delivery model is healthy.",
        "explanation_ar": "هامش الربح الإجمالي يُظهر إن كان نموذج التسليم صحياً.",
    },
    "initial_investment": {
        "category": "margins",
        "explanation_en": "Upfront investment frames payback and funding need.",
        "explanation_ar": "الاستثمار الأولي يحدد فترة الاسترداد والحاجة للتمويل.",
    },
    # Real estate
    "land_cost": {
        "category": "land",
        "explanation_en": "Land is often the largest capital commitment in development.",
        "explanation_ar": "الأرض غالباً أكبر التزام رأسمالي في التطوير.",
    },
    "construction_boq": {
        "category": "boq",
        "explanation_en": "BOQ / hard cost drives total development budget.",
        "explanation_ar": "تكلفة البناء (BOQ) تقود ميزانية التطوير الإجمالية.",
    },
    "units": {
        "category": "units",
        "explanation_en": "Unit count scales both cost and sellable inventory.",
        "explanation_ar": "عدد الوحدات يوسّع التكلفة والمخزون القابل للبيع.",
    },
    "selling_price": {
        "category": "selling_rental_price",
        "explanation_en": "Selling or rental price sets revenue per unit.",
        "explanation_ar": "سعر البيع أو الإيجار يحدد الإيراد لكل وحدة.",
    },
    "absorption_rate": {
        "category": "absorption",
        "explanation_en": "Absorption pace governs cash-in timing and risk.",
        "explanation_ar": "معدل الامتصاص يحكم توقيت التدفق النقدي والمخاطر.",
    },
    "financing": {
        "category": "financing",
        "explanation_en": "Financing structure changes leverage and funding risk.",
        "explanation_ar": "هيكل التمويل يغيّر الرافعة ومخاطر التمويل.",
    },
    "loan_to_cost": {
        "category": "financing",
        "explanation_en": "Loan-to-cost shows how much debt the plan assumes.",
        "explanation_ar": "نسبة القرض إلى التكلفة تُظهر حجم الدين المفترض.",
    },
    # Data center
    "mw_capacity": {
        "category": "mw",
        "explanation_en": "IT MW capacity is the primary commercial inventory.",
        "explanation_ar": "سعة الميجاواط هي المخزون التجاري الأساسي.",
    },
    "rack_count": {
        "category": "racks",
        "explanation_en": "Rack count translates capacity into sellable space.",
        "explanation_ar": "عدد الرفوف يحوّل السعة إلى مساحة قابلة للبيع.",
    },
    "pue": {
        "category": "pue",
        "explanation_en": "PUE drives power overhead and operating efficiency.",
        "explanation_ar": "PUE يقود عبء الطاقة وكفاءة التشغيل.",
    },
    "power_cost": {
        "category": "power",
        "explanation_en": "Power cost is a major OPEX driver for data centers.",
        "explanation_ar": "تكلفة الطاقة محرك رئيسي لتكاليف التشغيل في مراكز البيانات.",
    },
    "occupancy": {
        "category": "occupancy",
        "explanation_en": "Year-1 occupancy sets the ramp of contracted revenue.",
        "explanation_ar": "نسبة الإشغال سنة 1 تحدد مسار الإيراد المتعاقد.",
    },
    "pricing_per_kw": {
        "category": "occupancy",
        "explanation_en": "Price per kW is the main monetization rate.",
        "explanation_ar": "السعر لكل كيلوواط هو معدل التسييل الرئيسي.",
    },
    "capex_total": {
        "category": "capex_opex",
        "explanation_en": "Total CAPEX frames funding need and payback.",
        "explanation_ar": "إجمالي النفقات الرأسمالية يحدد الحاجة للتمويل والاسترداد.",
    },
    "opex_annual": {
        "category": "capex_opex",
        "explanation_en": "Annual OPEX (ex-power) affects long-run margins.",
        "explanation_ar": "التكاليف التشغيلية السنوية تؤثر على الهوامش طويلة الأجل.",
    },
    "tier": {
        "category": "pue",
        "explanation_en": "Target Tier influences design cost and SLA pricing.",
        "explanation_ar": "المستهدف Tier يؤثر على تكلفة التصميم وتسعير مستوى الخدمة.",
    },
    "contract_term_months": {
        "category": "occupancy",
        "explanation_en": "Contract term length stabilizes occupancy cash flow.",
        "explanation_ar": "مدة العقد تثبت التدفق النقدي من الإشغال.",
    },
    # Mobility
    "take_rate": {
        "category": "take_rate",
        "explanation_en": "Take rate is the marketplace's revenue share of GMV.",
        "explanation_ar": "نسبة العمولة هي حصة المنصة من إجمالي قيمة المعاملات.",
    },
    "monthly_trips": {
        "category": "trips",
        "explanation_en": "Trip volume is the demand engine for marketplace revenue.",
        "explanation_ar": "حجم الرحلات هو محرك الطلب لإيراد السوق.",
    },
    "drivers": {
        "category": "drivers",
        "explanation_en": "Active supply (drivers) must match trip demand.",
        "explanation_ar": "العرض النشط (السائقون) يجب أن يطابق طلب الرحلات.",
    },
    "driver_cac": {
        "category": "drivers",
        "explanation_en": "Supply acquisition cost affects marketplace unit economics.",
        "explanation_ar": "تكلفة اكتساب العرض تؤثر على اقتصاد وحدة السوق.",
    },
    "avg_trip_value": {
        "category": "trips",
        "explanation_en": "Average trip value scales GMV with take rate.",
        "explanation_ar": "متوسط قيمة الرحلة يوسّع إجمالي المعاملات مع نسبة العمولة.",
    },
    "monthly_fixed_opex": {
        "category": "take_rate",
        "explanation_en": "Fixed opex must be covered by take-rate contribution.",
        "explanation_ar": "التكاليف الثابتة يجب أن تُغطى من مساهمة نسبة العمولة.",
    },
}

_DEFAULT_CATEGORY = "general"

_DEFAULT_EXPLANATION = {
    "en": "This input sharpens the feasibility model for your project type.",
    "ar": "هذا المدخل يُحسّن نموذج الجدوى لنوع مشروعك.",
}

# Archetype → expected discovery categories (for validation / evidence)
ARCHETYPE_CATEGORY_PACKS: dict[str, list[str]] = {
    "saas_digital": ["customers", "pricing", "arr_model", "cac", "retention", "compliance"],
    "services_professional": [
        "consultants",
        "utilization",
        "contracts",
        "delivery_cost",
        "margins",
    ],
    "services_mobility": ["drivers", "trips", "take_rate"],
    "real_estate": ["land", "boq", "units", "selling_rental_price", "absorption", "financing"],
    "data_center": ["mw", "racks", "pue", "power", "occupancy", "capex_opex"],
}


def _answer_type(question_type: str) -> str:
    return _TYPE_MAP.get(str(question_type or "").upper(), "TEXT")


def _meta_for(field_key: str) -> dict[str, str]:
    return _FIELD_META.get(field_key) or {
        "category": _DEFAULT_CATEGORY,
        "explanation_en": _DEFAULT_EXPLANATION["en"],
        "explanation_ar": _DEFAULT_EXPLANATION["ar"],
    }


def enrich_question(raw: dict[str, Any], *, language: str = "en") -> dict[str, Any]:
    """Attach Discovery Advisor fields onto a schema-backed question dict."""
    lang = "ar" if language == "ar" else "en"
    field_key = str(raw.get("field_key") or raw.get("id") or "")
    meta = _meta_for(field_key)
    qtype = _answer_type(str(raw.get("question_type") or raw.get("answer_type") or "TEXT"))
    prompt = raw.get("prompt") or (
        raw.get("prompt_ar") if lang == "ar" else raw.get("prompt_en")
    )
    options = raw.get("options")
    if options is None:
        options = raw.get("options_ar") if lang == "ar" else raw.get("options_en")
    explanation = raw.get("explanation") or raw.get("description") or (
        meta["explanation_ar"] if lang == "ar" else meta["explanation_en"]
    )
    if not explanation:
        explanation = _DEFAULT_EXPLANATION["ar" if lang == "ar" else "en"]

    allow_ai = raw.get("allow_ai_estimate")
    if allow_ai is None:
        # Numeric / money / percent fields are estimable; selects may be too.
        allow_ai = qtype in {
            "NUMBER",
            "CURRENCY",
            "PERCENTAGE",
            "SELECT",
            "YES_NO",
            "TEXT",
            "MULTI_SELECT",
        }

    out = {
        **raw,
        "id": raw.get("id") or field_key,
        "field_key": field_key or raw.get("id"),
        "category": raw.get("category") or meta["category"],
        "question": raw.get("question") or prompt,
        "prompt": prompt,  # keep legacy UI field
        "explanation": explanation,
        "description": explanation,
        "answer_type": qtype,
        "question_type": {
            "YES_NO": "YES_NO",
            "SELECT": "SINGLE_SELECT",
            "MULTI_SELECT": "MULTI_SELECT",
            "NUMBER": "NUMBER",
            "CURRENCY": "CURRENCY",
            "PERCENTAGE": "PERCENTAGE",
            "TEXT": "SHORT_TEXT",
        }.get(qtype, "SHORT_TEXT"),
        "options": list(options or []),
        "required": bool(raw.get("required", True)),
        "allow_ai_estimate": bool(allow_ai),
        "answered": bool(raw.get("answered", False)),
        "ai_estimated": bool(raw.get("ai_estimated", False)),
        "answer": raw.get("answer"),
    }
    return out


def enrich_questions_for_language(
    questions: list[dict[str, Any]] | None,
    language: str = "en",
) -> list[dict[str, Any]]:
    return [enrich_question(q, language=language) for q in (questions or [])]


def build_discovery_interview(
    archetype: str,
    language: str = "en",
    *,
    context_text: str | None = None,
    services_variant: str | None = None,
) -> list[dict[str, Any]]:
    """Build full interview question list from archetype schema (read-only)."""
    base = get_structured_questions(
        archetype,
        context_text=context_text,
        services_variant=services_variant,
    )
    lang = "ar" if language == "ar" else "en"
    localized: list[dict[str, Any]] = []
    for q in base:
        localized.append(
            {
                **q,
                "prompt": q["prompt_ar"] if lang == "ar" else q["prompt_en"],
                "options": q["options_ar"] if lang == "ar" else q["options_en"],
                "description": q["description_ar"] if lang == "ar" else q["description_en"],
            }
        )
    return enrich_questions_for_language(localized, language=lang)


def is_question_satisfied(
    question: dict[str, Any],
    answers: dict[str, Any] | None = None,
) -> bool:
    """True when user answered or chose Let AI estimate."""
    if question.get("answered") or question.get("ai_estimated"):
        return True
    qid = question.get("id")
    if qid and answers and qid in answers:
        val = answers[qid]
        if val is None or val == "":
            return False
        if isinstance(val, str) and not val.strip():
            return False
        if isinstance(val, (list, tuple)) and len(val) == 0:
            return False
        return True
    return False


def unanswered_required(
    questions: list[dict[str, Any]] | None,
    answers: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    out = []
    for q in questions or []:
        if not q.get("required", True):
            continue
        if not is_question_satisfied(q, answers):
            out.append(q)
    return out
