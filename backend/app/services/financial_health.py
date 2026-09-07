"""
Deterministic company financial health engine (Phase 11).

Computes ratios strictly from CompanyFinancialPeriod data already recorded
for a study (see app.api.company_financial_profile). No LLM involvement, no
invented values: a metric whose required input is absent is MISSING_DATA;
a metric whose inputs are present but whose denominator is mathematically
zero is NOT_APPLICABLE (undefined) -- never silently defaulted to zero or
divided by zero.

THRESHOLDS below are the documented, configurable classification boundaries
for the category-level summary. They are illustrative screening bands for
this product, not a specific lender's underwriting policy -- recalibrate by
editing THRESHOLDS, not the calculation logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

STATUS_CALCULATED = "CALCULATED"
STATUS_MISSING = "MISSING_DATA"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"

# For symmetric bands: {"strong": X, "acceptable": Y} means value >= X -> first
# label, >= Y -> second label, else third. For "lower is better" bands (e.g.
# leverage) the keys are {"low": X, "moderate": Y}: value <= X -> first label,
# <= Y -> second label, else third.
THRESHOLDS = {
    "net_margin": {"strong": 0.10, "acceptable": 0.0},
    "current_ratio": {"strong": 1.5, "acceptable": 1.0},
    "debt_to_ebitda": {"low": 2.0, "moderate": 4.0},
    "dscr": {"strong": 1.5, "acceptable": 1.0},
}

METRIC_KEYS = (
    "revenue_growth", "gross_margin", "ebitda_margin", "operating_margin", "net_margin",
    "working_capital", "current_ratio", "quick_ratio",
    "debt_to_equity", "debt_to_ebitda",
    "interest_coverage", "dscr",
)


@dataclass
class Metric:
    status: str
    value: Optional[float] = None
    unit: Optional[str] = None


def _ratio(numerator: Optional[float], denominator: Optional[float], unit: str = "ratio") -> Metric:
    if numerator is None or denominator is None:
        return Metric(status=STATUS_MISSING)
    if denominator == 0:
        return Metric(status=STATUS_NOT_APPLICABLE)
    return Metric(status=STATUS_CALCULATED, value=numerator / denominator, unit=unit)


def _margin(numerator: Optional[float], revenue: Optional[float]) -> Metric:
    return _ratio(numerator, revenue, unit="percent")


def compute_metrics(period: dict, prior_period: Optional[dict] = None) -> dict[str, Metric]:
    """period/prior_period: dicts keyed by CompanyFinancialPeriod metric field names."""
    metrics: dict[str, Metric] = {}

    # Growth (needs a prior period on record; a single period alone cannot
    # produce a growth rate, so this is MISSING_DATA, not zero growth).
    prior_revenue = prior_period.get("revenue") if prior_period else None
    if prior_revenue is None or period.get("revenue") is None:
        metrics["revenue_growth"] = Metric(status=STATUS_MISSING)
    elif prior_revenue == 0:
        metrics["revenue_growth"] = Metric(status=STATUS_NOT_APPLICABLE)
    else:
        metrics["revenue_growth"] = Metric(
            status=STATUS_CALCULATED, value=(period["revenue"] - prior_revenue) / prior_revenue, unit="percent"
        )

    # Profitability
    revenue = period.get("revenue")
    metrics["gross_margin"] = _margin(period.get("gross_profit"), revenue)
    metrics["ebitda_margin"] = _margin(period.get("ebitda"), revenue)
    metrics["operating_margin"] = _margin(period.get("operating_profit"), revenue)
    metrics["net_margin"] = _margin(period.get("net_profit"), revenue)

    # Liquidity
    current_assets = period.get("current_assets")
    current_liabilities = period.get("current_liabilities")
    inventory = period.get("inventory")
    if current_assets is None or current_liabilities is None:
        metrics["working_capital"] = Metric(status=STATUS_MISSING)
    else:
        metrics["working_capital"] = Metric(status=STATUS_CALCULATED, value=current_assets - current_liabilities, unit="SAR")
    metrics["current_ratio"] = _ratio(current_assets, current_liabilities)
    if current_assets is None or inventory is None or current_liabilities is None:
        metrics["quick_ratio"] = Metric(status=STATUS_MISSING)
    elif current_liabilities == 0:
        metrics["quick_ratio"] = Metric(status=STATUS_NOT_APPLICABLE)
    else:
        metrics["quick_ratio"] = Metric(status=STATUS_CALCULATED, value=(current_assets - inventory) / current_liabilities, unit="ratio")

    # Leverage
    metrics["debt_to_equity"] = _ratio(period.get("existing_debt"), period.get("equity"))
    metrics["debt_to_ebitda"] = _ratio(period.get("existing_debt"), period.get("ebitda"))

    # Debt service. Interest Coverage = EBIT (operating_profit) / interest
    # expense. DSCR uses annual_debt_service (principal + interest), a
    # different figure -- the two must never be conflated.
    metrics["interest_coverage"] = _ratio(period.get("operating_profit"), period.get("interest_expense"))
    metrics["dscr"] = _ratio(period.get("ebitda"), period.get("annual_debt_service"))

    return metrics


def _bucket(metric: Metric, thresholds: dict, higher_is_better: bool, labels: tuple[str, str, str]) -> str:
    if metric.status != STATUS_CALCULATED or metric.value is None:
        return "INSUFFICIENT_DATA"
    first_label, second_label, third_label = labels
    first_key, second_key = ("strong", "acceptable") if "strong" in thresholds else ("low", "moderate")
    if higher_is_better:
        if metric.value >= thresholds[first_key]:
            return first_label
        if metric.value >= thresholds[second_key]:
            return second_label
        return third_label
    if metric.value <= thresholds[first_key]:
        return first_label
    if metric.value <= thresholds[second_key]:
        return second_label
    return third_label


def summarize(metrics: dict[str, Metric]) -> dict:
    profitability = _bucket(metrics["net_margin"], THRESHOLDS["net_margin"], True, ("STRONG", "ACCEPTABLE", "WEAK"))
    liquidity = _bucket(metrics["current_ratio"], THRESHOLDS["current_ratio"], True, ("STRONG", "ACCEPTABLE", "WEAK"))
    leverage = _bucket(metrics["debt_to_ebitda"], THRESHOLDS["debt_to_ebitda"], False, ("LOW", "MODERATE", "HIGH"))
    debt_service = _bucket(metrics["dscr"], THRESHOLDS["dscr"], True, ("STRONG", "ACCEPTABLE", "WEAK"))

    total = len(metrics)
    calculated = sum(1 for metric in metrics.values() if metric.status == STATUS_CALCULATED)
    if calculated == total:
        coverage = "FULL"
    elif calculated == 0:
        coverage = "MINIMAL"
    else:
        coverage = "PARTIAL"

    return {
        "profitability": profitability,
        "liquidity": liquidity,
        "leverage": leverage,
        "debt_service_capacity": debt_service,
        "data_coverage": coverage,
    }
