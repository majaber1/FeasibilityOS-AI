"""
FeasibilityOS AI - Financial Engine
Core financial feasibility calculations: ROI, Payback, NPV, IRR,
Break-even, and simple sensitivity analysis.

Pure Python (no external numerical dependency) so it runs anywhere
the backend runs, including serverless environments.
"""

from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Basic metrics
# ---------------------------------------------------------------------------

def roi(profit: float, investment: float) -> float:
    """Return on Investment, as a percentage."""
    if investment == 0:
        raise ValueError("investment must be non-zero")
    return (profit / investment) * 100


def payback_period(investment: float, annual_profit: float) -> float:
    """Simple payback period in years. Assumes constant annual profit."""
    if annual_profit <= 0:
        raise ValueError("annual_profit must be positive")
    return investment / annual_profit


def break_even_units(fixed_costs: float, price_per_unit: float, variable_cost_per_unit: float) -> float:
    """Units that must be sold to cover fixed costs."""
    contribution_margin = price_per_unit - variable_cost_per_unit
    if contribution_margin <= 0:
        raise ValueError("price_per_unit must exceed variable_cost_per_unit")
    return fixed_costs / contribution_margin


# ---------------------------------------------------------------------------
# Discounted cash flow metrics
# ---------------------------------------------------------------------------

def npv(discount_rate: float, cash_flows: List[float]) -> float:
    """
    Net Present Value.
    cash_flows[0] is the initial investment (typically negative),
    cash_flows[1:] are the projected period cash flows.
    """
    return sum(cf / ((1 + discount_rate) ** t) for t, cf in enumerate(cash_flows))


def irr(cash_flows: List[float], guess: float = 0.1, tol: float = 1e-6, max_iter: int = 1000) -> Optional[float]:
    """
    Internal Rate of Return via Newton-Raphson with a bisection fallback.
    Returns None if it fails to converge (e.g. no sign change in cash flows).
    """
    if not any(cf < 0 for cf in cash_flows) or not any(cf > 0 for cf in cash_flows):
        return None  # IRR undefined without both an outflow and an inflow

    rate = guess
    for _ in range(max_iter):
        value = npv(rate, cash_flows)
        derivative = sum(-t * cf / ((1 + rate) ** (t + 1)) for t, cf in enumerate(cash_flows))
        if derivative == 0:
            break
        new_rate = rate - value / derivative
        if abs(new_rate - rate) < tol:
            return new_rate
        rate = new_rate

    # Fallback: bisection search over an expandable rate range (high-IRR projects).
    low, high = -0.99, 10.0
    f_low, f_high = npv(low, cash_flows), npv(high, cash_flows)
    expand = 0
    while f_low * f_high > 0 and high < 1000.0 and expand < 8:
        high *= 2.0
        f_high = npv(high, cash_flows)
        expand += 1
    if f_low * f_high > 0:
        return None
    for _ in range(200):
        mid = (low + high) / 2
        f_mid = npv(mid, cash_flows)
        if abs(f_mid) < tol:
            return mid
        if f_low * f_mid < 0:
            high = mid
        else:
            low, f_low = mid, f_mid
    return (low + high) / 2


# ---------------------------------------------------------------------------
# Aggregate feasibility result
# ---------------------------------------------------------------------------

@dataclass
class FeasibilityResult:
    investment: float
    cash_flows: List[float]
    discount_rate: float
    roi_percent: Optional[float] = None
    payback_years: Optional[float] = None
    npv_value: Optional[float] = None
    irr_value: Optional[float] = None
    verdict: str = field(default="")

    def evaluate(self):
        annual_profit = self.cash_flows[1] if len(self.cash_flows) > 1 else 0
        self.roi_percent = roi(sum(self.cash_flows[1:]), self.investment) if self.investment else None
        try:
            self.payback_years = payback_period(self.investment, annual_profit)
        except ValueError:
            self.payback_years = None
        self.npv_value = npv(self.discount_rate, [-self.investment] + self.cash_flows[1:])
        self.irr_value = irr([-self.investment] + self.cash_flows[1:])

        if self.npv_value is not None and self.npv_value > 0 and (self.irr_value or 0) > self.discount_rate:
            self.verdict = "feasible"
        elif self.npv_value is not None and self.npv_value < 0:
            self.verdict = "not_feasible"
        else:
            self.verdict = "borderline"
        return self


def evaluate_feasibility(investment: float, annual_cash_flows: List[float], discount_rate: float = 0.10) -> FeasibilityResult:
    """Convenience entry point used by the API layer."""
    result = FeasibilityResult(
        investment=investment,
        cash_flows=[-investment] + annual_cash_flows,
        discount_rate=discount_rate,
    )
    return result.evaluate()


def sensitivity_analysis(investment: float, annual_cash_flows: List[float], discount_rate: float, deltas: List[float] = None) -> List[dict]:
    """
    Re-run NPV/IRR across a range of revenue deltas (e.g. -20%, -10%, 0%, +10%, +20%)
    to show how sensitive the feasibility verdict is to demand/revenue shocks.
    """
    deltas = deltas if deltas is not None else [-0.20, -0.10, 0.0, 0.10, 0.20]
    results = []
    for delta in deltas:
        adjusted_flows = [cf * (1 + delta) for cf in annual_cash_flows]
        r = evaluate_feasibility(investment, adjusted_flows, discount_rate)
        results.append({
            "revenue_change_percent": delta * 100,
            "npv": round(r.npv_value, 2) if r.npv_value is not None else None,
            "irr_percent": round(r.irr_value * 100, 2) if r.irr_value is not None else None,
            "verdict": r.verdict,
        })
    return results
