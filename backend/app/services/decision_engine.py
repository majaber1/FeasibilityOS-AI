"""
Deterministic explainable decision engine (Phase 13).

Derives GO / CONDITIONAL_GO / NO_GO / INSUFFICIENT_EVIDENCE strictly from
already-computed data: the study's evidence count and its latest BASE/
CONSERVATIVE ScenarioRun snapshots (Phase 12). No AI, no arbitrary success
score -- every branch below is a documented, deterministic rule with an
explanation traceable back to the inputs that produced it. An AI Advisor
(a later phase) may narrate this decision; it must never override it.
"""
from __future__ import annotations

from typing import Optional

DECISION_STATES = ("GO", "CONDITIONAL_GO", "NO_GO", "INSUFFICIENT_EVIDENCE")

# Documented, configurable thresholds -- recalibrate here, not in the logic.
MIN_EVIDENCE_COUNT = 1
LOW_EVIDENCE_WARNING_THRESHOLD = 2


def evaluate_decision(
    *,
    evidence_count: int,
    base_scenario: Optional[dict],
    conservative_scenario: Optional[dict],
) -> dict:
    """base_scenario/conservative_scenario: {"id", "financial_result_snapshot", "source_assumption_values"} or None.

    financial_result_snapshot must contain "verdict" (feasible/borderline/
    not_feasible) and "npv", matching ScenarioRun.financial_result_snapshot.
    """
    if base_scenario is None:
        return {
            "decision": "INSUFFICIENT_EVIDENCE",
            "reason": "No base financial scenario has been computed for this study yet.",
            "conditions": ["Record capex and revenue_year1 assumptions and run a BASE scenario."],
            "key_drivers": [],
            "key_risks": ["No BASE scenario computed."],
        }

    if evidence_count < MIN_EVIDENCE_COUNT:
        return {
            "decision": "INSUFFICIENT_EVIDENCE",
            "reason": "A base financial scenario exists, but no supporting market evidence has been recorded.",
            "conditions": ["Add at least one Saudi evidence source before proceeding."],
            "key_drivers": [],
            "key_risks": ["No market evidence has been recorded for this study."],
        }

    key_drivers = [f"{key}={entry['value']}" for key, entry in base_scenario["source_assumption_values"].items()]
    key_risks = []
    if evidence_count < LOW_EVIDENCE_WARNING_THRESHOLD:
        key_risks.append(f"Only {evidence_count} evidence item(s) recorded; consider adding more before committing capital.")

    base_result = base_scenario["financial_result_snapshot"]
    base_verdict = base_result["verdict"]
    base_npv = base_result["npv"]

    if base_verdict == "not_feasible":
        return {
            "decision": "NO_GO",
            "reason": f"The base scenario shows a negative NPV ({base_npv:,.0f} SAR); the project is not feasible under current assumptions.",
            "conditions": [],
            "key_drivers": key_drivers,
            "key_risks": key_risks + [f"Base NPV is negative ({base_npv:,.0f} SAR)."],
        }

    conservative_result = conservative_scenario["financial_result_snapshot"] if conservative_scenario else None
    if conservative_result is not None and conservative_result["npv"] <= 0:
        return {
            "decision": "CONDITIONAL_GO",
            "reason": "The project appears viable under base assumptions, but is not resilient to the conservative scenario.",
            "conditions": [
                "Confirm the conservative scenario's assumptions are unlikely, or improve the underlying "
                "assumptions (cost, revenue, or capex) before committing capital."
            ],
            "key_drivers": key_drivers,
            "key_risks": key_risks + [f"The conservative scenario produces a non-positive NPV ({conservative_result['npv']:,.0f} SAR)."],
        }

    if base_verdict == "borderline":
        return {
            "decision": "CONDITIONAL_GO",
            "reason": "The base scenario is borderline: NPV/IRR is close to the discount-rate threshold.",
            "conditions": ["Improve base assumptions (revenue, cost, or capex) to move NPV/IRR clearly above threshold."],
            "key_drivers": key_drivers,
            "key_risks": key_risks,
        }

    if conservative_scenario is None:
        key_risks.append("No CONSERVATIVE scenario has been computed yet; this decision is based on the base scenario only.")

    return {
        "decision": "GO",
        "reason": "The base scenario is feasible" + (" and resilient to the conservative scenario." if conservative_scenario else "."),
        "conditions": [],
        "key_drivers": key_drivers,
        "key_risks": key_risks,
    }
