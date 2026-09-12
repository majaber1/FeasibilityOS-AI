"""LangGraph research node — runs before evidence / AI assumption."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage

from ai_engine.models.study_state import Claim, StudyState
from ai_engine.research.planner import extract_gaps_from_state
from ai_engine.research.schemas import ResearchClaim, ResearchResult
from ai_engine.research.service import research_gaps

logger = logging.getLogger(__name__)


def merge_evidence_claims(
    existing: list[Any] | None,
    research_claims: list[ResearchClaim],
) -> list[Claim]:
    """
    Trust gate: official research claims win over ai_assumption.

    - Keep non-assumption existing claims
    - Append official (and document) research claims
    - Drop prior ai_assumption claims when research produced official claims
    """
    existing_list = list(existing or [])
    research_official = [
        c for c in research_claims if c.source_type in {"official", "document"}
    ]
    research_dicts = [c.to_claim_dict() for c in research_official]

    kept: list[Claim] = []
    drop_assumptions = bool(research_dicts)

    for claim in existing_list:
        if isinstance(claim, Claim):
            st = claim.source_type
            data = claim.model_dump()
        elif isinstance(claim, dict):
            st = str(claim.get("source_type") or "")
            data = claim
        else:
            continue
        if drop_assumptions and st == "ai_assumption":
            continue
        kept.append(
            Claim(
                statement=str(data.get("statement") or ""),
                source_type=data.get("source_type") or "unverified",  # type: ignore[arg-type]
                source_url=data.get("source_url"),
                retrieved_date=data.get("retrieved_date"),
                confidence=float(data.get("confidence") or 0.0),
                origin=data.get("origin"),
                document_id=data.get("document_id"),
                chunk_id=data.get("chunk_id"),
                source_key=data.get("source_key"),
            )
        )

    seen = {c.statement for c in kept}
    for rc in research_dicts:
        stmt = str(rc.get("statement") or "")
        if stmt and stmt not in seen:
            kept.append(
                Claim(
                    statement=stmt,
                    source_type=rc.get("source_type") or "official",  # type: ignore[arg-type]
                    source_url=rc.get("source_url"),
                    retrieved_date=rc.get("retrieved_date"),
                    confidence=float(rc.get("confidence") or 0.7),
                    origin=rc.get("origin") or "research",
                    document_id=rc.get("document_id"),
                    chunk_id=rc.get("chunk_id"),
                    source_key=rc.get("source_key"),
                )
            )
            seen.add(stmt)
    return kept


def validate_research_before_assumption(
    result: ResearchResult | None,
) -> dict[str, Any]:
    """Gate decision for AI assumption generation."""
    if result is None:
        return {
            "research_ran": False,
            "allow_ai_assumption": False,
            "reason": "research_not_run",
            "official_claim_count": 0,
        }
    official = [c for c in result.claims if c.source_type == "official"]
    return {
        "research_ran": True,
        "allow_ai_assumption": True,
        "reason": "research_completed",
        "official_claim_count": len(official),
        "research_status": result.status,
        "blocked_sources": list(result.blocked_sources),
        "unavailable_sources": list(result.unavailable_sources),
    }


def _open_db():
    try:
        from app.db import DB_ENABLED, SessionLocal  # type: ignore

        if not DB_ENABLED:
            return None
        return SessionLocal()
    except Exception:
        try:
            from backend.app.db import DB_ENABLED, SessionLocal

            if not DB_ENABLED:
                return None
            return SessionLocal()
        except Exception:
            return None


def run_research(state: StudyState) -> StudyState:
    """
    LangGraph node: Study Gap → Research Planner → Knowledge/MCP → claims.

    Never raises into Financial/Risk/Decision. Monsha'at blocked does not fail study.
    """
    study_id = str(state.study_id or "unknown")
    gaps = extract_gaps_from_state(state)
    owner_raw = state.user_id
    try:
        owner_id = int(owner_raw) if owner_raw is not None else None
    except (TypeError, ValueError):
        owner_id = None

    db = _open_db()
    try:
        result = research_gaps(
            study_id=study_id,
            gaps=gaps,
            owner_id=owner_id,
            db=db,
            knowledge_context=state.knowledge_context,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("research node failed: %s", exc)
        state.research_status = "failed"
        state.research_context = {"error": str(exc), "gaps": gaps}
        state.research_attempts = [{"outcome": "error", "error": str(exc)}]
        state.messages.append(
            AIMessage(
                content=f"Research step encountered an error (study continues): {exc}"
            )
        )
        state.error = None
        return state
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:  # noqa: BLE001
                pass

    state.claims = merge_evidence_claims(state.claims, result.claims)
    state.research_status = result.status
    state.research_context = result.to_public_dict()
    state.research_attempts = list(result.attempts)
    state.phase = "EVIDENCE_REVIEW"
    state.error = None
    state.messages.append(
        AIMessage(
            content=(
                f"Research {result.status}: {len(result.claims)} claim(s); "
                f"blocked={result.blocked_sources or []}; "
                f"unavailable={result.unavailable_sources or []}."
            )
        )
    )
    return state
