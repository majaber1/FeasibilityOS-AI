"""V2 study report builder — reuses reporting PDF generator with V2 state context."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from langchain_core.messages import AIMessage

from ..models.study_state import StudyState


def build_v2_report_context(state: StudyState, *, project_name: str = "") -> dict:
    """Build a structured report context from persisted study state (no invented facts)."""
    fr = state.financial_results or {}
    funding = (state.workflow_meta or {}).get("funding") or {}
    profile = state.profile
    evidence = [
        {
            "statement": c.statement,
            "source_title": c.source_title,
            "source_url": c.source_url,
            "source_type": c.source_type,
            "confidence": c.confidence,
            "status": c.status,
        }
        for c in (state.claims or [])
    ]
    assumptions = [
        {
            "key": a.key,
            "value": a.value,
            "origin": a.origin,
            "status": a.status,
            "low": a.low,
            "base": a.base,
            "high": a.high,
            "rationale": a.rationale,
        }
        for a in (state.assumptions or [])
    ]
    return {
        "title": project_name or f"Study {state.study_id}",
        "study_type": (profile.recommended_model if profile else None) or "v2_ai_study",
        "status": state.phase,
        "project_name": project_name or (profile.sector if profile else state.project_id),
        "industry": (profile.sector if profile else "") or "",
        "investment": fr.get("capex"),
        "archetype": profile.archetype if profile else "unknown",
        "sections": {
            "verified_evidence": evidence,
            "user_inputs": (profile.structured_answers if profile else {}) or {},
            "assumptions": assumptions,
            "platform_calculations": {
                k: fr.get(k)
                for k in ("npv", "irr", "payback_months", "capex", "revenue_projections", "cost_projections")
            },
            "financial_results": fr,
            "scenarios": fr.get("scenarios") or {},
            "risks": state.decision_risks or [],
            "decision": {
                "verdict": state.verdict,
                "rationale": state.decision_rationale,
                "conditions": state.decision_conditions or [],
                "confidence_note": "Derived from approved evidence + assumptions + deterministic finance",
            },
            "funding_readiness": funding,
            "next_actions": state.decision_conditions or [],
        },
        "result": SimpleNamespace(
            roi=fr.get("roi"),
            payback_years=(fr.get("payback_months") or 0) / 12.0 if fr.get("payback_months") else None,
            npv=fr.get("npv"),
            irr=(fr.get("irr") * 100 if isinstance(fr.get("irr"), (int, float)) and abs(fr.get("irr") or 0) <= 1 else fr.get("irr")),
            verdict=state.verdict,
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def run_report(state: StudyState) -> StudyState:
    """Persist report snapshot into workflow_meta (bytes generated on download endpoint)."""
    lang = state.language
    ctx = build_v2_report_context(state)
    state.workflow_meta = dict(state.workflow_meta or {})
    # Store JSON-serializable snapshot only (no bytes in DB).
    serializable = {
        "title": ctx["title"],
        "archetype": ctx["archetype"],
        "sections": {
            "verified_evidence_count": len(ctx["sections"]["verified_evidence"]),
            "assumptions_count": len(ctx["sections"]["assumptions"]),
            "decision": ctx["sections"]["decision"],
            "financial_results": {
                "status": (ctx["sections"]["financial_results"] or {}).get("status"),
                "npv": (ctx["sections"]["financial_results"] or {}).get("npv"),
                "irr": (ctx["sections"]["financial_results"] or {}).get("irr"),
                "payback_months": (ctx["sections"]["financial_results"] or {}).get("payback_months"),
                "missing_data": (ctx["sections"]["financial_results"] or {}).get("missing_data"),
            },
            "scenarios": ctx["sections"]["scenarios"],
            "risks": ctx["sections"]["risks"],
            "funding_readiness": {
                "score_percent": (ctx["sections"]["funding_readiness"] or {}).get("score_percent"),
                "blockers": (ctx["sections"]["funding_readiness"] or {}).get("blockers"),
            },
            "user_inputs": ctx["sections"]["user_inputs"],
        },
        "generated_at": ctx["generated_at"],
    }
    state.workflow_meta["report"] = serializable
    state.next_action = "download_report"
    msg = (
        "تم تجهيز ملخص التقرير من حالة الدراسة المحفوظة (أدلة / افتراضات / حسابات / قرار / تمويل)."
        if lang == "ar"
        else "Report summary prepared from persisted study state (evidence / assumptions / calculations / decision / funding)."
    )
    state.messages.append(AIMessage(content=msg))
    state.error = None
    return state
