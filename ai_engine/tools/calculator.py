from __future__ import annotations

from typing import List


def calculate_npv(cash_flows: List[float], discount_rate: float = 0.12) -> float:
    npv = 0.0
    for t, cf in enumerate(cash_flows):
        npv += cf / ((1 + discount_rate) ** t)
    return round(npv, 2)


def calculate_irr(cash_flows: List[float], tolerance: float = 0.0001, max_iter: int = 1000) -> float | None:
    if not cash_flows or len(cash_flows) < 2:
        return None

    low, high = -0.99, 10.0
    for _ in range(max_iter):
        mid = (low + high) / 2
        npv = sum(cf / ((1 + mid) ** t) for t, cf in enumerate(cash_flows))
        if abs(npv) < tolerance:
            return round(mid, 4)
        if npv > 0:
            low = mid
        else:
            high = mid
    return None


def calculate_payback_period(initial_investment: float, annual_cash_flows: List[float]) -> float | None:
    if not annual_cash_flows or initial_investment <= 0:
        return None

    cumulative = -initial_investment
    for year, cf in enumerate(annual_cash_flows, 1):
        cumulative += cf
        if cumulative >= 0:
            prev_cumulative = cumulative - cf
            fraction = (-prev_cumulative) / cf if cf > 0 else 0
            return round(year - 1 + fraction, 2)
    return None


def calculate_breakeven(fixed_costs: float, price_per_unit: float, variable_cost_per_unit: float) -> float | None:
    contribution_margin = price_per_unit - variable_cost_per_unit
    if contribution_margin <= 0:
        return None
    return round(fixed_costs / contribution_margin, 0)
