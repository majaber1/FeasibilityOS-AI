"""Archetype-specific structured discovery question catalogs for V2 studies."""
from __future__ import annotations

from typing import Any


QuestionType = (
    "YES_NO",
    "SINGLE_SELECT",
    "MULTI_SELECT",
    "NUMBER",
    "CURRENCY",
    "PERCENTAGE",
    "DATE",
    "FILE_UPLOAD",
    "SHORT_TEXT",
    "LONG_TEXT",
)


def _q(
    qid: str,
    *,
    prompt_ar: str,
    prompt_en: str,
    question_type: str,
    options_ar: list[str] | None = None,
    options_en: list[str] | None = None,
    unit: str | None = None,
    required: bool = True,
    field_key: str | None = None,
) -> dict[str, Any]:
    return {
        "id": qid,
        "prompt_ar": prompt_ar,
        "prompt_en": prompt_en,
        "question_type": question_type,
        "options_ar": options_ar or [],
        "options_en": options_en or [],
        "unit": unit,
        "required": required,
        "field_key": field_key or qid,
        "answer": None,
        "answered": False,
    }


# --- Golden scenario catalogs -------------------------------------------------

SAAS_DIGITAL = [
    _q(
        "project_stage",
        prompt_ar="ما هي مرحلة المشروع؟",
        prompt_en="What is the project stage?",
        question_type="SINGLE_SELECT",
        options_ar=["فكرة", "MVP", "يعمل بالفعل", "توسع"],
        options_en=["Idea", "MVP", "Already operating", "Expansion"],
        field_key="stage",
    ),
    _q(
        "target_customers",
        prompt_ar="من هم العملاء المستهدفون؟",
        prompt_en="Who are the target customers?",
        question_type="MULTI_SELECT",
        options_ar=["أفراد", "شركات صغيرة", "مؤسسات", "حكومة"],
        options_en=["Consumers", "SMBs", "Enterprises", "Government"],
    ),
    _q(
        "revenue_model",
        prompt_ar="ما هو نموذج الإيرادات؟",
        prompt_en="What is the revenue model?",
        question_type="SINGLE_SELECT",
        options_ar=["اشتراك", "عمولة على المعاملات", "استشارات", "مختلط", "لم يُحدد بعد"],
        options_en=["Subscription", "Transaction fee", "Consulting", "Mixed", "Not decided yet"],
    ),
    _q(
        "subscription_price",
        prompt_ar="ما سعر الاشتراك الشهري المتوقع؟",
        prompt_en="What is the expected monthly subscription price?",
        question_type="CURRENCY",
        unit="SAR",
    ),
    _q(
        "year1_customers",
        prompt_ar="كم عدد العملاء المتوقع في السنة الأولى؟",
        prompt_en="How many customers are expected in year 1?",
        question_type="NUMBER",
        unit="customers",
    ),
    _q(
        "cac",
        prompt_ar="ما تكلفة اكتساب العميل المتوقعة (CAC)؟",
        prompt_en="What is the expected customer acquisition cost (CAC)?",
        question_type="CURRENCY",
        unit="SAR",
    ),
    _q(
        "churn",
        prompt_ar="ما نسبة التسرب الشهرية المتوقعة؟",
        prompt_en="What is the expected monthly churn rate?",
        question_type="PERCENTAGE",
        unit="%",
    ),
    _q(
        "cloud_ai_cost",
        prompt_ar="ما التكلفة الشهرية المتوقعة للسحابة/الذكاء الاصطناعي؟",
        prompt_en="What is the expected monthly cloud/AI cost?",
        question_type="CURRENCY",
        unit="SAR",
    ),
    _q(
        "team_size",
        prompt_ar="ما حجم الفريق الحالي؟",
        prompt_en="What is the current team size?",
        question_type="NUMBER",
        unit="people",
    ),
    _q(
        "dev_cost",
        prompt_ar="ما تكلفة التطوير الأولية المتوقعة؟",
        prompt_en="What is the expected initial development cost?",
        question_type="CURRENCY",
        unit="SAR",
    ),
    _q(
        "funding_goal",
        prompt_ar="هل تحتاج تمويلاً الآن؟",
        prompt_en="Do you need funding now?",
        question_type="YES_NO",
    ),
]

