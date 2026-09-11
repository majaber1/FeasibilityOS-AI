from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

from ..config import get_llm
from ..models.study_state import StudyState

SYSTEM_PROMPT_AR = """
أنت محلل أدلة متخصص في السوق السعودي.
مهمتك: جمع وتقييم الأدلة والمصادر التي يقدمها المستخدم لدعم دراسة الجدوى.

خطوات العمل:
1. راجع المعلومات المقدمة من المستخدم
2. صنّف كل معلومة حسب مصدرها (رسمي / مدخل مستخدم / مستند / افتراض AI / غير موثق)
3. قيّم مستوى الثقة لكل معلومة (0.0 إلى 1.0)
4. حدد المعلومات الناقصة التي تحتاج تأكيد

قواعد صارمة:
- فضّل الأدلة الرسمية/مدخلات المستخدم عند توفرها
- وثّق كل مصدر بوضوح
- إذا لم يكن هناك مصدر رسمي، صنّف كـ "user_input" أو "ai_assumption"
- إذا أكّد المستخدم الملف وطلب تقدير الفجوات، يجب إنشاء claims من نوع ai_assumption
  بتقديرات واقعية للسوق السعودي لكل فجوة مطلوبة، مع توضيح أنها تقدير.
  لا تترك قائمة claims فارغة في هذه الحالة.
- أجب بالعربية ما لم يكتب المستخدم بالإنجليزية

أخرج JSON داخل ```json ... ```:
{
  "claims": [
    {
      "statement": "النص",
      "source_type": "official|user_input|document|ai_assumption|unverified",
      "confidence": 0.0-1.0,
      "source_url": "رابط إن وجد أو null"
    }
  ],
  "gaps": ["معلومات ناقصة"],
  "evidence_sufficient": true/false
}
"""

SYSTEM_PROMPT_EN = """
You are an evidence analyst specializing in the Saudi Arabian market.
Your task: collect and evaluate evidence and sources the user provides for the feasibility study.

Steps:
1. Review user-provided information
2. Classify each piece by source (official / user_input / document / ai_assumption / unverified)
3. Assess confidence level for each (0.0 to 1.0)
4. Identify missing information that needs confirmation

Strict rules:
- Prefer user/official evidence when present
- Document every source clearly
- If no official source, classify as "user_input" or "ai_assumption"
- When the user confirmed the profile and asked for estimates, you MUST create
  ai_assumption claims with realistic Saudi-market estimates for each requested gap.
  Mark those statements as estimates. Do not leave the claims list empty in that case.
- Reply in English if user writes in English

Output JSON inside ```json ... ```:
{
  "claims": [
    {
      "statement": "text",
      "source_type": "official|user_input|document|ai_assumption|unverified",
      "confidence": 0.0-1.0,
      "source_url": "url if available or null"
    }
  ],
  "gaps": ["missing information"],
  "evidence_sufficient": true/false
}
"""


def _gap_list_from_messages(state: StudyState) -> list[str]:
    gaps: list[str] = []
    for msg in reversed(state.messages or []):
        content = getattr(msg, "content", "") or ""
        lowered = content.lower()
        if (
            "ai_assumption" in lowered
            or "estimate" in lowered
            or "تقدير" in content
            or "remaining gaps" in lowered
            or "العناصر الناقصة" in content
        ):
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith(("- ", "• ")):
                    gaps.append(stripped[2:].strip())
            if gaps:
                break
    return gaps



