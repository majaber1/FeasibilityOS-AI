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
__COMPUTED_RESULTS__

الافتراضات المستخدمة:
__ASSUMPTIONS_TEXT__

أخرج JSON داخل ```json ... ```:
{{
  "revenue_projections": <من المدخلات>,
  "cost_projections": <من المدخلات>,
  "capex": <من المدخلات>,
  "npv": <محسوب>,
  "irr": <محسوب>,
  "payback_months": <محسوب>,
  "breakeven_months": 0,
  "scenarios": {{
    "optimistic": {{"npv": <محسوب>, "irr": <محسوب>}},
    "base": {{"npv": <محسوب>, "irr": <محسوب>}},
    "conservative": {{"npv": <محسوب>, "irr": <محسوب>}}
  }},
  "analysis_complete": true,
  "warnings": ["أي تحذيرات"]
}}
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
__COMPUTED_RESULTS__

Assumptions used:
__ASSUMPTIONS_TEXT__

Output JSON inside ```json ... ```:
{{
  "revenue_projections": <from inputs>,
  "cost_projections": <from inputs>,
  "capex": <from inputs>,
  "npv": <computed>,
  "irr": <computed>,
  "payback_months": <computed>,
  "breakeven_months": 0,
  "scenarios": {{
    "optimistic": {{"npv": <computed>, "irr": <computed>}},
    "base": {{"npv": <computed>, "irr": <computed>}},
    "conservative": {{"npv": <computed>, "irr": <computed>}}
  }},
  "analysis_complete": true,
  "warnings": ["any warnings"]
}}
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

_NUMBER_RE = re.compile(
    r"(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)",
)


def _parse_number(raw: str | float | int | None) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip()
    if not text or text.lower() in {"null", "none", "n/a", "-"}:
        return None
    is_percent = "%" in text or "٪" in text
    cleaned = (
        text.replace("٬", ",")
        .replace("ر.س", " ")
        .replace("SAR", " ")
        .replace("sar", " ")
        .replace("%", " ")
        .replace("٪", " ")
    )
    match = _NUMBER_RE.search(cleaned)
    if not match:
        return None
    try:
        value = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    if is_percent:
        return value / 100.0 if value > 1 else value
    return value


def _assumption_lookup(state: StudyState) -> dict[str, float]:
    """Best-effort numeric map from assumption keys/values for deterministic fallback."""
    found: dict[str, float] = {}
    for a in state.assumptions or []:
        key = (a.key or "").lower()
        for candidate in (a.base, a.value, a.low, a.high):
            num = _parse_number(candidate)
            if num is None:
                continue
            found[key] = num
            break
    return found