REAL_ESTATE = [
    _q(
        "company_status",
        prompt_ar="ما حالة الشركة المنفذة؟",
        prompt_en="What is the executing company's status?",
        question_type="SINGLE_SELECT",
        options_ar=["قائمة وتعمل", "جديدة", "شراكة", "أفراد"],
        options_en=["Operating company", "New company", "Partnership", "Individuals"],
    ),
    _q(
        "land_status",
        prompt_ar="ما حالة الأرض؟",
        prompt_en="What is the land status?",
        question_type="SINGLE_SELECT",
        options_ar=["مملوكة", "مستأجرة", "تحت الشراء", "غير محددة"],
        options_en=["Owned", "Leased", "Under purchase", "Undecided"],
    ),
    _q(
        "land_value",
        prompt_ar="ما قيمة الأرض إن وُجدت؟",
        prompt_en="What is the land value if applicable?",
        question_type="CURRENCY",
        unit="SAR",
        required=False,
    ),
    _q(
        "permits_status",
        prompt_ar="ما حالة التصاريح والرخص؟",
        prompt_en="What is the permit/license status?",
        question_type="SINGLE_SELECT",
        options_ar=["صادرة", "قيد الإصدار", "غير مبدوءة", "جزئية"],
        options_en=["Issued", "In progress", "Not started", "Partial"],
    ),
    _q(
        "unit_count",
        prompt_ar="كم عدد الوحدات وأنواعها الرئيسية؟",
        prompt_en="How many units and main types?",
        question_type="SHORT_TEXT",
    ),
    _q(
        "construction_progress",
        prompt_ar="ما نسبة إنجاز البناء الحالية؟",
        prompt_en="What is the current construction progress?",
        question_type="PERCENTAGE",
        unit="%",
    ),
    _q(
        "cost_incurred",
        prompt_ar="ما التكلفة المتكبدة حتى الآن؟",
        prompt_en="What cost has been incurred so far?",
        question_type="CURRENCY",
        unit="SAR",
    ),
    _q(
        "remaining_construction_cost",
        prompt_ar="ما تكلفة البناء المتبقية؟",
        prompt_en="What is the remaining construction cost?",
        question_type="CURRENCY",
        unit="SAR",
    ),
    _q(
        "sales_model",
        prompt_ar="ما نموذج البيع/التأجير؟",
        prompt_en="What is the sales/rental model?",
        question_type="SINGLE_SELECT",
        options_ar=["بيع", "تأجير", "مختلط"],
        options_en=["Sale", "Rent", "Mixed"],
    ),
    _q(
        "target_price",
        prompt_ar="ما سعر البيع أو الإيجار المستهدف للوحدة؟",
        prompt_en="What is the target sale or rent price per unit?",
        question_type="CURRENCY",
        unit="SAR",
    ),
    _q(
        "existing_debt",
        prompt_ar="هل يوجد دين قائم على المشروع؟",
        prompt_en="Is there existing project debt?",
        question_type="YES_NO",
    ),
    _q(
        "funding_required",
        prompt_ar="ما حجم التمويل المطلوب؟",
        prompt_en="What funding amount is required?",
        question_type="CURRENCY",
        unit="SAR",
    ),
    _q(
        "boq_upload",
        prompt_ar="ارفع جدول الكميات (BOQ) إن توفر",
        prompt_en="Upload the BOQ if available",
        question_type="FILE_UPLOAD",
        required=False,
    ),
]

