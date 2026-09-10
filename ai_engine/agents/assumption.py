from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

from ..archetypes import assumption_prompt_block
from ..config import get_llm
from ..models.study_state import StudyState

SYSTEM_PROMPT_AR = """
أنت محلل افتراضات خبير في دراسات الجدوى للسوق السعودي.
مهمتك: تحديد وتقييم الافتراضات الأساسية التي تبنى عليها دراسة الجدوى.

خطوات العمل:
1. راجع معلومات المشروع والأدلة المتاحة
2. حدد الافتراضات الأساسية (سعر، طلب، تكلفة، نمو، تنظيمات)
3. لكل افتراض، حدد: القيمة الأساسية، الحد الأدنى، الحد الأعلى
4. قيّم مستوى الثقة: confirmed / medium / low
5. وثّق مصدر كل افتراض

قواعد صارمة:
- لا تخترع أرقاماً بدون أساس
- إذا لم تجد مصدراً، صنّف الثقة كـ "low"
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
      "low": "الحد الأدنى",
      "base": "الأساس",
      "high": "الحد الأعلى"
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
5. Document the source of each assumption

Strict rules:
- Never invent numbers without basis
- If no source found, classify confidence as "low"
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
      "low": "low bound",
      "base": "base",
      "high": "high bound"
    }
  ],
  "assumptions_complete": true/false
}
"""


def run_assumptions(state: StudyState) -> StudyState:
    lang = state.language
    system_prompt = SYSTEM_PROMPT_AR if lang == "ar" else SYSTEM_PROMPT_EN
    llm = get_llm("assumptions")

    context_parts = []
    archetype = state.profile.archetype if state.profile else "unknown"
    if state.profile:
        context_parts.append(f"Project: {state.profile.archetype} / {state.profile.sector}")
    if state.claims:
        claims_text = "\n".join(f"- {c.statement} ({c.source_type}, confidence: {c.confidence})" for c in state.claims)
        context_parts.append(f"Evidence:\n{claims_text}")

    extra = ""
    if context_parts:
        extra = "\n\nContext:\n" + "\n".join(context_parts)
    extra += assumption_prompt_block(archetype, lang)
    extra += (
        "\n\nIMPORTANT: every assumption field (key, value, source, confidence, low, base, high) "
        "MUST be a JSON string, even when numeric (e.g. \"900000000\")."
    )

    # If this turn is an explicit challenge, require applying the requested value.
    last = state.messages[-1] if state.messages else None
    last_text = ""
    if last is not None:
        last_text = getattr(last, "content", None) or (last.get("content") if isinstance(last, dict) else "") or ""
    if "CHALLENGE" in last_text.upper() or "RECALCULATE WITH" in last_text.upper():
        extra += (
            "\n\nCHALLENGE MODE: The user's latest message revises a major assumption. "
            "You MUST apply the requested key/value change in the assumptions JSON, "
            "set assumptions_complete=true, and keep other assumptions stable unless "
            "they directly depend on the challenged value."
        )

    # Truncate chat history — long discovery threads exceed Groq 20b TPM (413).
    recent = list(state.messages[-2:]) if state.messages else []
    messages = [SystemMessage(content=system_prompt + extra)] + recent

    try:
        response = llm.invoke(messages)
        response_text = response.content
    except Exception as e:
        state.error = str(e)
        state.next_action = "retry"
        return state

    assumption_data = _extract_json(response_text)
    if assumption_data:
        from ..models.study_state import Assumption

        def _as_str(v):
            if v is None:
                return None
            return v if isinstance(v, str) else str(v)

        assumptions = []
        for a in assumption_data.get("assumptions", []):
            conf = _as_str(a.get("confidence") or "low") or "low"
            if conf not in {"confirmed", "medium", "low"}:
                conf = "low"
            assumptions.append(Assumption(
                key=_as_str(a.get("key")) or "",
                value=_as_str(a.get("value")) or "",
                source=_as_str(a.get("source")) or "",
                confidence=conf,
                low=_as_str(a.get("low")),
                base=_as_str(a.get("base")),
                high=_as_str(a.get("high")),
            ))
        prev_items = list(state.assumptions or [])
        prev_sig = [
            (a.key, a.value, a.base) for a in prev_items
        ] if prev_items else []
        new_sig = [(a.key, a.value, a.base) for a in assumptions]
        changed = new_sig != prev_sig

        if changed or state.assumptions_version == 0:
            from datetime import datetime, timezone

            prev_version = int(state.assumptions_version or 0)
            prev_npv = None
            if state.financial_results and isinstance(state.financial_results, dict):
                prev_npv = state.financial_results.get("npv")
            changed_keys = sorted({k for k, _, _ in set(new_sig) ^ set(prev_sig)})
            history = list(getattr(state, "assumptions_history", None) or [])
            history.append({
                "version": prev_version,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "assumptions": [
                    {
                        "key": a.key,
                        "value": a.value,
                        "source": a.source,
                        "confidence": a.confidence,
                        "low": a.low,
                        "base": a.base,
                        "high": a.high,
                    }
                    for a in prev_items
                ],
                "npv_at_version": prev_npv,
                "changed_keys": changed_keys,
                "note": (
                    "Assumptions updated; prior financial results invalidated for recalculation."
                    if prev_items else
                    "Initial assumptions version recorded."
                ),
            })
            state.assumptions_history = history[-20:]  # keep last 20

            state.assumptions = assumptions
            state.assumptions_version = prev_version + 1
            # Invalidate downstream so challenge/recalc must rebuild the model.
            state.financial_results = None
            state.financial_snapshot_id = None
            state.verdict = None
            state.decision_rationale = None
            state.decision_conditions = []
            state.decision_risks = []
        else:
            state.assumptions = assumptions

        if assumption_data.get("assumptions_complete", False):
            state.phase = "READY_FOR_ANALYSIS"
            state.assumptions_approved = True
        else:
            state.phase = "ASSUMPTIONS_REVIEW"
            state.assumptions_approved = False

    state.messages.append(AIMessage(content=response_text))
    state.next_action = "review_assumptions"
    return state


def _extract_json(text: str) -> dict | None:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None