def _deterministic_extract(state: StudyState) -> dict | None:
    """Build capex/revenues/costs from structured assumptions when LLM extraction fails."""
    vals = _assumption_lookup(state)
    answers = (state.profile.structured_answers if state.profile else {}) or {}
    archetype = state.profile.archetype if state.profile else "unknown"

    # Merge numeric structured answers into lookup (discovery → finance bridge).
    for key, raw in answers.items():
        num = _parse_number(raw if not isinstance(raw, bool) else None)
        if num is not None:
            vals[str(key).lower()] = num

    if not vals and not answers:
        return None

    def first(*needles: str) -> float | None:
        for key, value in vals.items():
            if any(n in key for n in needles):
                return value
        return None

    capex = first(
        "initial investment",
        "capex",
        "seed",
        "استثمار",
        "رأس المال",
        "development_cost",
        "funding_goal",
        "remaining_construction_cost",
        "required_funding",
    )
    discount = first("discount rate", "معدل الخصم") or 0.12
    if discount is not None and discount > 1:
        discount = discount / 100.0

    annual_revenues = None
    annual_costs = None

    # --- Archetype-specific deterministic models ---
    if archetype == "saas_digital":
        price = first("subscription_price", "price", "pricing", "سعر")
        customers = first("year1_customers", "customers", "عملاء")
        cac = first("cac", "acquisition")
        churn = first("churn", "تسرب") or 0
        cloud = first("cloud", "ai_cost", "cloud_ai_cost") or 0
        team = first("team", "team_cost", "تطوير") or 0
        if price is not None and customers is not None:
            # Monthly SaaS: price * customers * 12, light growth, churn drag
            churn_f = (churn / 100.0) if churn > 1 else float(churn)
            y1 = price * customers * 12 * max(0.0, 1.0 - churn_f * 6)
            annual_revenues = [y1, y1 * 1.5, y1 * 1.5 * 1.4]
            opex_m = (cac or 0) * (customers / 12.0) + cloud + team
            annual_costs = [opex_m * 12, opex_m * 12 * 1.2, opex_m * 12 * 1.3]
            if capex is None:
                capex = first("development_cost") or (team * 12 if team else 0) or (customers * (cac or 0))

    elif archetype == "real_estate":
        units = first("units", "number_of_units", "وحدات")
        price = first("selling_price", "rental_price", "سعر")
        remaining = first("remaining_construction_cost", "required_funding")
        incurred = first("cost_incurred", "cost")
        if units is not None and price is not None:
            # Sell-through over 3 years: 40/35/25
            gross = units * price
            annual_revenues = [gross * 0.4, gross * 0.35, gross * 0.25]
            build = remaining or 0
            annual_costs = [build * 0.5, build * 0.35, build * 0.15]
            if capex is None:
                capex = (incurred or 0) + (remaining or 0)

    elif archetype == "data_center":
        racks = first("rack", "rack_capacity")
        util = first("utilization", "اشغال") or 0.6
        if util > 1:
            util = util / 100.0
        rev_rack = first("revenue", "rack_revenue") or 15000  # SAR/rack/mo placeholder only if user gave racks
        opex = first("opex") or 0
        capex_ans = first("capex")
        if racks is not None:
            monthly = racks * rev_rack * util
            annual_revenues = [monthly * 12, monthly * 12 * 1.15, monthly * 12 * 1.25]
            annual_costs = [
                (opex or monthly * 0.45) * 12,
                (opex or monthly * 0.45) * 12 * 1.1,
                (opex or monthly * 0.45) * 12 * 1.15,
            ]
            if capex is None:
                capex = capex_ans

    elif archetype == "government_contract":
        award = first("award_value", "contract_value", "قيمة")
        margin = first("expected_margin", "margin", "هامش") or 10
        if margin > 1:
            margin = margin / 100.0
        exec_cost = first("execution_costs", "execution")
        if award is not None:
            # Recognize revenue over contract years (assume 2–3)
            annual_revenues = [award * 0.4, award * 0.35, award * 0.25]
            cost_total = exec_cost if exec_cost is not None else award * (1 - margin)
            annual_costs = [cost_total * 0.45, cost_total * 0.35, cost_total * 0.2]
            if capex is None:
                capex = first("cash_flow_gap", "financing_need") or cost_total * 0.2

    # Legacy marketplace / rideshare extraction
    atv = first("average trip", "atv", "ticket", "قيمة الرحلة", "متوسط")
    take_rate = first("take-rate", "take rate", "commission", "عمولة")
    rides = first("monthly rides", "rides/mo", "rides per month", "رحلات")
    fixed_opex = first("fixed opex", "monthly fixed", "opex", "تشغيل")
    variable = first("variable cost", "per ride", "تكلفة متغيرة")

    if take_rate is not None and take_rate > 1:
        take_rate = take_rate / 100.0

    if annual_revenues is None and atv is not None and take_rate is not None and rides is not None:
        monthly_revenue = atv * take_rate * rides
        annual_revenues = [
            monthly_revenue * 12,
            monthly_revenue * 12 * 1.4,
            monthly_revenue * 12 * 1.4 * 1.3,
        ]
        monthly_cost = (fixed_opex or 0) + (variable or 0) * rides
        annual_costs = [monthly_cost * 12, monthly_cost * 12 * 1.2, monthly_cost * 12 * 1.3]

    if annual_revenues is None:
        rev = first("annual revenue", "revenue_y1", "year1_revenue", "إيراد")
        if rev is not None:
            annual_revenues = [rev, rev * 1.2, rev * 1.4]
    if annual_costs is None:
        cost = first("annual cost", "annual opex", "cost_y1", "تكاليف")
        if cost is not None:
            annual_costs = [cost, cost * 1.1, cost * 1.15]

    if capex is None and annual_revenues is None:
        return None

    return {
        "capex": capex,
        "annual_revenues": annual_revenues,
        "annual_costs": annual_costs,
        "discount_rate": discount,
    }