DATA_CENTER = [
    _q(
        "dc_purpose",
        prompt_ar="ما غرض مركز البيانات؟",
        prompt_en="What is the data center purpose?",
        question_type="SINGLE_SELECT",
        options_ar=["داخلي للشركة", "تجاري", "هجين"],
        options_en=["Internal", "Commercial", "Hybrid"],
    ),
    _q(
        "location",
        prompt_ar="ما الموقع المقترح؟",
        prompt_en="What is the proposed location?",
        question_type="SHORT_TEXT",
    ),
    _q(
        "tier_target",
        prompt_ar="ما مستوى Tier المستهدف؟",
        prompt_en="What Tier is targeted?",
        question_type="SINGLE_SELECT",
        options_ar=["Tier I", "Tier II", "Tier III", "Tier IV"],
        options_en=["Tier I", "Tier II", "Tier III", "Tier IV"],
    ),
    _q(
        "power_mw",
        prompt_ar="ما سعة الطاقة المطلوبة (ميجاواط)؟",
        prompt_en="What power capacity is required (MW)?",
        question_type="NUMBER",
        unit="MW",
    ),
    _q(
        "rack_capacity",
        prompt_ar="ما سعة الرفوف (Racks)؟",
        prompt_en="What is the rack capacity?",
        question_type="NUMBER",
        unit="racks",
    ),
    _q(
        "build_vs_outsource",
        prompt_ar="هل البناء داخلي أم بالاستعانة بمصادر خارجية؟",
        prompt_en="Build in-house or outsource?",
        question_type="SINGLE_SELECT",
        options_ar=["بناء داخلي", "استعانة خارجية", "مختلط"],
        options_en=["In-house build", "Outsource", "Hybrid"],
    ),
    _q(
        "capex",
        prompt_ar="ما رأس المال المتوقع (CAPEX)؟",
        prompt_en="What is the expected CAPEX?",
        question_type="CURRENCY",
        unit="SAR",
    ),
    _q(
        "opex_annual",
        prompt_ar="ما التكلفة التشغيلية السنوية المتوقعة؟",
        prompt_en="What is the expected annual OPEX?",
        question_type="CURRENCY",
        unit="SAR",
    ),
    _q(
        "utilization_y1",
        prompt_ar="ما نسبة الإشغال المستهدفة في السنة الأولى؟",
        prompt_en="What is the year-1 utilization target?",
        question_type="PERCENTAGE",
        unit="%",
    ),
    _q(
        "commercial_revenue",
        prompt_ar="إن كان تجارياً: ما الإيراد السنوي المتوقع عند التشغيل الكامل؟",
        prompt_en="If commercial: expected annual revenue at full utilization?",
        question_type="CURRENCY",
        unit="SAR",
        required=False,
    ),
]