def _estimate_text_for_gap(gap: str, sector: str, archetype: str = "other") -> str:
    """Build a concrete provisional estimate so Evidence panels are never empty."""
    g = (gap or "").lower()
    sector_label = sector or "this sector"
    arch = (archetype or "other").lower()

    if any(k in g for k in ("stage", "مرحلة", "maturity")):
        return (
            f"Estimated project stage for {sector_label}: idea / pre-launch "
            "(provisional ai_assumption)."
        )
    if any(k in g for k in ("decision", "goal", "هدف", "قرار", "feasibility")):
        return (
            f"Estimated decision goal: feasibility go/no-go for a Saudi {sector_label} "
            "venture (provisional ai_assumption)."
        )

    # Archetype-specific estimates — never inject SaaS CAC/ARR/churn into non-SaaS.
    if arch == "real_estate":
        if any(k in g for k in ("land", "أرض", "boq", "construction", "بناء", "unit", "وحدة", "price", "سعر")):
            return (
                f"Indicative Saudi residential development inputs for {sector_label}: "
                "land + construction BOQ, sellable units, and absorption-led sales pricing "
                "(provisional ai_assumption)."
            )
        if any(k in g for k in ("capex", "investment", "تمويل", "استثمار", "تكلفة")):
            return (
                f"Indicative development CAPEX for Saudi {sector_label}: land + hard costs "
                "typically dominate; finance via equity and/or construction loan "
                "(provisional ai_assumption)."
            )
    elif arch == "data_center":
        if any(k in g for k in ("mw", "rack", "pue", "power", "occupancy", "kw", "سعة", "طاقة")):
            return (
                f"Indicative Saudi data-center inputs for {sector_label}: IT MW capacity, "
                "rack count, target PUE, power tariff, and year-1 occupancy "
                "(provisional ai_assumption)."
            )
        if any(k in g for k in ("capex", "investment", "تمويل", "استثمار", "تكلفة")):
            return (
                f"Indicative DC CAPEX for Saudi {sector_label}: shell + fit-out + power "
                "infrastructure scaled to MW capacity (provisional ai_assumption)."
            )
    elif arch in {"services", "other"}:
        if any(k in g for k in ("take", "trip", "driver", "commission", "عمولة", "رحلة", "سائق")):
            return (
                f"Indicative mobility/marketplace inputs for Saudi {sector_label}: take-rate, "
                "monthly trips, active drivers, and driver acquisition cost "
                "(provisional ai_assumption)."
            )
        if any(
            k in g
            for k in (
                "consultant",
                "utilization",
                "contract",
                "retainer",
                "delivery",
                "margin",
                "مستشار",
                "عقد",
                "هامش",
            )
        ):
            return (
                f"Indicative professional-services inputs for Saudi {sector_label}: "
                "consultant headcount, utilization, active/MRC contracts, delivery cost, "
                "and gross margin (provisional ai_assumption)."
            )
    elif arch == "industrial":
        if any(k in g for k in ("capacity", "utilization", "raw", "unit", "إنتاج", "تشغيل")):
            return (
                f"Indicative industrial inputs for Saudi {sector_label}: production capacity, "
                "raw material / unit cost, selling price, and utilization "
                "(provisional ai_assumption)."
            )
    elif arch == "saas_digital":
        if any(k in g for k in ("cac", "acquisition", "customer", "عميل", "اكتساب", "churn", "arr", "mrr")):
            return (
                f"Indicative year-1 SaaS metrics for Saudi {sector_label}: CAC, churn, and "
                "ARR/MRR calibrated to local B2B/B2C channels (provisional ai_assumption)."
            )

    if any(k in g for k in ("price", "pricing", "revenue", "سعر", "إيراد", "نموذج")):
        if arch == "saas_digital":
            return (
                f"Indicative SaaS revenue model for Saudi {sector_label}: subscription pricing "
                "with ARR/MRR build-up (provisional ai_assumption)."
            )
        if arch == "real_estate":
            return (
                f"Indicative sales revenue model for Saudi {sector_label}: unit selling price "
                "× absorption schedule (provisional ai_assumption)."
            )
        if arch == "data_center":
            return (
                f"Indicative colocation revenue for Saudi {sector_label}: pricing per kW × "
                "occupied IT load (provisional ai_assumption)."
            )
        return (
            f"Indicative revenue model for Saudi {sector_label} calibrated in discovery "
            "(provisional ai_assumption)."
        )

    # Block SaaS CAC language on non-SaaS archetypes even if gap text mentions customers.
    if any(k in g for k in ("cac", "acquisition", "customer", "عميل", "اكتساب")):
        if arch == "saas_digital":
            return (
                f"Indicative year-1 CAC for Saudi {sector_label}: SAR 40–120 per acquired active "
                "user, depending on digital vs. offline channels (provisional ai_assumption)."
            )
        if arch == "services":
            return (
                f"Indicative driver/supply acquisition cost for Saudi {sector_label}: "
                "sign-on incentives + onboarding (provisional ai_assumption)."
            )
        return (
            f"Indicative demand/traction estimate for Saudi {sector_label} without SaaS CAC/ARR "
            "metrics (provisional ai_assumption)."
        )

    if any(k in g for k in ("market", "size", "tam", "سوق", "حجم")):
        return (
            f"Indicative Saudi addressable market for {sector_label}: multi-billion SAR "
            "category with regional concentration in Riyadh/Jeddah/Dammam "
            "(provisional ai_assumption)."
        )
    if any(k in g for k in ("capex", "investment", "تمويل", "استثمار", "تكلفة")):
        return (
            f"Indicative initial investment range for Saudi {sector_label} "
            "(provisional ai_assumption)."
        )
    return (
        f"Provisional Saudi-market estimate for '{gap}' in {sector_label}: "
        "use as a reviewable ai_assumption until validated with primary sources."
    )