def _merge_extract(primary: dict | None, fallback: dict | None) -> dict | None:
    if not primary and not fallback:
        return None
    primary = primary or {}
    fallback = fallback or {}
    merged = {
        "capex": primary.get("capex") if primary.get("capex") is not None else fallback.get("capex"),
        "annual_revenues": primary.get("annual_revenues") or fallback.get("annual_revenues"),
        "annual_costs": primary.get("annual_costs") or fallback.get("annual_costs"),
        "discount_rate": primary.get("discount_rate") if primary.get("discount_rate") is not None else fallback.get("discount_rate", 0.12),
    }
    if merged["capex"] is None and not merged["annual_revenues"] and not merged["annual_costs"]:
        return None
    return merged


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

    llm_extracted = None
    if context_parts:
        prompt = (EXTRACT_PROMPT_AR if lang == "ar" else EXTRACT_PROMPT_EN) + "\n\n" + "\n".join(context_parts)
        try:
            response = llm.invoke([SystemMessage(content=prompt)])
            llm_extracted = _extract_json(response.content)
        except Exception:
            llm_extracted = None

    return _merge_extract(llm_extracted, _deterministic_extract(state))


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
        missing = []
        keys = {(a.key or "").lower() for a in (state.assumptions or [])}
        for needle, label in (
            ("capex", "capex/initial_investment"),
            ("revenue", "revenue"),
            ("cost", "opex/costs"),
            ("customer", "customers"),
            ("price", "pricing"),
        ):
            if not any(needle in k for k in keys):
                missing.append(label)
        state.financial_results = {
            "status": "MODEL_INCOMPLETE",
            "reason": "INSUFFICIENT_DATA",
            "missing_data": missing or ["financial_assumptions"],
            "analysis_complete": False,
            "npv": None,
            "irr": None,
            "payback_months": None,
            "scenarios": {},
        }
        state.verdict = "NEED_MORE_VALIDATION"
        state.phase = "ANALYZED"
        state.next_action = "complete_financial_inputs"
        msg = (
            "Financial model incomplete — missing required inputs: "
            + ", ".join(state.financial_results["missing_data"])
            if lang == "en"
            else "النموذج المالي غير مكتمل — المدخلات الناقصة: "
            + ", ".join(state.financial_results["missing_data"])
        )
        state.messages.append(AIMessage(content=msg))
        state.error = None
        return state

    capex = extracted.get("capex")
    revenues = extracted.get("annual_revenues")
    costs = extracted.get("annual_costs")
    discount_rate = extracted.get("discount_rate") or 0.12

    # Incomplete when revenue/cash-flow cannot be formed — do not fake NPV=-CAPEX.
    if not revenues or all((r or 0) == 0 for r in revenues):
        missing = ["annual_revenues"]
        if capex is None:
            missing.insert(0, "capex")
        if not costs:
            missing.append("annual_costs")
        state.financial_results = {
            "status": "MODEL_INCOMPLETE",
            "reason": "INSUFFICIENT_DATA",
            "missing_data": missing,
            "analysis_complete": False,
            "capex": capex,
            "npv": None,
            "irr": None,
            "payback_months": None,
            "scenarios": {},
        }
        state.verdict = "NEED_MORE_VALIDATION"
        state.phase = "ANALYZED"
        state.next_action = "complete_financial_inputs"
        msg = (
            "Financial model incomplete — cannot compute ROI/NPV without revenue/cash-flow. Missing: "
            + ", ".join(missing)
            if lang == "en"
            else "النموذج المالي غير مكتمل — لا يمكن حساب العائد/صافي القيمة الحالية بدون إيرادات. الناقص: "
            + ", ".join(missing)
        )
        state.messages.append(AIMessage(content=msg))
        state.error = None
        return state

    capex = float(capex or 0)
    revenues = list(revenues or [0, 0, 0])
    costs = list(costs or [0, 0, 0])

    # Normalize lengths to 3 years
    while len(revenues) < 3:
        revenues.append(revenues[-1] if revenues else 0)
    while len(costs) < 3:
        costs.append(costs[-1] if costs else 0)
    revenues = [float(r) if r else 0 for r in revenues[:3]]
    costs = [float(c) if c else 0 for c in costs[:3]]
    capex = float(capex)
    discount_rate = float(discount_rate)
    if discount_rate > 1:
        discount_rate = discount_rate / 100.0

    base = _compute_scenario(capex, revenues, costs, discount_rate, 1.0)
    optimistic = _compute_scenario(capex, revenues, costs, discount_rate, 1.2)
    conservative = _compute_scenario(capex, revenues, costs, discount_rate, 0.8)

    computed = {
        "capex": capex,
        "revenue_projections": {"year_1": revenues[0], "year_2": revenues[1], "year_3": revenues[2]},
        "cost_projections": {"year_1": costs[0], "year_2": costs[1], "year_3": costs[2]},
        "npv": base["npv"],
        "irr": base["irr"],
        "payback_months": base["payback_months"],
        "scenarios": {
            "BASE": {"npv": base["npv"], "irr": base["irr"], "payback_months": base["payback_months"]},
            "UPSIDE": {"npv": optimistic["npv"], "irr": optimistic["irr"], "payback_months": optimistic["payback_months"]},
            "DOWNSIDE": {"npv": conservative["npv"], "irr": conservative["irr"], "payback_months": conservative["payback_months"]},
            "optimistic": {"npv": optimistic["npv"], "irr": optimistic["irr"]},
            "base": {"npv": base["npv"], "irr": base["irr"]},
            "conservative": {"npv": conservative["npv"], "irr": conservative["irr"]},
        },
    }

    assumptions_text = "\n".join(
        f"- {a.key}: {a.value}" for a in state.assumptions
    ) if state.assumptions else "No assumptions provided."

    # IMPORTANT: do not use str.format() on prompts that contain JSON braces.
    explain_prompt = (EXPLAIN_PROMPT_AR if lang == "ar" else EXPLAIN_PROMPT_EN)
    explain_prompt = explain_prompt.replace(
        "__COMPUTED_RESULTS__", json.dumps(computed, ensure_ascii=False, indent=2)
    ).replace("__ASSUMPTIONS_TEXT__", assumptions_text)
    # Convert doubled braces (documentation leftovers) back to single braces for the model.
    explain_prompt = explain_prompt.replace("{{", "{").replace("}}", "}")

    try:
        response = llm.invoke([SystemMessage(content=explain_prompt)] + state.messages)
        response_text = response.content
    except Exception as e:
        state.error = None
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
        financial_data.setdefault("revenue_projections", computed["revenue_projections"])
        financial_data.setdefault("cost_projections", computed["cost_projections"])
        financial_data.setdefault("capex", computed["capex"])
        financial_data["analysis_complete"] = True
        state.financial_results = financial_data
    else:
        computed["analysis_complete"] = True
        computed["warnings"] = []
        state.financial_results = computed

    state.error = None
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
    # Fallback: first JSON object in the text
    brace = re.search(r"\{[\s\S]*\}", text)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            return None
    return None