GOVERNMENT_CONTRACT = [
    _q(
        "gov_entity",
        prompt_ar="ما الجهة الحكومية المانحة؟",
        prompt_en="Which government entity awarded the project?",
        question_type="SHORT_TEXT",
    ),
    _q(
        "award_value",
        prompt_ar="ما قيمة الترسية؟",
        prompt_en="What is the award value?",
        question_type="CURRENCY",
        unit="SAR",
    ),
    _q(
        "award_letter",
        prompt_ar="ارفع خطاب الترسية إن توفر",
        prompt_en="Upload the award letter if available",
        question_type="FILE_UPLOAD",
        required=False,
    ),
    _q(
        "contract_duration",
        prompt_ar="ما مدة العقد؟",
        prompt_en="What is the contract duration?",
        question_type="SHORT_TEXT",
    ),
    _q(
        "payment_terms",
        prompt_ar="ما شروط الدفع؟",
        prompt_en="What are the payment terms?",
        question_type="LONG_TEXT",
    ),
    _q(
        "performance_guarantee",
        prompt_ar="هل مطلوب ضمان أداء؟ وما نسبته؟",
        prompt_en="Is a performance guarantee required, and at what %?",
        question_type="PERCENTAGE",
        unit="%",
        required=False,
    ),
    _q(
        "advance_payment",
        prompt_ar="هل يوجد دفعة مقدمة؟ وما نسبتها؟",
        prompt_en="Is there an advance payment, and at what %?",
        question_type="PERCENTAGE",
        unit="%",
        required=False,
    ),
    _q(
        "execution_cost",
        prompt_ar="ما تكلفة التنفيذ المتوقعة؟",
        prompt_en="What is the expected execution cost?",
        question_type="CURRENCY",
        unit="SAR",
    ),
    _q(
        "expected_margin",
        prompt_ar="ما هامش الربح المتوقع؟",
        prompt_en="What is the expected margin?",
        question_type="PERCENTAGE",
        unit="%",
    ),
    _q(
        "cashflow_gap",
        prompt_ar="ما فجوة التدفق النقدي المتوقعة؟",
        prompt_en="What is the expected cash-flow gap?",
        question_type="CURRENCY",
        unit="SAR",
    ),
    _q(
        "financing_need",
        prompt_ar="هل تحتاج تمويلاً رأس مال عامل / ضمانات؟",
        prompt_en="Do you need working-capital financing / guarantees?",
        question_type="YES_NO",
    ),
    _q(
        "boq_or_contract",
        prompt_ar="ارفع العقد أو جدول الكميات إن توفر",
        prompt_en="Upload the contract or BOQ if available",
        question_type="FILE_UPLOAD",
        required=False,
    ),
]

CATALOGS: dict[str, list[dict[str, Any]]] = {
    "saas_digital": SAAS_DIGITAL,
    "real_estate": REAL_ESTATE,
    "data_center": DATA_CENTER,
    "government_contract": GOVERNMENT_CONTRACT,
    "retail": SAAS_DIGITAL[:6],
    "industrial": REAL_ESTATE[:8],
    "services": SAAS_DIGITAL[:7],
    "franchise": SAAS_DIGITAL[:7],
    "unknown": SAAS_DIGITAL[:5],
}


def classify_archetype_from_text(text: str) -> str:
    """Keyword heuristic to stabilize golden scenarios when LLM is unavailable."""
    t = (text or "").lower()
    gov_kw = (
        "government",
        "award",
        "ترسية",
        "حكوم",
        "منافسة",
        "عقد حكومي",
        "وزارة",
        "جهة حكومية",
    )
    if any(k in t for k in gov_kw):
        return "government_contract"
    dc_kw = ("data center", "datacenter", "مركز بيانات", "rack", "ميجاواط", "tier iii", "tier 3")
    if any(k in t for k in dc_kw):
        return "data_center"
    re_kw = (
        "residential",
        "real estate",
        "سكني",
        "عقار",
        "مجمع",
        "وحدات",
        "construction",
        "بناء",
        "riyadh compound",
        "مجمع سكني",
    )
    if any(k in t for k in re_kw):
        return "real_estate"
    saas_kw = (
        "saas",
        "whatsapp",
        "ai platform",
        "اشتراك",
        "منصة",
        "software",
        "تطبيق",
        "compliance",
        "ملتزم",
    )
    if any(k in t for k in saas_kw):
        return "saas_digital"
    return "unknown"


def build_questions_for_archetype(archetype: str, language: str = "ar") -> list[dict[str, Any]]:
    catalog = CATALOGS.get(archetype) or CATALOGS["unknown"]
    out: list[dict[str, Any]] = []
    for raw in catalog:
        item = dict(raw)
        item["prompt"] = item.pop("prompt_ar") if language == "ar" else item.pop("prompt_en")
        item.pop("prompt_ar", None)
        item.pop("prompt_en", None)
        opts = item.pop("options_ar") if language == "ar" else item.pop("options_en")
        item.pop("options_ar", None)
        item.pop("options_en", None)
        item["options"] = opts or []
        out.append(item)
    return out
