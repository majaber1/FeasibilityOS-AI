"""
Deterministic cash-flow projection derived from a study's recorded
assumptions. No AI, no invented numbers -- pure functions over whatever the
study's active StudyAssumption rows actually contain.

Recognizes a small set of canonical assumption keys mirroring the
feasibility model's known inputs (capex, revenue_year1, opex_annual,
growth_rate, discount_rate, horizon_years). A study must have at least
capex and revenue_year1 recorded as active assumptions before a projection
can be computed; nothing here estimates a value the study doesn't have.
Same assumption values always produce the same projection (see
app.api.feasibility: compute-from-assumptions persists which assumption
versions produced a given result, so it stays reproducible).
"""
from __future__ import annotations

from typing import Optional

# Bumped whenever the projection formula changes, so a scenario snapshot
# computed under an older version is never silently reinterpreted as if it
# came from the current logic (see app.api.scenarios).
CALCULATION_VERSION = "financial_projection.v1"

REQUIRED_ASSUMPTION_KEYS = ("capex", "revenue_year1")
OPTIONAL_ASSUMPTION_DEFAULTS: dict[str, float] = {
    "opex_annual": 0.0,
    "growth_rate": 0.0,
    "discount_rate": 0.10,
    "horizon_years": 5,
}
ALL_ASSUMPTION_KEYS = REQUIRED_ASSUMPTION_KEYS + tuple(OPTIONAL_ASSUMPTION_DEFAULTS)


def missing_required_keys(values: dict[str, Optional[float]]) -> list[str]:
    return [key for key in REQUIRED_ASSUMPTION_KEYS if values.get(key) is None]


def project_cash_flows(values: dict[str, Optional[float]]) -> tuple[float, list[float], float]:
    """Return (investment, annual_cash_flows, discount_rate).

    Revenue grows at growth_rate year over year from revenue_year1;
    opex_annual is held flat across the horizon -- the simplest defensible
    model. Anything more sophisticated (staffing ramps, seasonality, working
    capital) belongs to a later, explicitly-scoped phase, not invented here.
    """
    missing = missing_required_keys(values)
    if missing:
        raise ValueError(f"Missing required assumptions: {', '.join(missing)}")

    capex = float(values["capex"])
    revenue_year1 = float(values["revenue_year1"])
    opex_annual = float(values.get("opex_annual") if values.get("opex_annual") is not None else OPTIONAL_ASSUMPTION_DEFAULTS["opex_annual"])
    growth_rate = float(values.get("growth_rate") if values.get("growth_rate") is not None else OPTIONAL_ASSUMPTION_DEFAULTS["growth_rate"])
    discount_rate = float(values.get("discount_rate") if values.get("discount_rate") is not None else OPTIONAL_ASSUMPTION_DEFAULTS["discount_rate"])
    horizon_years = int(values.get("horizon_years") if values.get("horizon_years") is not None else OPTIONAL_ASSUMPTION_DEFAULTS["horizon_years"])
    if horizon_years < 1:
        raise ValueError("horizon_years must be at least 1")

    cash_flows = [revenue_year1 * ((1 + growth_rate) ** (year - 1)) - opex_annual for year in range(1, horizon_years + 1)]
    return capex, cash_flows, discount_rate
