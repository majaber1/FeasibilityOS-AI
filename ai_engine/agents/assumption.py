from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..config import get_llm
from ..models.study_state import Assumption, StudyState

SYSTEM_PROMPT_AR = """
أنت محلل افتراضات خبير في دراسات الجدوى للسوق السعودي.
مهمتك: تحديد وتقييم الافتراضات الأساسية التي تبنى عليها دراسة الجدوى.

خطوات العمل:
1. راجع معلومات المشروع والأدلة المتاحة
2. حدد الافتراضات الأساسية (سعر، طلب، تكلفة، نمو، تنظيمات)
3. لكل افتراض، حدد: القيمة الأساسية، الحد الأدنى، الحد الأعلى
4. قيّم مستوى الثقة: confirmed / medium / low
5. وثّق مصدر كل افتراض وorigin: user|evidence_derived|provisional_estimate

قواعد صارمة:
- التقديرات التخطيطية توضع هنا كافتراضات فقط — وليست أدلة
- إذا كان المسار تقديرياً (provisional)، استخدم origin=provisional_estimate و confidence=low
- الافتراضات يجب أن تكون قابلة للقياس
- أجب بالعربية ما لم يكتب المستخدم بالإنجليزية

أخرج JSON داخل ```json ... ```:
{
  "assumptions": [
    {
      "key": "اسم الافتراض",
      "value": "القيمة الأساسية",
      "source": "المصدر",
      "confidence": "confirmed|medium|low",
      "origin": "user|evidence_derived|provisional_estimate",
      "low": "الحد الأدنى",
      "base": "الأساس",
      "high": "الحد الأعلى",
      "rationale": "سبب مختصر"
    }
  ],
  "assumptions_complete": true/false
}
"""

SYSTEM_PROMPT_EN = """
You are an assumptions analyst expert in feasibility studies for the Saudi market.
Your task: identify and evaluate key assumptions the feasibility study is built on.

Steps:
1. Review project information and available evidence
2. Identify key assumptions (price, demand, cost, growth, regulations)
3. For each assumption: base value, low bound, high bound
4. Assess confidence: confirmed / medium / low
5. Document source and origin: user|evidence_derived|provisional_estimate

Strict rules:
- Planning estimates belong here as assumptions only — never as Evidence
- If the path is provisional, use origin=provisional_estimate and confidence=low
- Assumptions must be measurable
- Reply in English if user writes in English

Output JSON inside ```json ... ```:
{
  "assumptions": [
    {
      "key": "assumption name",
      "value": "base value",
      "source": "source",
      "confidence": "confirmed|medium|low",
      "origin": "user|evidence_derived|provisional_estimate",
      "low": "low bound",
      "base": "base",
      "high": "high bound",
      "rationale": "short why"
    }
  ],
  "assumptions_complete": true/false
}
"""


def _gap_list(state: StudyState) -> list[str]:
    gaps: list[str] = []
    if state.profile and state.profile.missing_information:
        gaps = list(state.profile.missing_information)
    if gaps:
        return gaps
    for msg in reversed(state.messages or []):
        content = getattr(msg, "content", "") or ""
        if "provisional" in content.lower() or "تقدير" in content or "estimate" in content.lower():
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith(("- ", "• ")):
                    gaps.append(stripped[2:].strip())
            if gaps:
                return gaps
    sector = state.profile.sector if state.profile else "this project"
    return [
        f"Year-1 revenue estimate for {sector}",
        f"Customer acquisition cost for {sector}",
        f"Operating cost structure for {sector}",
    ]


def _provisional_assumptions(state: StudyState) -> list[Assumption]:
    """Deterministic provisional assumptions — NEVER written as Evidence claims."""
    sector = state.profile.sector if state.profile and state.profile.sector else "project"
    assumptions: list[Assumption] = []
    for gap in _gap_list(state):
        key = gap[:80]
        assumptions.append(
            Assumption(
                key=key,
                value=f"Provisional Saudi-market planning estimate for '{gap}' ({sector})",
                source="provisional_ai_estimate",
                confidence="low",
                origin="provisional_estimate",
                status="draft",
                low="conservative",
                base="base case",
                high="optimistic",
                rationale="Generated as provisional planning input because the user chose estimates; not Evidence.",
            )
        )
    return assumptions


