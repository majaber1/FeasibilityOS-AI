"""Scenario challenge recalculation — deterministic, no LLM arithmetic."""
from __future__ import annotations

from langchain_core.messages import AIMessage

from .financial_analyst import _compute_scenario, _extract_financials_from_assumptions
from ..models.study_state import StudyState


def apply_scenario_challenge(state: StudyState, challenge: dict) -> StudyState:
    """
    Apply user challenges then recalculate BASE/UPSIDE/DOWNSIDE.

    challenge keys (optional):
      revenue_multiplier: float (e.g. 0.7 for -30% customers)
      cost_multiplier: float (e.g. 1.15 for +15% construction)
      delay_months: float (affects payback display only)
      occupancy: float 0-1 (real estate utilization)
      note: str
    """
    lang = state.language
    extracted = _extract_financials_from_assumptions(state)
    fr = dict(state.financial_results or {})

    if not extracted or not extracted.get("annual_revenues"):
        fr["status"] = "MODEL_INCOMPLETE"
        fr["reason"] = "INSUFFICIENT_DATA"
        fr["missing_data"] = fr.get("missing_data") or ["annual_revenues"]
        state.financial_results = fr
        state.next_action = "complete_financial_inputs"
        return state

    rev_m = float(challenge.get("revenue_multiplier") or 1.0)
    cost_m = float(challenge.get("cost_multiplier") or 1.0)
    occ = challenge.get("occupancy")
    if occ is not None:
        rev_m *= float(occ)

    capex = float(extracted.get("capex") or 0)
    revenues = [float(r or 0) * rev_m for r in (extracted.get("annual_revenues") or [0, 0, 0])[:3]]
    costs = [float(c or 0) * cost_m for c in (extracted.get("annual_costs") or [0, 0, 0])[:3]]
    while len(revenues) < 3:
        revenues.append(revenues[-1] if revenues else 0)
    while len(costs) < 3:
        costs.append(costs[-1] if costs else 0)
    discount = float(extracted.get("discount_rate") or 0.12)
    if discount > 1:
        discount = discount / 100.0

    base = _compute_scenario(capex, revenues, costs, discount, 1.0)
    upside = _compute_scenario(capex, revenues, costs, discount, 1.2)
    downside = _compute_scenario(capex, revenues, costs, discount, 0.8)

    delay = float(challenge.get("delay_months") or 0)
    if delay and base.get("payback_months") is not None:
        base["payback_months"] = round(float(base["payback_months"]) + delay, 1)

    scenarios = {
        "BASE": base,
        "UPSIDE": upside,
        "DOWNSIDE": downside,
        # keep legacy keys for existing UI
        "base": base,
        "optimistic": upside,
        "conservative": downside,
    }
    fr.update(
        {
            "status": "OK",
            "analysis_complete": True,
            "capex": capex,
            "revenue_projections": {"year_1": revenues[0], "year_2": revenues[1], "year_3": revenues[2]},
            "cost_projections": {"year_1": costs[0], "year_2": costs[1], "year_3": costs[2]},
            "npv": base["npv"],
            "irr": base["irr"],
            "payback_months": base["payback_months"],
            "scenarios": scenarios,
            "last_challenge": {
                "revenue_multiplier": rev_m,
                "cost_multiplier": cost_m,
                "delay_months": delay,
                "occupancy": occ,
                "note": challenge.get("note"),
            },
        }
    )
    state.financial_results = fr
    state.workflow_meta = dict(state.workflow_meta or {})
    hist = list(state.workflow_meta.get("scenario_challenges") or [])
    hist.append(fr["last_challenge"])
    state.workflow_meta["scenario_challenges"] = hist[-20:]

    note = challenge.get("note") or ""
    msg = (
        f"تم إعادة حساب السيناريوهات بعد التحدي. NPV الأساس={base['npv']}. {note}".strip()
        if lang == "ar"
        else f"Scenarios recalculated after challenge. Base NPV={base['npv']}. {note}".strip()
    )
    state.messages.append(AIMessage(content=msg))
    state.next_action = "review_scenarios"
    state.error = None
    return state
