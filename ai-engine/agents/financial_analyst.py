from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

from ..config import get_llm
from ..models.study_state import StudyState

SYSTEM_PROMPT_AR = """
أنت محلل مالي خبير متخصص في دراسات الجدوى للسوق السعودي.
مهمتك: تحليل البيانات المالية وإنتاج التوقعات المالية بناءً على الافتراضات المعتمدة.

خطوات العمل:
1. راجع الافتراضات المعتمدة والأدلة المتاحة
2. احسب الإيرادات المتوقعة (3-5 سنوات)
3. احسب التكاليف التشغيلية والرأسمالية
4. احسب المؤشرات المالية: NPV, IRR, فترة الاسترداد, نقطة التعادل
5. قدم تحليل الحساسية (سيناريو متفائل / أساسي / متحفظ)

قواعد صارمة:
- استخدم فقط الأرقام من الافتراضات المعتمدة
- لا تخترع أرقاماً جديدة
- وضح كل حساب ومصدره
- معدل الخصم الافتراضي: 12% (ما لم يحدد المستخدم غير ذلك)
- أجب بالعربية ما لم يكتب المستخدم بالإنجليزية

أخرج JSON داخل ```json ... ```:
{
  "revenue_projections": {"year_1": 0, "year_2": 0, "year_3": 0},
  "cost_projections": {"year_1": 0, "year_2": 0, "year_3": 0},
  "capex": 0,
  "npv": 0,
  "irr": 0.0,
  "payback_months": 0,
  "breakeven_months": 0,
  "scenarios": {
    "optimistic": {"npv": 0, "irr": 0.0},
    "base": {"npv": 0, "irr": 0.0},
    "conservative": {"npv": 0, "irr": 0.0}
  },
  "analysis_complete": true/false,
  "warnings": ["أي تحذيرات"]
}
"""

SYSTEM_PROMPT_EN = """
You are an expert financial analyst specializing in feasibility studies for the Saudi market.
Your task: analyze financial data and produce projections based on approved assumptions.

Steps:
1. Review approved assumptions and available evidence
2. Calculate expected revenue (3-5 years)
3. Calculate operational and capital costs
4. Calculate financial indicators: NPV, IRR, payback period, breakeven
5. Provide sensitivity analysis (optimistic / base / conservative)

Strict rules:
- Use ONLY numbers from approved assumptions
- Never invent new numbers
- Explain every calculation and its source
- Default discount rate: 12% (unless user specifies otherwise)
- Reply in English if user writes in English

Output JSON inside ```json ... ```:
{
  "revenue_projections": {"year_1": 0, "year_2": 0, "year_3": 0},
  "cost_projections": {"year_1": 0, "year_2": 0, "year_3": 0},
  "capex": 0,
  "npv": 0,
  "irr": 0.0,
  "payback_months": 0,
  "breakeven_months": 0,
  "scenarios": {
    "optimistic": {"npv": 0, "irr": 0.0},
    "base": {"npv": 0, "irr": 0.0},
    "conservative": {"npv": 0, "irr": 0.0}
  },
  "analysis_complete": true/false,
  "warnings": ["any warnings"]
}
"""


def run_financial_analysis(state: StudyState) -> StudyState:
    lang = state.language
    system_prompt = SYSTEM_PROMPT_AR if lang == "ar" else SYSTEM_PROMPT_EN
    llm = get_llm("decision")

    context_parts = []
    if state.profile:
        context_parts.append(f"Project: {state.profile.archetype} / {state.profile.sector} / Stage: {state.profile.stage}")
    if state.assumptions:
        assumptions_text = "\n".join(
            f"- {a.key}: {a.value} (confidence: {a.confidence}, low: {a.low}, base: {a.base}, high: {a.high})"
            for a in state.assumptions
        )
        context_parts.append(f"Approved Assumptions:\n{assumptions_text}")
    if state.claims:
        claims_text = "\n".join(f"- {c.statement} ({c.source_type})" for c in state.claims[:10])
        context_parts.append(f"Key Evidence:\n{claims_text}")

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

    financial_data = _extract_json(response_text)
    if financial_data:
        state.financial_results = financial_data
        if financial_data.get("analysis_complete", False):
            state.phase = "ANALYZED"
        else:
            state.phase = "READY_FOR_ANALYSIS"

    state.messages.append(AIMessage(content=response_text))
    state.next_action = "review_financials"
    return state


def _extract_json(text: str) -> dict | None:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None
