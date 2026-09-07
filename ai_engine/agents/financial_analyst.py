from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

from ..config import get_llm
from ..models.study_state import StudyState
from ..tools.calculator import calculate_npv, calculate_irr, calculate_payback_period

EXPLAIN_PROMPT_AR = """
أنت محلل مالي خبير متخصص في دراسات الجدوى للسوق السعودي.
مهمتك: شرح النتائج المالية التالية التي تم حسابها بالفعل.

لا تحسب أي أرقام بنفسك — الأرقام أدناه محسوبة بالفعل بدقة.
اشرح كل مؤشر ومعناه للمستثمر بلغة واضحة.

قواعد صارمة:
- لا تغيّر الأرقام المحسوبة
- اشرح ماذا تعني للمستثمر
- حدد نقاط القوة والضعف
- أجب بالعربية

النتائج المحسوبة:
{computed_results}

الافتراضات المستخدمة:
{assumptions_text}

أخرج JSON داخل ```json ... ```:
{
  "revenue_projections": <من المدخلات>,
  "cost_projections": <من المدخلات>,
  "capex": <من المدخلات>,
  "npv": <محسوب>,
  "irr": <محسوب>,
  "payback_months": <محسوب>,
  "breakeven_months": 0,
  "scenarios": {
    "optimistic": {"npv": <محسوب>, "irr": <محسوب>},
    "base": {"npv": <محسوب>, "irr": <محسوب>},
    "conservative": {"npv": <محسوب>, "irr": <محسوب>}
  },
  "analysis_complete": true,
  "warnings": ["أي تحذيرات"]
}
"""

EXPLAIN_PROMPT_EN = """
You are an expert financial analyst specializing in feasibility studies for the Saudi market.
Your task: explain the following pre-computed financial results.

Do NOT calculate any numbers yourself — the numbers below are already computed accurately.
Explain what each indicator means for the investor in clear language.

Strict rules:
- Do NOT change the computed numbers
- Explain what they mean for the investor
- Identify strengths and weaknesses
- Reply in English

Computed results:
{computed_results}

Assumptions used:
{assumptions_text}

Output JSON inside ```json ... ```:
{
  "revenue_projections": <from inputs>,
  "cost_projections": <from inputs>,
  "capex": <from inputs>,
  "npv": <computed>,
  "irr": <computed>,
  "payback_months": <computed>,
  "breakeven_months": 0,
  "scenarios": {
    "optimistic": {"npv": <computed>, "irr": <computed>},
    "base": {"npv": <computed>, "irr": <computed>},
    "conservative": {"npv": <computed>, "irr": <computed>}
  },
  "analysis_complete": true,
  "warnings": ["any warnings"]
}
"""

EXTRACT_PROMPT_AR = """
أنت مساعد استخراج بيانات. من الافتراضات والأدلة أدناه، استخرج الأرقام المالية.

المطلوب استخراجه (أخرج JSON داخل ```json ... ```):
{
  "capex": <الاستثمار الأولي بالريال>,
  "annual_revenues": [<إيراد السنة 1>, <إيراد السنة 2>, <إيراد السنة 3>],
  "annual_costs": [<تكلفة السنة 1>, <تكلفة السنة 2>, <تكلفة السنة 3>],
  "discount_rate": 0.12
}

إذا لم تجد رقماً محدداً، ضع null. لا تخترع أرقاماً.
"""

EXTRACT_PROMPT_EN = """
You are a data extraction assistant. From the assumptions and evidence below, extract the financial numbers.

Required extraction (output JSON inside ```json ... ```):
{
  "capex": <initial investment in SAR>,
  "annual_revenues": [<year 1 revenue>, <year 2 revenue>, <year 3 revenue>],
  "annual_costs": [<year 1 cost>, <year 2 cost>, <year 3 cost>],
  "discount_rate": 0.12
}

If a specific number is not found, put null. Do NOT invent numbers.
"""