def run_assumptions(state: StudyState) -> StudyState:
    lang = state.language
    provisional = state.gate_choice == "provisional" or (
        (state.workflow_meta or {}).get("force_provisional_assumptions") is True
    )

    if provisional:
        # Prefer LLM when available; always land as assumptions, never claims.
        try:
            llm = get_llm("assumptions")
        except Exception as e:
            state.assumptions = _provisional_assumptions(state)
            state.phase = "ASSUMPTIONS_REVIEW"
            state.next_action = "review_assumptions"
            state.error = None
            note = (
                "تم إنشاء افتراضات تقديرية أولية (ليست أدلة) بعد تعذر تهيئة النموذج."
                if lang == "ar"
                else "Provisional assumptions were created (not Evidence) because the model could not be initialized."
            )
            state.messages.append(AIMessage(content=f"{note}\n\n(Details: {e})"))
            return state

        instruct = (
            "Create provisional_estimate assumptions for each remaining gap. "
            "Do not create Evidence claims."
            if lang == "en"
            else "أنشئ افتراضات من نوع provisional_estimate لكل فجوة متبقية. لا تنشئ أدلة."
        )
        system_prompt = SYSTEM_PROMPT_EN if lang == "en" else SYSTEM_PROMPT_AR
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=instruct + "\n" + "\n".join(f"- {g}" for g in _gap_list(state))),
        ] + list(state.messages or [])
        try:
            response = llm.invoke(messages)
            response_text = response.content
            assumption_data = _extract_json(response_text) or {}
            assumptions = _parse_assumptions(
                assumption_data.get("assumptions", []),
                default_origin="provisional_estimate",
                default_confidence="low",
            )
            if not assumptions:
                assumptions = _provisional_assumptions(state)
            state.assumptions = assumptions
            state.phase = "ASSUMPTIONS_REVIEW"
            state.next_action = "review_assumptions"
            state.error = None
            state.messages.append(AIMessage(content=response_text))
            return state
        except Exception as e:
            state.assumptions = _provisional_assumptions(state)
            state.phase = "ASSUMPTIONS_REVIEW"
            state.next_action = "review_assumptions"
            state.error = None
            note = (
                "تعذر استدعاء نموذج الافتراضات؛ تم إنشاء افتراضات تقديرية محلية (ليست أدلة)."
                if lang == "ar"
                else "Assumption model call failed; local provisional assumptions were created (not Evidence)."
            )
            state.messages.append(AIMessage(content=f"{note}\n\n(Details: {e})"))
            return state

    system_prompt = SYSTEM_PROMPT_AR if lang == "ar" else SYSTEM_PROMPT_EN
    try:
        llm = get_llm("assumptions")
    except Exception as e:
        state.error = str(e)
        state.next_action = "retry"
        return state

    context_parts = []
    if state.profile:
        context_parts.append(f"Project: {state.profile.archetype} / {state.profile.sector}")
    if state.claims:
        claims_text = "\n".join(
            f"- {c.statement} ({c.source_type}, confidence: {c.confidence})" for c in state.claims
        )
        context_parts.append(f"Evidence:\n{claims_text}")

    extra = ""
    if context_parts:
        extra = "\n\nContext:\n" + "\n".join(context_parts)

    messages = [SystemMessage(content=system_prompt + extra)] + state.messages

    try:
        response = llm.invoke(messages)
        response_text = response.content
    except Exception as e:
        state.error = str(e)
        state.next_action = "retry"
        return state

    assumption_data = _extract_json(response_text)
    if assumption_data:
        state.assumptions = _parse_assumptions(
            assumption_data.get("assumptions", []),
            default_origin="evidence_derived" if state.claims else "user",
        )
        if assumption_data.get("assumptions_complete", False) and state.assumptions:
            state.phase = "READY_FOR_ANALYSIS"
            state.assumptions_approved = True
        else:
            state.phase = "ASSUMPTIONS_REVIEW"

    state.messages.append(AIMessage(content=response_text))
    state.next_action = "review_assumptions"
    return state


def _parse_assumptions(
    rows: list,
    *,
    default_origin: str = "user",
    default_confidence: str = "low",
) -> list[Assumption]:
    assumptions: list[Assumption] = []
    for a in rows or []:
        origin = a.get("origin") or default_origin
        if origin not in ("user", "evidence_derived", "provisional_estimate"):
            origin = default_origin
        confidence = a.get("confidence") or default_confidence
        if confidence not in ("confirmed", "medium", "low"):
            confidence = default_confidence
        assumptions.append(
            Assumption(
                key=a.get("key", "") or "assumption",
                value=a.get("value", "") or "",
                source=a.get("source", "") or origin,
                confidence=confidence,
                low=a.get("low"),
                base=a.get("base"),
                high=a.get("high"),
                origin=origin,
                status="draft",
                rationale=a.get("rationale"),
            )
        )
    return assumptions


def _extract_json(text: str) -> dict | None:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None
