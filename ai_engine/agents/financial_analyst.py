from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

from ..config import get_llm
from ..models.study_state import StudyState
from ..tools.calculator import calculate_npv, calculate_irr, calculate_payback_period
from ..tools.financial_trust import (
    attach_financial_display_fields,
    irr_metric_state,
    irr_user_message,
    payback_metric_state,
    payback_user_message,
    services_capacity_revenue,
    validate_financial_inputs,
)

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
    if not vals:
        return None

    def first(*needles: str) -> float | None:
        for key, value in vals.items():
            if any(n in key for n in needles):
                return value
        return None

    capex = first(
        "initial_investment", "initial investment", "capex", "seed", "استثمار", "رأس المال",
        "land_cost", "construction_boq", "capex_machinery",
    )
    # Prefer summing land + BOQ for real estate when both present.
    land = first("land_cost", "land cost")
    boq = first("construction_boq", "construction boq", "boq")
    if land is not None or boq is not None:
        capex = (land or 0.0) + (boq or 0.0)

    atv = first("avg_trip_value", "average trip", "atv", "ticket", "قيمة الرحلة", "متوسط")
    take_rate = first("take_rate", "take-rate", "take rate", "commission", "عمولة")
    rides = first("monthly_trips", "monthly rides", "rides/mo", "rides per month", "رحلات")
    fixed_opex = first("monthly_fixed_opex", "fixed opex", "monthly fixed", "opex", "تشغيل", "opex_year1")
    variable = first("variable cost", "per ride", "تكلفة متغيرة")
    discount = first("discount rate", "معدل الخصم") or 0.12

    # Professional / managed services model
    mrc = first("monthly_recurring_contracts", "monthly recurring", "mrc", "monthly_retainer")
    delivery_monthly = first("delivery_cost_monthly", "delivery cost")
    gross_margin = first("gross_margin", "gross margin")
    billing_rate = first(
        "billing_rate",
        "hourly_rate",
        "average_billing_rate",
        "bill_rate",
        "سعر الساعة",
        "معدل الفوترة",
    )
    utilization_rate = first("utilization_rate", "utilization", "billable utilization", "نسبة الاستخدام")
    consultants_headcount = first(
        "consultants_headcount",
        "headcount",
        "fte",
        "consultants",
        "employees",
        "عدد المستشارين",
    )
    active_contracts = first("active_contracts", "contracts", "clients", "عقود")
    billable_hours_month = first("billable_hours_month", "billable_hours", "hours_per_month")
    billable_period = first(
        "billable_period",
        "billable_period_hours",
        "annual_billable_hours",
        "billable_months",
        "فترة الفوترة",
    )
    extract_notes: list[str] = []

    # Real estate sales model
    units = first("units", "unit count")
    selling_price = first("selling_price", "selling price")
    absorption = first("absorption_rate", "absorption")

    # Data center model
    mw = first("mw_capacity", "mw")
    pricing_kw = first("pricing_per_kw", "pricing per kw")
    occupancy = first("occupancy")
    power_cost = first("power_cost", "power cost")
    capex_total = first("capex_total", "total capex")
    opex_annual = first("opex_annual", "annual opex")
    if capex_total is not None and (capex is None or capex == 0):
        capex = capex_total

    # SaaS
    arr = first("arr", "annual recurring")
    mrr = first("mrr")
    pricing = first("pricing", "subscription")
    customers = first("target_customers", "customers")

    if take_rate is not None and take_rate > 1:
        take_rate = take_rate / 100.0
    if occupancy is not None and occupancy > 1:
        occupancy = occupancy / 100.0
    if gross_margin is not None and gross_margin > 1:
        gross_margin = gross_margin / 100.0
    if discount is not None and discount > 1:
        discount = discount / 100.0

    annual_revenues = None
    annual_costs = None

    # Services: prefer capacity revenue (billing_rate × utilization × resources),
    # fall back to MRC — never silently ignore utilization/headcount.
    services_y1, services_notes = services_capacity_revenue(
        billing_rate=billing_rate,
        utilization_rate=utilization_rate,
        headcount=consultants_headcount,
        active_contracts=active_contracts,
        billable_hours_month=billable_hours_month,
        billable_period=billable_period,
        mrc=mrc,
    )
    extract_notes.extend(services_notes)
    if services_y1 is not None:
        annual_revenues = [services_y1, services_y1 * 1.25, services_y1 * 1.5]
        if delivery_monthly is not None:
            annual_costs = [
                delivery_monthly * 12,
                delivery_monthly * 12 * 1.15,
                delivery_monthly * 12 * 1.3,
            ]
        elif gross_margin is not None:
            annual_costs = [r * (1.0 - gross_margin) for r in annual_revenues]
        else:
            # Trust hardening: never default services OPEX to zero (inflates NPV).
            # Conservative 55% delivery-cost ratio when margin/delivery missing.
            default_cost_ratio = 0.55
            annual_costs = [r * default_cost_ratio for r in annual_revenues]
            extract_notes.append("services_opex_defaulted_from_55pct_cost_ratio")
    elif atv is not None and take_rate is not None and rides is not None:
        monthly_revenue = atv * take_rate * rides
        annual_revenues = [
            monthly_revenue * 12,
            monthly_revenue * 12 * 1.4,
            monthly_revenue * 12 * 1.4 * 1.3,
        ]
    elif units is not None and selling_price is not None:
        sold_y1 = min(units, absorption) if absorption is not None else units * 0.35
        annual_revenues = [
            sold_y1 * selling_price,
            min(units, sold_y1 * 1.2) * selling_price,
            min(units, sold_y1 * 1.35) * selling_price,
        ]
    elif mw is not None and pricing_kw is not None:
        occ = occupancy if occupancy is not None else 0.5
        monthly = mw * 1000.0 * pricing_kw * occ
        annual_revenues = [monthly * 12, monthly * 12 * 1.25, monthly * 12 * 1.4]
        if power_cost is not None:
            # rough power opex from MW * PUE~1.4 * hours
            pue = first("pue") or 1.4
            annual_power = mw * 1000.0 * 8760.0 * pue * power_cost * occ
            base_opex = opex_annual or 0.0
            annual_costs = [
                annual_power + base_opex,
                annual_power * 1.05 + base_opex * 1.05,
                annual_power * 1.1 + base_opex * 1.1,
            ]
        elif opex_annual is not None:
            annual_costs = [opex_annual, opex_annual * 1.05, opex_annual * 1.1]
    elif arr is not None:
        annual_revenues = [arr, arr * 1.4, arr * 1.4 * 1.3]
    elif mrr is not None:
        annual_revenues = [mrr * 12, mrr * 12 * 1.4, mrr * 12 * 1.4 * 1.3]
    elif pricing is not None and customers is not None:
        annual_revenues = [
            pricing * customers,
            pricing * customers * 1.5,
            pricing * customers * 2.0,
        ]

    if fixed_opex is not None and annual_costs is None:
        # monthly_fixed_opex vs annual opex_year1
        if "opex_year1" in vals or any("opex_year1" in k for k in vals):
            base = fixed_opex
            annual_costs = [base, base * 1.1, base * 1.2]
        else:
            var = variable or 0.0
            ride_count = rides or 0.0
            monthly_cost = fixed_opex + (var * ride_count)
            annual_costs = [
                monthly_cost * 12,
                monthly_cost * 12 * 1.15,
                monthly_cost * 12 * 1.25,
            ]

    if capex is None and annual_revenues is None and annual_costs is None:
        return None

    # Data center / other revenue models: never leave costs as silent None → [0,0,0].
    if annual_revenues is not None and annual_costs is None:
        annual_costs = [r * 0.45 for r in annual_revenues]
        extract_notes.append("opex_defaulted_from_45pct_of_revenue_missing_cost_inputs")

    assumption_values: dict[str, float] = {
        k: vals[k]
        for k in (
            "mw_capacity",
            "mw",
            "units",
            "unit_count",
            "consultants_headcount",
            "headcount",
        )
        if k in vals
    }
    if mw is not None:
        assumption_values.setdefault("mw_capacity", mw)
    if units is not None:
        assumption_values.setdefault("units", units)
    if consultants_headcount is not None:
        assumption_values.setdefault("consultants_headcount", consultants_headcount)

    return {
        "capex": capex,
        "annual_revenues": annual_revenues,
        "annual_costs": annual_costs,
        "discount_rate": discount if discount is not None else 0.12,
        "extract_notes": extract_notes,
        "assumption_values": assumption_values,
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
        "extract_notes": list(fallback.get("extract_notes") or []) + list(primary.get("extract_notes") or []),
        "assumption_values": {
            **(fallback.get("assumption_values") or {}),
            **(primary.get("assumption_values") or {}),
        },
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
        "cash_flows": [round(cf, 2) for cf in cash_flows],
        "revenue_projections": [round(r, 2) for r in adj_revenues],
        "cost_projections": [round(c, 2) for c in adj_costs],
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
    extract_notes = list(extracted.get("extract_notes") or [])
    assumption_values = dict(extracted.get("assumption_values") or {})

    # Normalize lengths to 3 years
    while len(revenues) < 3:
        revenues.append(revenues[-1] if revenues else 0)
    while len(costs) < 3:
        costs.append(costs[-1] if costs else 0)
    revenues = [float(r) if r else 0 for r in revenues[:3]]
    costs = [float(c) if c else 0 for c in costs[:3]]
    # Trust hardening: never silently treat missing costs as zero when revenue exists.
    if any(r > 0 for r in revenues) and all(c == 0 for c in costs):
        costs = [r * 0.45 for r in revenues]
        extract_notes.append("opex_defaulted_from_45pct_of_revenue_zero_cost_vector")
    capex = float(capex)
    discount_rate = float(discount_rate)
    if discount_rate > 1:
        discount_rate = discount_rate / 100.0

    base = _compute_scenario(capex, revenues, costs, discount_rate, 1.0)
    optimistic = _compute_scenario(capex, revenues, costs, discount_rate, 1.2)
    conservative = _compute_scenario(capex, revenues, costs, discount_rate, 0.8)

    archetype = getattr(getattr(state, "profile", None), "archetype", None) or getattr(state, "archetype", None)
    trust_warnings = validate_financial_inputs(
        archetype=archetype,
        capex=capex,
        annual_revenues=revenues,
        annual_costs=costs,
        assumptions=assumption_values,
        language=lang or "en",
    )
    if "services_opex_defaulted_from_55pct_cost_ratio" in extract_notes:
        trust_warnings.append(
            "Operating costs were estimated at 55% of revenue because delivery cost / gross margin were missing."
            if lang != "ar"
            else "تم تقدير تكاليف التشغيل بنسبة 55% من الإيراد لعدم توفر تكلفة التسليم / هامش الربح."
        )
    if "opex_defaulted_from_45pct_of_revenue_missing_cost_inputs" in extract_notes or (
        "opex_defaulted_from_45pct_of_revenue_zero_cost_vector" in extract_notes
    ):
        trust_warnings.append(
            "Operating costs were estimated because cost inputs were missing — review before relying on NPV."
            if lang != "ar"
            else "تم تقدير تكاليف التشغيل لنقص مدخلات التكلفة — راجع قبل الاعتماد على صافي القيمة الحالية."
        )

    computed = {
        "capex": capex,
        "revenue_projections": {"year_1": revenues[0], "year_2": revenues[1], "year_3": revenues[2]},
        "cost_projections": {"year_1": costs[0], "year_2": costs[1], "year_3": costs[2]},
        "cash_flows": base["cash_flows"],
        "discount_rate": discount_rate,
        "npv": base["npv"],
        "irr": base["irr"],
        "irr_display": irr_user_message(base["irr"], language=lang or "en"),
        "irr_available": base["irr"] is not None,
        "irr_state": irr_metric_state(base["irr"], language=lang or "en"),
        "payback_months": base["payback_months"],
        "payback_display": payback_user_message(base["payback_months"], language=lang or "en"),
        "payback_available": base["payback_months"] is not None,
        "payback_state": payback_metric_state(base["payback_months"], language=lang or "en"),
        "warnings": trust_warnings,
        "extract_notes": extract_notes,
        "scenarios": {
            "optimistic": {
                "npv": optimistic["npv"],
                "irr": optimistic["irr"],
                "irr_display": irr_user_message(optimistic["irr"], language=lang or "en"),
            },
            "base": {
                "npv": base["npv"],
                "irr": base["irr"],
                "irr_display": irr_user_message(base["irr"], language=lang or "en"),
            },
            "conservative": {
                "npv": conservative["npv"],
                "irr": conservative["irr"],
                "irr_display": irr_user_message(conservative["irr"], language=lang or "en"),
            },
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

    lang = getattr(state, "language", "en") or "en"
    try:
        response = llm.invoke([SystemMessage(content=explain_prompt)] + state.messages)
        response_text = response.content
    except Exception as e:
        from ..utils.safe_messages import sanitize_error_for_user

        sanitize_error_for_user(e, language=lang, context="financial.explain")
        state.error = None
        state.financial_results = computed
        state.financial_results["analysis_complete"] = True
        state.financial_results["warnings"] = list(trust_warnings) + ["explain_model_unavailable"]
        state.phase = "ANALYZED"
        state.messages.append(AIMessage(content=_financial_chat_summary(computed, lang)))
        state.next_action = "review_financials"
        return state

    financial_data = _extract_json(response_text)
    if financial_data:
        financial_data["npv"] = computed["npv"]
        financial_data["irr"] = computed["irr"]
        financial_data["irr_display"] = computed["irr_display"]
        financial_data["irr_available"] = computed["irr_available"]
        financial_data["irr_state"] = computed["irr_state"]
        financial_data["payback_months"] = computed["payback_months"]
        financial_data["payback_display"] = computed["payback_display"]
        financial_data["payback_available"] = computed["payback_available"]
        financial_data["payback_state"] = computed["payback_state"]
        financial_data["cash_flows"] = computed["cash_flows"]
        financial_data = attach_financial_display_fields(financial_data, language=lang or "en")
        financial_data["discount_rate"] = computed["discount_rate"]
        financial_data["scenarios"] = computed["scenarios"]
        financial_data.setdefault("revenue_projections", computed["revenue_projections"])
        financial_data.setdefault("cost_projections", computed["cost_projections"])
        financial_data.setdefault("capex", computed["capex"])
        existing_warnings = financial_data.get("warnings") or []
        if isinstance(existing_warnings, str):
            existing_warnings = [existing_warnings]
        financial_data["warnings"] = list(dict.fromkeys([*trust_warnings, *existing_warnings]))
        financial_data["extract_notes"] = extract_notes
        financial_data["analysis_complete"] = True
        state.financial_results = financial_data
    else:
        computed["analysis_complete"] = True
        state.financial_results = computed

    state.error = None
    state.phase = "ANALYZED"
    from ..utils.safe_messages import sanitize_chat_content

    public = sanitize_chat_content(response_text, language=lang) or _financial_chat_summary(
        state.financial_results or computed, lang
    )
    state.messages.append(AIMessage(content=public))
    state.next_action = "review_financials"
    return state


def _financial_chat_summary(computed: dict, lang: str) -> str:
    """User-safe financial summary — never interpolates raw null IRR/payback."""
    enriched = attach_financial_display_fields(computed or {}, language=lang)
    npv = enriched.get("npv")
    irr_text = enriched.get("irr_display") or irr_user_message(enriched.get("irr"), language=lang)
    payback_text = enriched.get("payback_display") or payback_user_message(
        enriched.get("payback_months"), language=lang
    )
    if lang == "ar":
        return (
            "اكتمل التحليل المالي. راجع لوحة النتائج للتفاصيل "
            f"(صافي القيمة الحالية: {npv}، معدل العائد الداخلي: {irr_text}، فترة الاسترداد: {payback_text})."
        )
    return (
        "Financial analysis complete. Review the results panel for details "
        f"(NPV: {npv}, IRR: {irr_text}, Payback: {payback_text})."
    )


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