def _extract_financials_from_assumptions(state: StudyState) -> dict | None:
    lang = state.language
    llm = get_llm("extraction")

    context_parts = []
    if state.assumptions:
        for a in state.assumptions:
            context_parts.append(f"- {a.key}: {a.value} (low: {a.low}, base: {a.base}, high: {a.high})")
    if state.claims:
        for c in state.claims[:10]:
            context_parts.append(f"- {c.statement} ({c.source_type})")

    if not context_parts:
        return None

    prompt = (EXTRACT_PROMPT_AR if lang == "ar" else EXTRACT_PROMPT_EN) + "\n\n" + "\n".join(context_parts)

    try:
        response = llm.invoke([SystemMessage(content=prompt)])
        return _extract_json(response.content)
    except Exception:
        return None


def _compute_scenario(capex: float, revenues: list, costs: list, discount_rate: float, multiplier: float) -> dict:
    adj_revenues = [r * multiplier for r in revenues]
    adj_costs = [c * (2 - multiplier) for c in costs]
    cash_flows = [-capex] + [r - c for r, c in zip(adj_revenues, adj_costs)]
    annual_net = [r - c for r, c in zip(adj_revenues, adj_costs)]

    npv = calculate_npv(cash_flows, discount_rate)
    irr = calculate_irr(cash_flows)
    payback = calculate_payback_period(capex, annual_net)

    return {
        "npv": npv,
        "irr": round(irr, 4) if irr is not None else None,
        "payback_months": round(payback * 12, 1) if payback is not None else None,
    }


def run_financial_analysis(state: StudyState) -> StudyState:
    lang = state.language
    llm = get_llm("decision")

    extracted = _extract_financials_from_assumptions(state)

    if not extracted:
        state.error = "Could not extract financial data from assumptions." if lang == "en" else "لم يتم استخراج البيانات المالية من الافتراضات."
        state.next_action = "retry"
        return state

    capex = extracted.get("capex") or 0
    revenues = extracted.get("annual_revenues") or [0, 0, 0]
    costs = extracted.get("annual_costs") or [0, 0, 0]
    discount_rate = extracted.get("discount_rate") or 0.12

    revenues = [float(r) if r else 0 for r in revenues]
    costs = [float(c) if c else 0 for c in costs]
    capex = float(capex)

    base = _compute_scenario(capex, revenues, costs, discount_rate, 1.0)
    optimistic = _compute_scenario(capex, revenues, costs, discount_rate, 1.2)
    conservative = _compute_scenario(capex, revenues, costs, discount_rate, 0.8)

    computed = {
        "capex": capex,
        "revenue_projections": {"year_1": revenues[0], "year_2": revenues[1] if len(revenues) > 1 else 0, "year_3": revenues[2] if len(revenues) > 2 else 0},
        "cost_projections": {"year_1": costs[0], "year_2": costs[1] if len(costs) > 1 else 0, "year_3": costs[2] if len(costs) > 2 else 0},
        "npv": base["npv"],
        "irr": base["irr"],
        "payback_months": base["payback_months"],
        "scenarios": {
            "optimistic": {"npv": optimistic["npv"], "irr": optimistic["irr"]},
            "base": {"npv": base["npv"], "irr": base["irr"]},
            "conservative": {"npv": conservative["npv"], "irr": conservative["irr"]},
        },
    }

    assumptions_text = "\n".join(
        f"- {a.key}: {a.value}" for a in state.assumptions
    ) if state.assumptions else "No assumptions provided."

    explain_prompt = (EXPLAIN_PROMPT_AR if lang == "ar" else EXPLAIN_PROMPT_EN).format(
        computed_results=json.dumps(computed, ensure_ascii=False, indent=2),
        assumptions_text=assumptions_text,
    )

    try:
        response = llm.invoke([SystemMessage(content=explain_prompt)] + state.messages)
        response_text = response.content
    except Exception as e:
        state.financial_results = computed
        state.financial_results["analysis_complete"] = True
        state.financial_results["warnings"] = [str(e)]
        state.phase = "ANALYZED"
        state.messages.append(AIMessage(content=json.dumps(computed, ensure_ascii=False, indent=2)))
        state.next_action = "review_financials"
        return state

    financial_data = _extract_json(response_text)
    if financial_data:
        financial_data["npv"] = computed["npv"]
        financial_data["irr"] = computed["irr"]
        financial_data["payback_months"] = computed["payback_months"]
        financial_data["scenarios"] = computed["scenarios"]
        state.financial_results = financial_data
    else:
        computed["analysis_complete"] = True
        computed["warnings"] = []
        state.financial_results = computed

    state.phase = "ANALYZED"
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