def _default_gaps_for_archetype(archetype: str, sector: str) -> list[str]:
    arch = (archetype or "other").lower()
    label = sector or "this project"
    if arch == "real_estate":
        return [
            f"Land cost and construction BOQ for {label}",
            "Unit count, selling price, and absorption rate",
            "Financing structure (equity / construction loan / off-plan)",
        ]
    if arch == "data_center":
        return [
            f"IT MW capacity, rack count, and target PUE for {label}",
            "Power cost and year-1 occupancy",
            "Pricing per kW / month",
        ]
    if arch == "services":
        return [
            f"Take rate, monthly trips, and active drivers for {label}",
            "Driver acquisition cost and average trip value",
            "Initial investment and monthly fixed opex",
        ]
    if arch == "industrial":
        return [
            f"Production capacity and utilization for {label}",
            "Raw material / unit cost and selling price",
            "Machinery / plant CAPEX",
        ]
    if arch == "retail":
        return [
            f"Store count, average ticket, and monthly transactions for {label}",
            "Gross margin and rent / lease",
        ]
    if arch == "saas_digital":
        return [
            f"Target customers, pricing, and ARR for {label}",
            "CAC, churn, and acquisition channels",
        ]
    return [
        f"Initial market assumptions for {label}",
        "Indicative revenue model estimate",
        "Indicative year-1 operating cost / investment estimate",
    ]


def _provisional_estimate_claims(state: StudyState) -> list:
    from ..models.study_state import Claim

    sector = ""
    archetype = "other"
    if state.profile:
        sector = state.profile.sector or ""
        archetype = state.profile.archetype or "other"

    gaps = _gap_list_from_messages(state)
    if not gaps:
        gaps = _default_gaps_for_archetype(archetype, sector)

    claims = []
    for gap in gaps:
        claims.append(
            Claim(
                statement=_estimate_text_for_gap(gap, sector, archetype),
                source_type="ai_assumption",
                confidence=0.45,
                source_url=None,
            )
        )
    return claims


