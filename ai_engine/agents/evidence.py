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


def _estimate_text_for_gap(gap: str, sector: str) -> str:
    """Build a concrete provisional estimate so Evidence panels are never empty."""
    g = (gap or "").lower()
    sector_label = sector or "this sector"
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
    if any(k in g for k in ("price", "pricing", "revenue", "سعر", "إيراد", "نموذج")):
        return (
            f"Indicative revenue model for Saudi {sector_label}: commission/take-rate around "
            "15–25% of gross booking value, with ARPU calibrated in discovery "
            "(provisional ai_assumption)."
        )
    if any(k in g for k in ("cac", "acquisition", "customer", "عميل", "اكتساب")):
        return (
            f"Indicative year-1 CAC for Saudi {sector_label}: SAR 40–120 per acquired active "
            "user, depending on digital vs. offline channels (provisional ai_assumption)."
        )
    if any(k in g for k in ("market", "size", "tam", "سوق", "حجم")):
        return (
            f"Indicative Saudi addressable market for {sector_label}: multi-billion SAR "
            "category with regional concentration in Riyadh/Jeddah/Dammam "
            "(provisional ai_assumption)."
        )
    if any(k in g for k in ("capex", "investment", "تمويل", "استثمار", "تكلفة")):
        return (
            f"Indicative initial investment range for Saudi {sector_label}: SAR 2M–8M "
            "for MVP + first-city launch (provisional ai_assumption)."
        )
    return (
        f"Provisional Saudi-market estimate for '{gap}' in {sector_label}: "
        "use as a reviewable ai_assumption until validated with primary sources."
    )


def _provisional_estimate_claims(state: StudyState) -> list:
    from ..models.study_state import Claim

    sector = ""
    if state.profile and state.profile.sector:
        sector = state.profile.sector

    gaps = _gap_list_from_messages(state)
    if not gaps:
        gaps = [
            f"Initial market assumptions for {sector or 'this project'}",
            "Indicative pricing / revenue model estimate",
            "Indicative year-1 customer / traction estimate",
        ]

    claims = []
    for gap in gaps:
        claims.append(
            Claim(
                statement=_estimate_text_for_gap(gap, sector),
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
            state.messages.append(AIMessage(content=note + f"\n\n(Details: {e})"))
            return state
        state.error = str(e)
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
            state.messages.append(AIMessage(content=note + f"\n\n(Details: {e})"))
            return state
        state.error = str(e)
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

    state.messages.append(AIMessage(content=response_text))
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
