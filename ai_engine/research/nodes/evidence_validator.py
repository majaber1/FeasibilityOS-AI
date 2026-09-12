"""Evidence validator — enforces research-before-assumption trust rules."""

from __future__ import annotations

from typing import Any

from ai_engine.research.nodes.research import validate_research_before_assumption
from ai_engine.research.schemas import ResearchClaim, ResearchPlan, ResearchResult


def claims_have_official(claims: list[Any] | None) -> bool:
    for c in claims or []:
        if isinstance(c, dict):
            st = c.get("source_type")
        else:
            st = getattr(c, "source_type", None)
        if st == "official":
            return True
    return False


def run_evidence_validator(state: Any) -> Any:
    """
    Validate evidence pack after research (+ optional assumption).

    Failures are recorded in research_context; they do not crash the graph.
    """
    from ai_engine.models.study_state import StudyState

    is_model = isinstance(state, StudyState)
    ctx = (state.research_context if is_model else state.get("research_context")) or {}
    claims = state.claims if is_model else state.get("claims") or []
    research_status = (
        state.research_status if is_model else state.get("research_status")
    ) or (ctx.get("status") if isinstance(ctx, dict) else None)

    result = None
    if isinstance(ctx, dict) and ctx.get("status"):
        plan_raw = ctx.get("plan") or {}
        plan = ResearchPlan(
            study_id=str(
                plan_raw.get("study_id")
                or (state.study_id if is_model else state.get("study_id"))
                or "unknown"
            ),
            gaps=list(plan_raw.get("gaps") or []),
            sources=[],
            queries=list(plan_raw.get("queries") or []),
            status="planned",
        )
        r_claims: list[ResearchClaim] = []
        for c in ctx.get("claims") or []:
            if not isinstance(c, dict):
                continue
            r_claims.append(
                ResearchClaim(
                    statement=str(c.get("statement") or ""),
                    source_type=c.get("source_type") or "official",  # type: ignore[arg-type]
                    source_url=c.get("source_url"),
                    retrieved_date=c.get("retrieved_date"),
                    confidence=float(c.get("confidence") or 0.5),
                    source_key=c.get("source_key"),
                    from_knowledge=bool(c.get("from_knowledge")),
                )
            )
        result = ResearchResult(
            plan=plan,
            status=ctx.get("status") or "partial",  # type: ignore[arg-type]
            claims=r_claims,
            blocked_sources=list(ctx.get("blocked_sources") or []),
            unavailable_sources=list(ctx.get("unavailable_sources") or []),
        )

    gate = validate_research_before_assumption(result)
    violations: list[str] = []

    claim_dicts: list[dict[str, Any]] = []
    for c in claims:
        if hasattr(c, "model_dump"):
            claim_dicts.append(c.model_dump())
        elif isinstance(c, dict):
            claim_dicts.append(c)

    if gate["official_claim_count"] > 0 and not claims_have_official(claim_dicts):
        violations.append("official_research_claims_missing_from_evidence")

    has_assumption = any(
        str(c.get("source_type") or "") == "ai_assumption" for c in claim_dicts
    )
    if has_assumption and not gate["research_ran"]:
        violations.append("ai_assumption_without_prior_research")

    ok = len(violations) == 0
    validation = {
        "ok": ok,
        "violations": violations,
        "gate": gate,
        "research_status": research_status,
    }
    new_ctx = {**(ctx if isinstance(ctx, dict) else {}), "evidence_validation": validation}

    if is_model:
        state.research_context = new_ctx
        return state
    return {"research_context": new_ctx}
