from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, UniqueConstraint, text
from sqlalchemy.orm import Session

from app.db import DB_ENABLED, SessionLocal, Base
from ..auth import get_current_user

router = APIRouter(prefix="/api/v2/studies", tags=["v2-studies"])


class StudyStateRow(Base):
    __tablename__ = "study_states_v2"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    study_id = Column(String(64), unique=True, nullable=False, index=True)
    project_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    language = Column(String(5), nullable=False, server_default="ar")
    phase = Column(String(32), nullable=False, server_default="DRAFT")
    phase_history = Column(JSON, nullable=False, server_default="[]")
    profile_json = Column(JSON, nullable=True)
    profile_confirmed = Column(Boolean, nullable=False, server_default=text("false"))
    gate_choice = Column(String(32), nullable=True)
    evidence_status = Column(String(32), nullable=False, server_default="not_started")
    workflow_meta_json = Column(JSON, nullable=False, server_default="{}")
    claims_json = Column(JSON, nullable=False, server_default="[]")
    evidence_approved = Column(Boolean, nullable=False, server_default=text("false"))
    assumptions_json = Column(JSON, nullable=False, server_default="[]")
    assumptions_approved = Column(Boolean, nullable=False, server_default=text("false"))
    financial_results_json = Column(JSON, nullable=True)
    verdict = Column(String(32), nullable=True)
    decision_rationale = Column(Text, nullable=True)
    decision_conditions = Column(JSON, nullable=False, server_default="[]")
    decision_risks = Column(JSON, nullable=False, server_default="[]")
    decision_version = Column(Integer, nullable=False, server_default=text("0"))
    messages_json = Column(JSON, nullable=False, server_default="[]")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class StudyVersionRow(Base):
    __tablename__ = "study_state_versions"
    __table_args__ = (
        UniqueConstraint("study_id", "version", name="uq_study_version"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    study_id = Column(String(64), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    phase = Column(String(32), nullable=False)
    snapshot_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


_fallback_studies: dict[str, dict] = {}


def _get_db_session() -> Session | None:
    if not DB_ENABLED or SessionLocal is None:
        return None
    return SessionLocal()


def _sanitize_state_dict(state_dict: dict) -> dict:
    """Enforce NO SOURCE → NOT EVIDENCE before persistence."""
    from ai_engine.models.study_state import (
        filter_evidence_claims,
        compute_evidence_status,
    )

    claims = filter_evidence_claims(state_dict.get("claims") or [])
    state_dict = dict(state_dict)
    state_dict["claims"] = [c.model_dump() for c in claims]
    provider_error = None
    if state_dict.get("blocking_reason") == "evidence_provider_unavailable":
        provider_error = state_dict.get("blocking_reason")
    state_dict["evidence_status"] = state_dict.get("evidence_status") or compute_evidence_status(
        claims, provider_error=provider_error
    )
    # Never leave ai_assumption residue in assumptions disguised as claims.
    assumptions = []
    for a in state_dict.get("assumptions") or []:
        item = a if isinstance(a, dict) else (a.model_dump() if hasattr(a, "model_dump") else {})
        if item.get("source_type") == "ai_assumption":
            # Defensive: convert legacy claim-shaped rows if any slipped in.
            assumptions.append(
                {
                    "key": item.get("statement", "legacy_estimate")[:80],
                    "value": item.get("statement", ""),
                    "source": "provisional_ai_estimate",
                    "confidence": "low",
                    "origin": "provisional_estimate",
                    "status": "draft",
                }
            )
        else:
            assumptions.append(item)
    state_dict["assumptions"] = assumptions
    return state_dict


def _load_study(study_id: str, user_id: str) -> dict | None:
    db = _get_db_session()
    if db is not None:
        try:
            row = db.query(StudyStateRow).filter_by(study_id=study_id, user_id=user_id).first()
            if row:
                return _row_to_dict(row)
        except Exception:
            pass
        finally:
            db.close()
    return _fallback_studies.get(study_id)


def _save_study(study_id: str, state_dict: dict, user_id: str):
    state_dict = _sanitize_state_dict(state_dict)
    # Persist structured discovery questions inside workflow_meta (no new column).
    meta = dict(state_dict.get("workflow_meta") or {})
    if state_dict.get("discovery_questions") is not None:
        meta["discovery_questions"] = state_dict.get("discovery_questions") or []
        state_dict["workflow_meta"] = meta
    now = datetime.now(timezone.utc).isoformat()
    db = _get_db_session()
    if db is not None:
        try:
            row = db.query(StudyStateRow).filter_by(study_id=study_id).first()
            fields = dict(
                language=state_dict.get("language", "ar"),
                phase=state_dict.get("phase", "DRAFT"),
                phase_history=state_dict.get("phase_history", []),
                profile_json=state_dict.get("profile"),
                profile_confirmed=state_dict.get("profile_confirmed", False),
                gate_choice=state_dict.get("gate_choice"),
                evidence_status=state_dict.get("evidence_status", "not_started"),
                workflow_meta_json=state_dict.get("workflow_meta") or {},
                claims_json=state_dict.get("claims", []),
                evidence_approved=state_dict.get("evidence_approved", False),
                assumptions_json=state_dict.get("assumptions", []),
                assumptions_approved=state_dict.get("assumptions_approved", False),
                financial_results_json=state_dict.get("financial_results"),
                verdict=state_dict.get("verdict"),
                decision_rationale=state_dict.get("decision_rationale"),
                decision_conditions=state_dict.get("decision_conditions", []),
                decision_risks=state_dict.get("decision_risks", []),
                decision_version=state_dict.get("decision_version", 0),
                messages_json=_serialize_messages(state_dict.get("messages", [])),
                error=state_dict.get("error"),
            )
            if row:
                for k, v in fields.items():
                    setattr(row, k, v)
                row.updated_at = datetime.now(timezone.utc)
            else:
                row = StudyStateRow(
                    study_id=study_id,
                    project_id=state_dict.get("project_id", ""),
                    user_id=user_id,
                    **fields,
                )
                db.add(row)

            last_ver = (
                db.query(StudyVersionRow)
                .filter_by(study_id=study_id)
                .order_by(StudyVersionRow.version.desc())
                .first()
            )
            version_num = (last_ver.version + 1) if last_ver else 1
            db.add(
                StudyVersionRow(
                    study_id=study_id,
                    version=version_num,
                    phase=state_dict.get("phase", "DRAFT"),
                    snapshot_json=state_dict,
                )
            )
            db.commit()
            return
        except Exception:
            db.rollback()
        finally:
            db.close()

    _fallback_studies[study_id] = {
        "state": state_dict,
        "user_id": user_id,
        "created_at": _fallback_studies.get(study_id, {}).get("created_at", now),
        "updated_at": now,
    }


def _serialize_messages(messages) -> list:
    result = []
    for msg in messages:
        if isinstance(msg, dict):
            result.append(msg)
        elif hasattr(msg, "type") and hasattr(msg, "content"):
            result.append({"type": msg.type, "content": msg.content})
        else:
            result.append({"type": "unknown", "content": str(msg)})
    return result


def _row_to_dict(row: StudyStateRow) -> dict:
    claims = row.claims_json or []
    from ai_engine.models.study_state import filter_evidence_claims

    clean_claims = [c.model_dump() for c in filter_evidence_claims(claims)]
    return {
        "state": {
            "study_id": row.study_id,
            "project_id": row.project_id,
            "user_id": row.user_id,
            "language": row.language,
            "phase": row.phase,
            "phase_history": row.phase_history or [],
            "profile": row.profile_json,
            "profile_confirmed": row.profile_confirmed,
            "gate_choice": getattr(row, "gate_choice", None),
            "evidence_status": getattr(row, "evidence_status", None) or "not_started",
            "workflow_meta": getattr(row, "workflow_meta_json", None) or {},
            "claims": clean_claims,
            "evidence_approved": row.evidence_approved,
            "assumptions": row.assumptions_json or [],
            "assumptions_approved": row.assumptions_approved,
            "financial_results": row.financial_results_json,
            "verdict": row.verdict,
            "decision_rationale": row.decision_rationale,
            "decision_conditions": row.decision_conditions or [],
            "decision_risks": row.decision_risks or [],
            "decision_version": row.decision_version,
            "messages": row.messages_json or [],
            "error": row.error,
        },
        "user_id": row.user_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _list_user_studies(user_id: str) -> list[dict]:
    db = _get_db_session()
    if db is not None:
        try:
            rows = (
                db.query(StudyStateRow)
                .filter_by(user_id=user_id)
                .order_by(StudyStateRow.updated_at.desc())
                .all()
            )
            return [
                {
                    "study_id": r.study_id,
                    "project_id": r.project_id,
                    "phase": r.phase,
                    "archetype": (r.profile_json or {}).get("archetype")
                    if isinstance(r.profile_json, dict)
                    else None,
                    "verdict": r.verdict,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in rows
            ]
        except Exception:
            pass
        finally:
            db.close()

    results = []
    for sid, record in _fallback_studies.items():
        if record["user_id"] == user_id:
            s = record["state"]
            results.append(
                {
                    "study_id": sid,
                    "project_id": s.get("project_id") or record.get("project_id"),
                    "phase": s.get("phase"),
                    "archetype": (s.get("profile") or {}).get("archetype")
                    if isinstance(s.get("profile"), dict)
                    else None,
                    "verdict": s.get("verdict"),
                    "created_at": record.get("created_at"),
                    "updated_at": record.get("updated_at"),
                }
            )
    return results


class StudyCreateRequest(BaseModel):
    project_id: str
    language: str = "ar"
    description: str = ""


class StudyMessageRequest(BaseModel):
    message: str
    language: Optional[str] = None


class StudyApprovalRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None


class InformationGateRequest(BaseModel):
    choice: str = Field(..., description="manual | research | provisional")


class ItemActionRequest(BaseModel):
    target: str = Field(..., description="claim | assumption")
    index: int
    action: str = Field(
        ...,
        description="edit|approve|reject|regenerate|ask_why|request_alternative",
    )
    value: Optional[str] = None
    note: Optional[str] = None


class AnswerQuestionsRequest(BaseModel):
    answers: list[dict] = Field(
        default_factory=list,
        description="[{id, value}] structured discovery answers",
    )


class ScenarioChallengeRequest(BaseModel):
    revenue_multiplier: Optional[float] = 1.0
    cost_multiplier: Optional[float] = 1.0
    delay_months: Optional[float] = 0
    occupancy: Optional[float] = None
    note: Optional[str] = None


async def _advance_pipeline(state, run_study_step, *, max_steps: int = 4):
    """Run orchestrator steps until a human gate or idle (no duplicate engines)."""
    for _ in range(max_steps):
        before = (
            state.phase,
            state.verdict,
            bool(state.financial_results),
            len(state.decision_risks or []),
        )
        try:
            state = await run_study_step(state)
        except Exception as e:
            state.error = f"AI service error: {e}"
            break
        if state.error:
            break
        # Stop once decision is presented for human review.
        if state.phase == "DECISION_READY" and state.verdict and state.next_action == "present_decision":
            break
        if state.phase == "FUNDING_READY" and (state.workflow_meta or {}).get("funding"):
            break
        after = (
            state.phase,
            state.verdict,
            bool(state.financial_results),
            len(state.decision_risks or []),
        )
        if after == before:
            break
    return state


def _normalize_profile_label(value: str | None, *, fallback: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned or cleaned.lower() in {"unknown", "n/a", "na", "none", "null", "-", "غير معروف"}:
        return fallback
    return cleaned


def _prepare_profile_gate(state, *, clear_missing: bool) -> list[str]:
    gaps: list[str] = []
    if state.profile:
        state.profile.stage = _normalize_profile_label(state.profile.stage, fallback="idea")
        state.profile.decision_goal = _normalize_profile_label(
            state.profile.decision_goal, fallback="feasibility"
        )
        gaps = list(state.profile.missing_information or [])
        if clear_missing:
            state.profile.missing_information = []
    return gaps


def _set_phase(state, nxt: str, *, actor: str | None = None, reason: str | None = None) -> None:
    from ai_engine.models.study_state import assert_legal_transition

    try:
        assert_legal_transition(state.phase, nxt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    prev = state.phase
    state.phase_history.append(f"{prev}->{nxt}")
    state.phase = nxt
    meta = dict(state.workflow_meta or {})
    transitions = list(meta.get("transitions") or [])
    transitions.append(
        {
            "from": prev,
            "to": nxt,
            "actor": actor or state.user_id,
            "at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
        }
    )
    meta["transitions"] = transitions[-50:]
    state.workflow_meta = meta


def _import_engine():
    try:
        from ai_engine.models.study_state import StudyState
        from ai_engine.orchestrator import run_study_step

        return StudyState, run_study_step
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="AI engine not available. Please install ai-engine dependencies.",
        )


def _state_from_record(record: dict):
    from ai_engine.models.study_state import StudyState, filter_evidence_claims

    state_data = dict(record["state"])
    msgs = state_data.pop("messages", []) or []
    # Drop illegal evidence before pydantic validation.
    state_data["claims"] = [
        c.model_dump() for c in filter_evidence_claims(state_data.get("claims") or [])
    ]
    # Legacy rows may lack new fields.
    state_data.setdefault("evidence_status", "not_started")
    state_data.setdefault("workflow_meta", {})
    meta = state_data.get("workflow_meta") or {}
    if not state_data.get("discovery_questions") and isinstance(meta, dict):
        state_data["discovery_questions"] = meta.get("discovery_questions") or []
    state = StudyState(**state_data)
    for m in msgs:
        if isinstance(m, dict):
            mtype = m.get("type", "human")
            content = m.get("content", "")
            if mtype == "ai":
                from langchain_core.messages import AIMessage

                state.messages.append(AIMessage(content=content))
            elif mtype == "system":
                from langchain_core.messages import SystemMessage

                state.messages.append(SystemMessage(content=content))
            else:
                from langchain_core.messages import HumanMessage

                state.messages.append(HumanMessage(content=content))
    return state


def _public_messages(raw_messages) -> list[dict]:
    out: list[dict] = []
    for msg in raw_messages or []:
        if isinstance(msg, dict):
            mtype = msg.get("type") or msg.get("role") or "human"
            content = msg.get("content", "")
        elif hasattr(msg, "type") and hasattr(msg, "content"):
            mtype = msg.type
            content = msg.content
        else:
            continue
        if not content:
            continue
        if mtype in ("ai", "assistant"):
            role = "assistant"
        elif mtype in ("system",):
            role = "system"
        else:
            role = "user"
        out.append({"role": role, "content": str(content)})
    return out


def _payload_from_state(
    study_id: str, state, *, response: str | None = None, record_meta: dict | None = None
) -> dict:
    from ai_engine.models.study_state import filter_evidence_claims, compute_evidence_status

    claims = filter_evidence_claims(state.claims or [])
    state.claims = claims
    state.evidence_status = compute_evidence_status(
        claims,
        provider_error=state.blocking_reason
        if state.blocking_reason == "evidence_provider_unavailable"
        else None,
    )
    claim_dicts = [c.model_dump() for c in claims]
    assumptions = [a.model_dump() if hasattr(a, "model_dump") else a for a in (state.assumptions or [])]
    profile = (
        state.profile.model_dump()
        if state.profile and hasattr(state.profile, "model_dump")
        else state.profile
    )
    payload = {
        "study_id": study_id,
        "project_id": state.project_id,
        "phase": state.phase,
        "profile": profile,
        "profile_confirmed": state.profile_confirmed,
        "gate_choice": state.gate_choice,
        "evidence_status": state.evidence_status,
        "claims": claim_dicts,
        "assumptions": assumptions,
        "claims_count": len(claim_dicts),
        "assumptions_count": len(assumptions),
        "financial_results": state.financial_results,
        "verdict": state.verdict,
        "decision_rationale": state.decision_rationale,
        "decision_conditions": state.decision_conditions or [],
        "decision_risks": state.decision_risks or [],
        "messages": _public_messages(state.messages),
        "next_action": state.next_action,
        "blocking_reason": state.blocking_reason,
        "error": state.error,
        "workflow_meta": state.workflow_meta or {},
        "discovery_questions": [
            q.model_dump() if hasattr(q, "model_dump") else q
            for q in (state.discovery_questions or [])
        ],
        "created_at": (record_meta or {}).get("created_at"),
        "updated_at": (record_meta or {}).get("updated_at"),
    }
    if response is not None:
        payload["response"] = response
    return payload


def _study_payload(study_id: str, record: dict, *, response: str | None = None) -> dict:
    state = _state_from_record(record)
    return _payload_from_state(study_id, state, response=response, record_meta=record)


@router.post("")
async def create_study(req: StudyCreateRequest, user=Depends(get_current_user)):
    StudyState, run_study_step = _import_engine()

    study_id = f"study_{uuid.uuid4().hex[:12]}"
    user_id = str(user.id)

    state = StudyState(
        study_id=study_id,
        project_id=req.project_id,
        user_id=user_id,
        language=req.language,
        phase="DRAFT",
    )

    if req.description:
        from langchain_core.messages import HumanMessage

        state.messages.append(HumanMessage(content=req.description))
        try:
            state = await run_study_step(state)
        except Exception as e:
            state.error = f"AI service error: {e}"

    _save_study(study_id, state.model_dump(), user_id)

    last_ai_message = None
    for msg in reversed(state.messages):
        if hasattr(msg, "type") and msg.type == "ai":
            last_ai_message = msg.content
            break

    return _payload_from_state(study_id, state, response=last_ai_message)


@router.get("/{study_id}")
async def get_study(study_id: str, user=Depends(get_current_user)):
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")
    return _study_payload(study_id, record)


@router.post("/{study_id}/message")
async def send_message(study_id: str, req: StudyMessageRequest, user=Depends(get_current_user)):
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")

    _, run_study_step = _import_engine()
    state = _state_from_record(record)
    if req.language:
        state.language = req.language

    from langchain_core.messages import HumanMessage

    state.messages.append(HumanMessage(content=req.message))
    state.error = None

    try:
        state = await run_study_step(state)
    except Exception as e:
        state.error = f"AI service error: {e}"

    _save_study(study_id, state.model_dump(), user_id)

    last_ai_message = None
    for msg in reversed(state.messages):
        if hasattr(msg, "type") and msg.type == "ai":
            last_ai_message = msg.content
            break

    return _payload_from_state(study_id, state, response=last_ai_message, record_meta=record)


@router.post("/{study_id}/answer-questions")
async def answer_questions(
    study_id: str,
    req: AnswerQuestionsRequest,
    user=Depends(get_current_user),
):
    """Persist structured discovery answers (not freeform chat Markdown)."""
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")

    state = _state_from_record(record)
    if state.phase not in {"NEEDS_INFORMATION", "UNDERSTANDING", "DRAFT"}:
        raise HTTPException(
            status_code=400,
            detail=f"answer-questions only allowed during discovery (now {state.phase})",
        )
    from ai_engine.agents.discovery import apply_structured_answers

    state = apply_structured_answers(state, req.answers or [])
    _save_study(study_id, state.model_dump(), user_id)
    return _payload_from_state(study_id, state, record_meta=record)


@router.post("/{study_id}/information-gate")
async def information_gate(
    study_id: str,
    req: InformationGateRequest,
    user=Depends(get_current_user),
):
    """Three explicit choices replacing ambiguous Confirm Profile."""
    choice = (req.choice or "").strip().lower()
    if choice not in {"manual", "research", "provisional"}:
        raise HTTPException(
            status_code=400,
            detail="choice must be one of: manual, research, provisional",
        )

    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")

    _, run_study_step = _import_engine()
    state = _state_from_record(record)

    if state.phase != "NEEDS_INFORMATION":
        raise HTTPException(
            status_code=400,
            detail=f"information-gate only allowed in NEEDS_INFORMATION (now {state.phase})",
        )

    from langchain_core.messages import AIMessage, HumanMessage

    lang = state.language
    state.gate_choice = choice  # type: ignore[assignment]
    state.workflow_meta = dict(state.workflow_meta or {})
    state.workflow_meta["gate_choice_at"] = datetime.now(timezone.utc).isoformat()
    state.error = None
    state.blocking_reason = None

    if choice == "manual":
        gaps = _prepare_profile_gate(state, clear_missing=False)
        state.profile_confirmed = False
        state.phase_history.append("gate_manual")
        note = (
            "حسناً. أكمل المعلومات الناقصة في المحادثة. سنبقى في مرحلة جمع المعلومات."
            if lang == "ar"
            else "Understood. Complete the missing information in chat. Staying in Gathering Info."
        )
        if gaps:
            note += "\n" + "\n".join(f"- {g}" for g in gaps)
        state.messages.append(AIMessage(content=note))
        state.next_action = "answer_questions"
        _save_study(study_id, state.model_dump(), user_id)
        return _payload_from_state(study_id, state, record_meta=record)

    if choice == "research":
        gaps = _prepare_profile_gate(state, clear_missing=True)
        state.profile_confirmed = True
        state.phase_history.append("gate_research")
        _set_phase(state, "EVIDENCE_REVIEW", actor=user_id, reason="gate_research")
        state.evidence_status = "not_started"
        instruct = (
            "Research available source-backed evidence only. "
            "Do not invent estimates as Evidence. If no sources, return empty claims."
            if lang == "en"
            else "ابحث عن أدلة مصدرية فقط. لا تخترع تقديرات كأدلة. إذا لم توجد مصادر أعد claims فارغة."
        )
        if gaps:
            instruct += "\nGaps previously listed (for context, not as Evidence):\n" + "\n".join(
                f"- {g}" for g in gaps
            )
        state.messages.append(
            AIMessage(
                content=(
                    "Research path selected. Evidence must be source-backed."
                    if lang == "en"
                    else "تم اختيار مسار البحث. الأدلة يجب أن تكون مدعومة بمصادر."
                )
            )
        )
        state.messages.append(HumanMessage(content=instruct))
        try:
            state = await run_study_step(state)
        except Exception as e:
            state.error = f"AI service error: {e}"
            state.claims = []
            state.evidence_status = "degraded"
        _save_study(study_id, state.model_dump(), user_id)
        return _payload_from_state(study_id, state, record_meta=record)

    # provisional
    gaps = _prepare_profile_gate(state, clear_missing=True)
    state.profile_confirmed = True
    state.phase_history.append("gate_provisional")
    state.workflow_meta["force_provisional_assumptions"] = True
    # Keep evidence empty — estimates are assumptions only.
    state.claims = []
    state.evidence_status = "empty"
    state.evidence_approved = False
    _set_phase(state, "ASSUMPTIONS_REVIEW", actor=user_id, reason="gate_provisional")
    note = (
        "Provisional study path selected. Estimates will be stored as Assumptions only "
        "(not Evidence)."
        if lang == "en"
        else "تم اختيار الدراسة التقديرية. ستُحفظ التقديرات كافتراضات فقط (وليست أدلة)."
    )
    state.messages.append(AIMessage(content=note))
    if gaps:
        state.messages.append(
            HumanMessage(
                content="Create provisional_estimate assumptions for:\n"
                + "\n".join(f"- {g}" for g in gaps)
            )
        )
    try:
        state = await run_study_step(state)
    except Exception as e:
        state.error = f"AI service error: {e}"
    # Hard guarantee: no claim pollution from provisional path.
    state.claims = []
    state.evidence_status = "empty"
    _save_study(study_id, state.model_dump(), user_id)
    return _payload_from_state(study_id, state, record_meta=record)


@router.post("/{study_id}/approve/{stage}")
async def approve_stage(
    study_id: str,
    stage: str,
    req: StudyApprovalRequest,
    user=Depends(get_current_user),
):
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")

    _, run_study_step = _import_engine()
    state = _state_from_record(record)

    if stage == "profile":
        raise HTTPException(
            status_code=400,
            detail=(
                "Confirm Profile was replaced by POST /information-gate with choice="
                "manual|research|provisional"
            ),
        )

    valid_stages = {
        "evidence": ("EVIDENCE_REVIEW", "evidence_approved"),
        "assumptions": ("ASSUMPTIONS_REVIEW", "assumptions_approved"),
        "decision": ("DECISION_READY", None),
    }
    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")

    expected_phase, flag_field = valid_stages[stage]
    if state.phase != expected_phase:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve '{stage}' in phase '{state.phase}'. Expected phase: '{expected_phase}'.",
        )

    if stage == "assumptions" and not state.assumptions:
        raise HTTPException(status_code=400, detail="No assumptions to confirm.")

    if stage == "assumptions" and req.approved:
        # Option A: bulk-approve eligible DRAFT critical/provisional assumptions.
        # Rejected items remain blockers and must be replaced/edited/regenerated.
        for a in state.assumptions:
            is_critical = bool(getattr(a, "critical", False)) or getattr(a, "origin", None) == "provisional_estimate"
            if is_critical and getattr(a, "status", "draft") == "draft":
                a.status = "approved"  # type: ignore[attr-defined]
        critical = [
            a for a in state.assumptions
            if getattr(a, "critical", False) or getattr(a, "origin", None) == "provisional_estimate"
        ]
        blocked = [a for a in critical if getattr(a, "status", "draft") != "approved"]
        if blocked:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot continue: {len(blocked)} critical assumption(s) are rejected. "
                    "Edit, regenerate, or replace them before approving."
                ),
            )

    if stage == "evidence" and not state.claims:
        raise HTTPException(
            status_code=400,
            detail="No source-backed evidence to approve. Use research again or provisional assumptions.",
        )

    if stage == "decision" and not req.approved:
        if req.feedback:
            from langchain_core.messages import HumanMessage

            state.messages.append(HumanMessage(content=req.feedback))
        _save_study(study_id, state.model_dump(), user_id)
        return _payload_from_state(study_id, state, record_meta=record) | {
            "message": "Decision feedback recorded."
        }

    if not req.approved:
        if req.feedback:
            from langchain_core.messages import HumanMessage

            state.messages.append(HumanMessage(content=req.feedback))
        _save_study(study_id, state.model_dump(), user_id)
        return _payload_from_state(study_id, state, record_meta=record) | {
            "message": "Feedback recorded. Continue the conversation."
        }

    if flag_field:
        setattr(state, flag_field, True)
    state.phase_history.append(f"{stage}_approved")

    if stage == "evidence":
        _set_phase(state, "ASSUMPTIONS_REVIEW", actor=user_id, reason="approve_evidence")
    elif stage == "assumptions":
        _set_phase(state, "READY_FOR_ANALYSIS", actor=user_id, reason="approve_assumptions")
    elif stage == "decision":
        if state.verdict in {None, "INSUFFICIENT_EVIDENCE", "NEED_MORE_VALIDATION"}:
            raise HTTPException(
                status_code=400,
                detail="Cannot proceed to funding while decision is incomplete or insufficient.",
            )
        _set_phase(state, "FUNDING_READY", actor=user_id, reason="approve_decision")

    try:
        if stage == "assumptions":
            # Financial → risk → decision without dead-ending after one node.
            state = await _advance_pipeline(state, run_study_step, max_steps=4)
        else:
            state = await run_study_step(state)
    except Exception as e:
        state.error = f"AI service error: {e}"

    _save_study(study_id, state.model_dump(), user_id)
    return _payload_from_state(study_id, state, record_meta=record)


@router.post("/{study_id}/item-action")
async def item_action(
    study_id: str,
    req: ItemActionRequest,
    user=Depends(get_current_user),
):
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")

    state = _state_from_record(record)
    target = req.target.lower()
    action = req.action.lower()
    if target not in {"claim", "assumption"}:
        raise HTTPException(status_code=400, detail="target must be claim or assumption")
    if action not in {
        "edit",
        "approve",
        "reject",
        "regenerate",
        "ask_why",
        "request_alternative",
    }:
        raise HTTPException(status_code=400, detail="unsupported action")

    from langchain_core.messages import AIMessage, HumanMessage

    items = state.claims if target == "claim" else state.assumptions
    if req.index < 0 or req.index >= len(items):
        raise HTTPException(status_code=400, detail="index out of range")

    item = items[req.index]

    if action == "edit":
        if not req.value:
            raise HTTPException(status_code=400, detail="value required for edit")
        if target == "claim":
            item.statement = req.value
        else:
            history = list(getattr(item, "previous_values", None) or [])
            history.append(
                {
                    "value": item.value,
                    "low": getattr(item, "low", None),
                    "base": getattr(item, "base", None),
                    "high": getattr(item, "high", None),
                    "status": getattr(item, "status", None),
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )
            item.previous_values = history[-50:]  # type: ignore[attr-defined]
            item.value = req.value
        item.status = "draft"
    elif action == "approve":
        item.status = "approved"
    elif action == "reject":
        item.status = "rejected"
    elif action == "ask_why":
        why = getattr(item, "rationale", None) or getattr(item, "source", None) or "No rationale stored."
        state.messages.append(AIMessage(content=f"Why ({target} #{req.index}): {why}"))
    elif action == "request_alternative":
        state.messages.append(
            HumanMessage(
                content=req.note
                or f"Please propose an alternative for {target} #{req.index}."
            )
        )
        state.next_action = "review_" + ("evidence" if target == "claim" else "assumptions")
    elif action == "regenerate":
        if target == "claim":
            raise HTTPException(
                status_code=400,
                detail="Regenerate is not allowed for Evidence without a research pass "
                "(would risk synthetic Evidence). Use information-gate choice=research.",
            )
        history = list(getattr(item, "previous_values", None) or [])
        history.append(
            {
                "value": item.value,
                "status": getattr(item, "status", None),
                "at": datetime.now(timezone.utc).isoformat(),
                "reason": "regenerate",
            }
        )
        item.previous_values = history[-50:]  # type: ignore[attr-defined]
        # Mark for provisional regenerate of a single assumption.
        item.status = "draft"
        item.origin = "provisional_estimate"  # type: ignore[attr-defined]
        item.rationale = (req.note or "User requested alternative provisional estimate.")
        item.value = f"[Needs regenerate] {item.value}"
        state.messages.append(
            AIMessage(
                content=f"Assumption #{req.index} marked for regenerate (still an Assumption, not Evidence)."
            )
        )

    if target == "claim":
        state.claims[req.index] = item
    else:
        state.assumptions[req.index] = item

    state.phase_history.append(f"item_action:{target}:{action}:{req.index}")
    _save_study(study_id, state.model_dump(), user_id)
    return _payload_from_state(study_id, state, record_meta=record)


@router.post("/{study_id}/scenario-challenge")
async def scenario_challenge(
    study_id: str,
    req: ScenarioChallengeRequest,
    user=Depends(get_current_user),
):
    """User challenge → deterministic recalculation of BASE/UPSIDE/DOWNSIDE."""
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")
    if record.get("phase") not in {
        "ANALYZED",
        "DECISION_READY",
        "FUNDING_READY",
        "READY_FOR_ANALYSIS",
    }:
        raise HTTPException(
            status_code=400,
            detail=f"scenario-challenge not allowed in phase {record.get('phase')}",
        )
    state = _state_from_record(record)
    from ai_engine.agents.scenarios import apply_scenario_challenge

    state = apply_scenario_challenge(
        state,
        {
            "revenue_multiplier": req.revenue_multiplier,
            "cost_multiplier": req.cost_multiplier,
            "delay_months": req.delay_months,
            "occupancy": req.occupancy,
            "note": req.note,
        },
    )
    # Material challenges should refresh decision if already decided.
    if state.phase in {"DECISION_READY", "FUNDING_READY"} and state.financial_results:
        _, run_study_step = _import_engine()
        state.phase = "DECISION_READY"
        state.verdict = None
        try:
            state = await run_study_step(state)
        except Exception as e:
            state.error = f"AI service error: {e}"
    _save_study(study_id, state.model_dump(), user_id)
    return _payload_from_state(study_id, state, record_meta=record)


@router.post("/{study_id}/generate-report")
async def generate_report(study_id: str, user=Depends(get_current_user)):
    """Build report snapshot from persisted V2 study state."""
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")
    state = _state_from_record(record)
    from ai_engine.agents.report import run_report

    state = run_report(state)
    _save_study(study_id, state.model_dump(), user_id)
    return _payload_from_state(study_id, state, record_meta=record)


@router.get("/{study_id}/report.pdf")
async def download_report_pdf(study_id: str, user=Depends(get_current_user)):
    """Arabic/English PDF from V2 state via existing reportlab generator."""
    from fastapi.responses import Response

    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")
    state = _state_from_record(record)
    from ai_engine.agents.report import build_v2_report_context
    from app.services.reporting import generate_pdf

    ctx = build_v2_report_context(state)
    # Ensure report snapshot exists
    from ai_engine.agents.report import run_report

    state = run_report(state)
    _save_study(study_id, state.model_dump(), user_id)
    data = generate_pdf(ctx, locale=state.language)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="study-{study_id}.pdf"',
        },
    )


@router.post("/{study_id}/advance")
async def advance_study(study_id: str, user=Depends(get_current_user)):
    """Continue pipeline when not at a human gate (no dead ends)."""
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")
    _, run_study_step = _import_engine()
    state = _state_from_record(record)
    state = await _advance_pipeline(state, run_study_step, max_steps=4)
    _save_study(study_id, state.model_dump(), user_id)
    return _payload_from_state(study_id, state, record_meta=record)


@router.get("")
async def list_studies(user=Depends(get_current_user)):
    return {"studies": _list_user_studies(str(user.id))}
