from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

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
    if state.profile:
        context_parts.append(f"Project: {state.profile.archetype} / {state.profile.sector}")
    if state.claims:
        claims_text = "\n".join(f"- {c.statement} ({c.source_type}, confidence: {c.confidence})" for c in state.claims)
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
        from ..models.study_state import Assumption

        assumptions = []
        for a in assumption_data.get("assumptions", []):
            assumptions.append(Assumption(
                key=a.get("key", ""),
                value=a.get("value", ""),
                source=a.get("source", ""),
                confidence=a.get("confidence", "low"),
                low=a.get("low"),
                base=a.get("base"),
                high=a.get("high"),
            ))
        state.assumptions = assumptions

        if assumption_data.get("assumptions_complete", False):
            state.phase = "READY_FOR_ANALYSIS"
            state.assumptions_approved = True
        else:
            state.phase = "ASSUMPTIONS_REVIEW"

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
