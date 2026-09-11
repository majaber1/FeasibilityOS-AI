"""Build a persisted feasibility report body from study state (not outline-only)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..models.study_state import StudyState

# Mean claim confidence below this forces INSUFFICIENT_EVIDENCE over investment verdicts.
EVIDENCE_CONFIDENCE_THRESHOLD = 0.60
MIN_CLAIMS_FOR_INVESTMENT_VERDICT = 3


def mean_evidence_confidence(state: StudyState) -> float | None:
    claims = state.claims or []
    if not claims:
        return None
    vals = []
    for c in claims:
        try:
            vals.append(float(getattr(c, "confidence", 0) or 0))
        except (TypeError, ValueError):
            vals.append(0.0)
    return sum(vals) / len(vals) if vals else None


def evidence_below_threshold(state: StudyState) -> bool:
    """True when evidence is too weak for a firm investment verdict."""
    claims = state.claims or []
    if len(claims) < MIN_CLAIMS_FOR_INVESTMENT_VERDICT:
        return True
    mean = mean_evidence_confidence(state)
    if mean is None:
        return True
    return mean < EVIDENCE_CONFIDENCE_THRESHOLD


def apply_evidence_verdict_override(state: StudyState) -> StudyState:
    """Insufficient evidence overrides GO/NO_GO/DEFER when confidence is below threshold."""
    if not evidence_below_threshold(state):
        return state
    prior = state.verdict
    if prior in {None, "INSUFFICIENT_EVIDENCE"}:
        state.verdict = "INSUFFICIENT_EVIDENCE"
        return state
    if prior in {"GO", "GO_WITH_CONDITIONS", "DEFER", "NO_GO"}:
        mean = mean_evidence_confidence(state)
        note = (
            f"Evidence-confidence override: mean claim confidence "
            f"{mean if mean is not None else 0:.2f} is below threshold "
            f"{EVIDENCE_CONFIDENCE_THRESHOLD:.2f} (or fewer than "
            f"{MIN_CLAIMS_FOR_INVESTMENT_VERDICT} claims). "
            f"Prior verdict `{prior}` replaced with INSUFFICIENT_EVIDENCE."
        )
        state.verdict = "INSUFFICIENT_EVIDENCE"
        base = (state.decision_rationale or "").strip()
        state.decision_rationale = f"{base}\n\n{note}".strip() if base else note
    return state


def _recommendation_for(verdict: str | None) -> str:
    mapping = {
        "GO": "Proceed with investment subject to normal diligence.",
        "GO_WITH_CONDITIONS": "Proceed only after stated conditions are met and re-checked.",
        "DEFER": "Defer the investment decision until material gaps are closed.",
        "NO_GO": "Do not proceed with the investment under current assumptions and evidence.",
        "INSUFFICIENT_EVIDENCE": (
            "Do not issue a firm investment verdict yet — gather higher-confidence evidence "
            "and re-run analysis."
        ),
    }
    return mapping.get(verdict or "INSUFFICIENT_EVIDENCE", mapping["INSUFFICIENT_EVIDENCE"])


def build_report(state: StudyState, *, funding_package: dict | None = None) -> dict[str, Any]:
    """Material report with required REPORT_READY sections (persisted body, not outline-only)."""
    profile = state.profile
    fr = dict(state.financial_results or {})
    funding_package = funding_package or fr.get("funding_package") or {}
    history = list(getattr(state, "assumptions_history", None) or [])
    financial_change = fr.get("financial_change") if isinstance(fr.get("financial_change"), dict) else {}

    evidence = [
        {
            "statement": c.statement,
            "source_type": c.source_type,
            "confidence": c.confidence,
            "source_url": c.source_url,
        }
        for c in (state.claims or [])
    ]
    assumptions = [
        {
            "key": a.key,
            "value": a.value,
            "source": a.source,
            "confidence": a.confidence,
            "low": a.low,
            "base": a.base,
            "high": a.high,
        }
        for a in (state.assumptions or [])
    ]
    financial_metrics = {
        "npv": fr.get("npv"),
        "irr": fr.get("irr"),
        "payback_months": fr.get("payback_months"),
        "breakeven_months": fr.get("breakeven_months"),
        "capex": fr.get("capex"),
        "analysis_complete": fr.get("analysis_complete"),
        "scenarios": fr.get("scenarios") or fr.get("scenario_table") or {},
        "revenue_projections": fr.get("revenue_projections"),
        "cost_projections": fr.get("cost_projections"),
        "assumptions_version": int(getattr(state, "assumptions_version", 0) or 0),
        "previous_npv": financial_change.get("previous_npv"),
        "npv_delta": financial_change.get("npv_delta"),
        "change_explanation": financial_change.get("explanation"),
    }
    risks = list(state.decision_risks or [])
    mean_conf = mean_evidence_confidence(state)
    verdict = state.verdict
    recommendation = _recommendation_for(verdict)

    exec_bits = [
        f"Archetype: {(profile.archetype if profile else 'unknown')}.",
        f"Verdict: {verdict or 'pending'}.",
        f"NPV={financial_metrics.get('npv')}, IRR={financial_metrics.get('irr')}, "
        f"Payback={financial_metrics.get('payback_months')}m.",
        f"Evidence claims={len(evidence)} (mean confidence="
        f"{mean_conf if mean_conf is not None else 'n/a'}).",
        f"Assumptions version={getattr(state, 'assumptions_version', 0)}.",
        recommendation,
    ]

    sections = {
        "executive_summary": {
            "title": "Executive summary",
            "summary": " ".join(exec_bits),
            "items": exec_bits,
        },
        "evidence": {
            "title": "Evidence",
            "summary": f"{len(evidence)} claims; mean confidence={mean_conf if mean_conf is not None else 'n/a'}",
            "items": evidence,
        },
        "assumptions": {
            "title": "Assumptions",
            "summary": (
                f"{len(assumptions)} assumptions (version {getattr(state, 'assumptions_version', 0)}); "
                f"{len(history)} history snapshots"
            ),
            "items": assumptions,
            "history": history,
        },
        "financial_results": {
            "title": "Financial results",
            "summary": (
                f"NPV={financial_metrics.get('npv')}, IRR={financial_metrics.get('irr')}, "
                f"Payback={financial_metrics.get('payback_months')}m"
                + (
                    f"; ΔNPV={financial_metrics.get('npv_delta')}"
                    if financial_metrics.get("npv_delta") is not None
                    else ""
                )
            ),
            "metrics": financial_metrics,
            "items": (
                [financial_change["explanation"]]
                if financial_change.get("explanation")
                else []
            ),
        },
        # Keep calculations as an alias of financial_results for backward-compatible UI keys.
        "calculations": {
            "title": "Calculations",
            "summary": (
                f"NPV={financial_metrics.get('npv')}, IRR={financial_metrics.get('irr')}, "
                f"Payback={financial_metrics.get('payback_months')}m"
            ),
            "metrics": financial_metrics,
        },
        "risks": {
            "title": "Risks",
            "summary": f"{len(risks)} decision risks",
            "items": risks,
        },
        "decision_rationale": {
            "title": "Decision rationale",
            "verdict": verdict,
            "rationale": state.decision_rationale,
            "conditions": list(state.decision_conditions or []),
            "decision_version": getattr(state, "decision_version", 0),
        },
        "recommendation": {
            "title": "Recommendation",
            "summary": recommendation,
            "verdict": verdict,
            "items": [recommendation, *(state.decision_conditions or [])],
        },
    }

    return {
        "title": f"Feasibility Report — {(profile.archetype if profile else 'unknown')}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": "REPORT_READY",
        "archetype": profile.archetype if profile else "unknown",
        "verdict": verdict,
        "assumptions_version": int(getattr(state, "assumptions_version", 0) or 0),
        "decision_version": int(getattr(state, "decision_version", 0) or 0),
        "evidence_confidence_mean": mean_conf,
        "evidence_confidence_threshold": EVIDENCE_CONFIDENCE_THRESHOLD,
        "assumptions_history": history,
        "section_order": [
            "executive_summary",
            "evidence",
            "assumptions",
            "financial_results",
            "risks",
            "decision_rationale",
            "recommendation",
        ],
        "sections": sections,
        "funding_package": funding_package,
    }
