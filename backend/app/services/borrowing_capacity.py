"""
Deterministic borrowing capacity engine (Phase 15).

Estimates a *range* of additional borrowing capacity from a company's
recorded financial data (EBITDA, existing debt, annual debt service) --
never a single fake exact figure, and never an approval. Two binding
constraints are checked and the lower one wins:

  1. Debt service capacity: how much additional annual debt service the
     company's EBITDA can support at a target DSCR, converted to an
     indicative principal amount via a documented, configurable multiplier.
  2. Existing leverage: how much additional debt the company can carry
     before total debt/EBITDA exceeds a configured ceiling.

THRESHOLDS below are illustrative SME screening bands for this product --
NOT a specific lender's underwriting policy, interest rate, or loan term.
capacity_multiplier in particular is an indicative principal-per-SAR-of-
available-annual-debt-service ratio, not a computed amortization (which
would require assuming a specific rate/term this product has no verified
source for). Recalibrate by editing THRESHOLDS, not the logic below.

This estimates capacity from the EXISTING business's financial health only
(Journey B: an existing company seeking financing). Blending in the new
project's own projected cash flow (Phase 10/12) would require another
undocumented assumption about how lenders weight it, so it is intentionally
left out rather than fabricated -- see missing_underwriting_inputs.
"""
from __future__ import annotations

from typing import Optional

THRESHOLDS = {
    "target_dscr": 1.25,            # lenders typically require EBITDA / total debt service >= this
    "ebitda_stress_haircut": 0.85,  # stress case: EBITDA reduced by 15%
    "capacity_multiplier": 4.5,     # indicative principal capacity per SAR of available annual debt-service headroom
    "max_leverage_multiple": 4.0,   # total debt (existing + new) should not exceed this multiple of EBITDA
}

MISSING_UNDERWRITING_INPUTS = (
    "SIMAH / credit bureau report",
    "bank account conduct",
    "lender-specific risk assessment",
    "final collateral valuation",
)

REQUIRED_INPUTS = ("ebitda", "annual_debt_service")


def _capacity_for(ebitda_value: float, existing_debt: float, annual_debt_service: float) -> tuple[float, str]:
    max_total_debt_service = ebitda_value / THRESHOLDS["target_dscr"]
    headroom = max(max_total_debt_service - annual_debt_service, 0.0)
    capacity_from_dscr = headroom * THRESHOLDS["capacity_multiplier"]

    max_total_debt = ebitda_value * THRESHOLDS["max_leverage_multiple"]
    capacity_from_leverage = max(max_total_debt - existing_debt, 0.0)

    if capacity_from_leverage < capacity_from_dscr:
        return capacity_from_leverage, "existing_leverage"
    return capacity_from_dscr, "debt_service_capacity"


def estimate_borrowing_capacity(
    *, ebitda: Optional[float], existing_debt: Optional[float], annual_debt_service: Optional[float]
) -> dict:
    if ebitda is None or annual_debt_service is None:
        missing = [name for name, value in (("ebitda", ebitda), ("annual_debt_service", annual_debt_service)) if value is None]
        return {
            "status": "INSUFFICIENT_DATA",
            "base_capacity": None,
            "stress_capacity": None,
            "primary_constraint": None,
            "secondary_constraint": None,
            "financial_support": "INSUFFICIENT_DATA",
            "missing_inputs": missing,
            "missing_underwriting_inputs": list(MISSING_UNDERWRITING_INPUTS),
            "assumptions_used": THRESHOLDS,
        }

    # existing_debt absent is treated as 0 for the calculation (a company
    # with literally no recorded debt is a legitimate, common case) but is
    # still flagged in missing_inputs so "confirmed debt-free" isn't
    # confused with "debt figure not yet provided".
    missing_inputs = ["existing_debt"] if existing_debt is None else []
    resolved_existing_debt = existing_debt or 0.0

    base_capacity, base_constraint = _capacity_for(ebitda, resolved_existing_debt, annual_debt_service)
    stressed_ebitda = ebitda * THRESHOLDS["ebitda_stress_haircut"]
    stress_capacity, stress_constraint = _capacity_for(stressed_ebitda, resolved_existing_debt, annual_debt_service)

    if annual_debt_service:
        dscr = ebitda / annual_debt_service
        if dscr >= 1.5:
            financial_support = "STRONG"
        elif dscr >= 1.0:
            financial_support = "ACCEPTABLE"
        else:
            financial_support = "WEAK"
    else:
        financial_support = "INSUFFICIENT_DATA"

    return {
        "status": "CALCULATED",
        "base_capacity": round(base_capacity, 2),
        "stress_capacity": round(stress_capacity, 2),
        "primary_constraint": base_constraint,
        "secondary_constraint": stress_constraint if stress_constraint != base_constraint else None,
        "financial_support": financial_support,
        "missing_inputs": missing_inputs,
        "missing_underwriting_inputs": list(MISSING_UNDERWRITING_INPUTS),
        "assumptions_used": THRESHOLDS,
    }