def run_evidence(state: StudyState) -> StudyState:
    lang = state.language
    system_prompt = SYSTEM_PROMPT_AR if lang == "ar" else SYSTEM_PROMPT_EN
    if state.profile_confirmed:
        if lang == "ar":
            system_prompt += (
                "\n\nملاحظة: تم تأكيد الملف. إذا طُلب منك تقدير الفجوات، أنشئ claims من نوع "
                "ai_assumption بقيم تقديرية واقعية ولا تترك القائمة فارغة."
            )
        else:
            system_prompt += (
                "\n\nNote: Profile is confirmed. If asked to estimate gaps, create ai_assumption "
                "claims with realistic values and do not leave the claims list empty."
            )
    llm = None
    try:
        llm = get_llm("extraction")
    except Exception as e:
        if state.profile_confirmed:
            state.claims = _provisional_estimate_claims(state)
            state.phase = "EVIDENCE_REVIEW"
            state.next_action = "review_evidence"
            state.error = None
            note = (
                "تعذر تهيئة نموذج الذكاء الاصطناعي، فتم إنشاء تقديرات أولية قابلة للمراجعة."
                if lang == "ar"
                else "AI model could not be initialized, so provisional reviewable estimates were created from the confirmed gaps."
            )
            from ..utils.safe_messages import sanitize_error_for_user

            sanitize_error_for_user(e, language=lang, context="evidence.init")
            state.messages.append(AIMessage(content=note))
            return state
        from ..utils.safe_messages import sanitize_error_for_user

        state.error = sanitize_error_for_user(e, language=lang, context="evidence.init")
        state.next_action = "retry"
        return state

    messages = [SystemMessage(content=system_prompt)] + state.messages

    try:
        response = llm.invoke(messages)
        response_text = response.content
    except Exception as e:
        # After Confirm Profile, still fill visible provisional estimates so UI is not empty.
        if state.profile_confirmed:
            state.claims = _provisional_estimate_claims(state)
            state.phase = "EVIDENCE_REVIEW"
            state.next_action = "review_evidence"
            state.error = None
            note = (
                "تعذر الاتصال بنموذج الذكاء الاصطناعي، فتم إنشاء تقديرات أولية قابلة للمراجعة."
                if lang == "ar"
                else "AI model unavailable, so provisional reviewable estimates were created from the confirmed gaps."
            )
            from ..utils.safe_messages import sanitize_error_for_user

            sanitize_error_for_user(e, language=lang, context="evidence.invoke")
            state.messages.append(AIMessage(content=note))
            return state
        from ..utils.safe_messages import sanitize_error_for_user

        state.error = sanitize_error_for_user(e, language=lang, context="evidence.invoke")
        state.next_action = "retry"
        return state

    evidence_data = _extract_json(response_text)
    if evidence_data:
        from ..models.study_state import Claim

        allowed = {"official", "user_input", "document", "ai_assumption", "unverified"}
        aliases = {
            "derived": "ai_assumption",
            "calculated": "ai_assumption",
            "estimate": "ai_assumption",
            "estimated": "ai_assumption",
            "assumption": "ai_assumption",
            "ai": "ai_assumption",
            "user": "user_input",
            "input": "user_input",
            "manual": "user_input",
            "gov": "official",
            "government": "official",
            "regulation": "official",
            "regulatory": "official",
            "file": "document",
            "doc": "document",
            "unknown": "unverified",
            "other": "unverified",
        }

        claims = []
        for c in evidence_data.get("claims", []):
            raw_type = str(c.get("source_type") or "unverified").strip().lower()
            source_type = raw_type if raw_type in allowed else aliases.get(raw_type, "unverified")
            try:
                confidence = float(c.get("confidence", 0.0) or 0.0)
            except (TypeError, ValueError):
                confidence = 0.0
            claims.append(Claim(
                statement=c.get("statement", "") or "",
                source_type=source_type,
                confidence=max(0.0, min(1.0, confidence)),
                source_url=c.get("source_url"),
            ))
        if not claims and state.profile_confirmed:
            claims = _provisional_estimate_claims(state)
        state.claims = claims
        state.error = None

        if evidence_data.get("evidence_sufficient", False) and claims:
            state.phase = "ASSUMPTIONS_REVIEW"
            state.evidence_approved = True
        else:
            state.phase = "EVIDENCE_REVIEW"
    elif state.profile_confirmed:
        state.claims = _provisional_estimate_claims(state)
        state.phase = "EVIDENCE_REVIEW"
        state.error = None
        response_text = (
            "تعذر استخراج JSON من النموذج؛ تم إنشاء تقديرات أولية للمراجعة."
            if lang == "ar"
            else "Could not parse model JSON; provisional estimates were created for review."
        )

    from ..utils.safe_messages import sanitize_chat_content

    public = sanitize_chat_content(
        response_text,
        language=lang,
        fallback=(
            "تم تحديث الأدلة. راجع المطالبات في اللوحة الجانبية."
            if lang == "ar"
            else "Evidence updated. Review claims in the side panel."
        ),
    )
    if public:
        state.messages.append(AIMessage(content=public))
    state.next_action = "review_evidence"
    return state


def _extract_json(text: str) -> dict | None:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None
