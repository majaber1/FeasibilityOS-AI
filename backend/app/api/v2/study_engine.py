from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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
    now = datetime.now(timezone.utc).isoformat()
    db = _get_db_session()
    if db is not None:
        try:
            row = db.query(StudyStateRow).filter_by(study_id=study_id).first()
            if row:
                row.language = state_dict.get("language", "ar")
                row.phase = state_dict.get("phase", "DRAFT")
                row.phase_history = state_dict.get("phase_history", [])
                row.profile_json = state_dict.get("profile")
                row.profile_confirmed = state_dict.get("profile_confirmed", False)
                row.claims_json = [c if isinstance(c, dict) else c for c in state_dict.get("claims", [])]
                row.evidence_approved = state_dict.get("evidence_approved", False)
                row.assumptions_json = {
                    "_v": int(state_dict.get("assumptions_version") or 0),
                    "items": [a if isinstance(a, dict) else a for a in state_dict.get("assumptions", [])],
                }
                row.assumptions_approved = state_dict.get("assumptions_approved", False)
                row.financial_results_json = state_dict.get("financial_results")
                row.verdict = state_dict.get("verdict")
                row.decision_rationale = state_dict.get("decision_rationale")
                row.decision_conditions = state_dict.get("decision_conditions", [])
                row.decision_risks = state_dict.get("decision_risks", [])
                row.decision_version = state_dict.get("decision_version", 0)
                row.messages_json = _serialize_messages(state_dict.get("messages", []))
                row.error = state_dict.get("error")
                row.updated_at = datetime.now(timezone.utc)
            else:
                row = StudyStateRow(
                    study_id=study_id,
                    project_id=state_dict.get("project_id", ""),
                    user_id=user_id,
                    language=state_dict.get("language", "ar"),
                    phase=state_dict.get("phase", "DRAFT"),
                    phase_history=state_dict.get("phase_history", []),
                    profile_json=state_dict.get("profile"),
                    profile_confirmed=state_dict.get("profile_confirmed", False),
                    claims_json=[c if isinstance(c, dict) else c for c in state_dict.get("claims", [])],
                    evidence_approved=state_dict.get("evidence_approved", False),
                    assumptions_json={
                        "_v": int(state_dict.get("assumptions_version") or 0),
                        "items": [a if isinstance(a, dict) else a for a in state_dict.get("assumptions", [])],
                    },
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
                db.add(row)

            last_ver = db.query(StudyVersionRow).filter_by(study_id=study_id).order_by(StudyVersionRow.version.desc()).first()
            version_num = (last_ver.version + 1) if last_ver else 1
            version_row = StudyVersionRow(
                study_id=study_id,
                version=version_num,
                phase=state_dict.get("phase", "DRAFT"),
                snapshot_json=state_dict,
            )
            db.add(version_row)
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
    raw_assumptions = row.assumptions_json or []
    assumptions_version = 0
    if isinstance(raw_assumptions, dict) and "items" in raw_assumptions:
        assumptions_version = int(raw_assumptions.get("_v") or 0)
        assumptions = raw_assumptions.get("items") or []
    else:
        assumptions = raw_assumptions if isinstance(raw_assumptions, list) else []
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
            "claims": row.claims_json or [],
            "evidence_approved": row.evidence_approved,
            "assumptions": assumptions,
            "assumptions_approved": row.assumptions_approved,
            "assumptions_version": assumptions_version,
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
            rows = db.query(StudyStateRow).filter_by(user_id=user_id).order_by(StudyStateRow.updated_at.desc()).all()
            return [
                {
                    "study_id": r.study_id,
                    "phase": r.phase,
                    "archetype": (r.profile_json or {}).get("archetype") if isinstance(r.profile_json, dict) else None,
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
            results.append({
                "study_id": sid,
                "phase": s.get("phase"),
                "archetype": (s.get("profile") or {}).get("archetype") if isinstance(s.get("profile"), dict) else None,
                "verdict": s.get("verdict"),
                "created_at": record.get("created_at"),
                "updated_at": record.get("updated_at"),
            })
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


def _normalize_profile_label(value: str | None, *, fallback: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned or cleaned.lower() in {"unknown", "n/a", "na", "none", "null", "-", "غير معروف"}:
        return fallback
    return cleaned


def _finalize_profile_confirmation(state):
    """Confirm Profile means: proceed even if gaps remain; AI must fill estimates next."""
    from langchain_core.messages import AIMessage, HumanMessage

    state.profile_confirmed = True
    gaps: list[str] = []
    if state.profile:
        state.profile.stage = _normalize_profile_label(state.profile.stage, fallback="idea")
        state.profile.decision_goal = _normalize_profile_label(
            state.profile.decision_goal, fallback="feasibility"
        )
        gaps = list(state.profile.missing_information or [])
        # Stop blocking the gate; later agents use conversation + estimates.
        state.profile.missing_information = []

    lang = getattr(state, "language", "en")
    if gaps:
        gap_lines = "\n".join(f"- {g}" for g in gaps)
        if lang == "ar":
            note = (
                "تم تأكيد ملف المشروع. سأملأ الآن الأدلة والافتراضات "
                "بتقديرات صريحة وواضحة للعناصر الناقصة التالية:\n"
                + gap_lines
            )
            instruct = (
                "تم تأكيد الملف. املأ الأدلة الآن. لكل عنصر ناقص أدناه، أنشئ claim "
                "من نوع ai_assumption بقيمة تقديرية واقعية للسوق السعودي، مع ذكر أنها تقدير:\n"
                + gap_lines
                + "\nثم اضبط evidence_sufficient=true إذا أصبحت التقديرات كافية للمتابعة."
            )
        else:
            note = (
                "Profile confirmed. I will now fill evidence and assumptions "
                "with explicit estimates for these remaining gaps:\n"
                + gap_lines
            )
            instruct = (
                "Profile confirmed. Fill evidence now. For each missing item below, create an "
                "ai_assumption claim with a realistic Saudi-market estimate and label it as an estimate:\n"
                + gap_lines
                + "\nThen set evidence_sufficient=true if these estimates are enough to continue."
            )
        state.messages.append(AIMessage(content=note))
        # Seed the next agent turn with an explicit fill request.
        state.messages.append(HumanMessage(content=instruct))
    else:
        if lang == "ar":
            state.messages.append(AIMessage(content="تم تأكيد الملف. المتابعة إلى جمع الأدلة."))
        else:
            state.messages.append(AIMessage(content="Profile confirmed. Continuing to evidence collection."))

    state.phase = "EVIDENCE_REVIEW"
    state.next_action = "review_evidence"
    # Clear any prior LLM failure so the orchestrator routes to evidence, not error_handler.
    state.error = None
    state.blocking_reason = None
    return state


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
    from ai_engine.models.study_state import StudyState
    # Copy so we do not mutate the cached/persisted record when popping messages.
    state_data = dict(record["state"])
    msgs = state_data.pop("messages", []) or []
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
    """Normalize persisted / LangChain messages for the workspace UI."""
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


def _study_payload(study_id: str, record: dict, *, response: str | None = None) -> dict:
    """Full study payload so the UI can show AI-filled information."""
    s = record["state"] if "state" in record else record
    claims = s.get("claims") or []
    assumptions = s.get("assumptions") or []
    profile = s.get("profile")
    fr = s.get("financial_results") or {}
    payload = {
        "study_id": study_id,
        "project_id": s.get("project_id"),
        "phase": s.get("phase"),
        "profile": profile,
        "claims": claims,
        "assumptions": assumptions,
        "claims_count": len(claims),
        "assumptions_count": len(assumptions),
        "assumptions_version": s.get("assumptions_version") or 0,
        "decision_version": s.get("decision_version") or 0,
        "financial_results": s.get("financial_results"),
        "funding_package": (fr or {}).get("funding_package") if isinstance(fr, dict) else None,
        "report_outline": (fr or {}).get("report_outline") if isinstance(fr, dict) else None,
        "report": (fr or {}).get("report") if isinstance(fr, dict) else None,
        "verdict": s.get("verdict"),
        "decision_rationale": s.get("decision_rationale"),
        "decision_conditions": s.get("decision_conditions") or [],
        "decision_risks": s.get("decision_risks") or [],
        "messages": _public_messages(s.get("messages")),
        "next_action": s.get("next_action"),
        "error": s.get("error"),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }
    if response is not None:
        payload["response"] = response
    return payload


def _payload_from_state(study_id: str, state, *, response: str | None = None, record_meta: dict | None = None) -> dict:
    claims = [c.model_dump() if hasattr(c, "model_dump") else c for c in (state.claims or [])]
    assumptions = [a.model_dump() if hasattr(a, "model_dump") else a for a in (state.assumptions or [])]
    profile = state.profile.model_dump() if state.profile and hasattr(state.profile, "model_dump") else state.profile
    fr = state.financial_results or {}
    payload = {
        "study_id": study_id,
        "project_id": state.project_id,
        "phase": state.phase,
        "profile": profile,
        "claims": claims,
        "assumptions": assumptions,
        "claims_count": len(claims),
        "assumptions_count": len(assumptions),
        "assumptions_version": getattr(state, "assumptions_version", 0) or 0,
        "decision_version": getattr(state, "decision_version", 0) or 0,
        "financial_results": state.financial_results,
        "funding_package": fr.get("funding_package") if isinstance(fr, dict) else None,
        "report_outline": fr.get("report_outline") if isinstance(fr, dict) else None,
        "report": fr.get("report") if isinstance(fr, dict) else None,
        "verdict": state.verdict,
        "decision_rationale": state.decision_rationale,
        "decision_conditions": state.decision_conditions or [],
        "decision_risks": state.decision_risks or [],
        "messages": _public_messages(state.messages),
        "next_action": state.next_action,
        "error": state.error,
        "created_at": (record_meta or {}).get("created_at"),
        "updated_at": (record_meta or {}).get("updated_at"),
    }
    if response is not None:
        payload["response"] = response
    return payload


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

    valid_stages = {
        "profile": ("NEEDS_INFORMATION", "profile_confirmed"),
        "evidence": ("EVIDENCE_REVIEW", "evidence_approved"),
        "assumptions": ("ASSUMPTIONS_REVIEW", "assumptions_approved"),
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

    if stage == "evidence" and not state.claims:
        raise HTTPException(status_code=400, detail="No evidence to approve.")

    if not req.approved:
        if req.feedback:
            from langchain_core.messages import HumanMessage
            state.messages.append(HumanMessage(content=req.feedback))
        _save_study(study_id, state.model_dump(), user_id)
        return _payload_from_state(
            study_id,
            state,
            record_meta=record,
        ) | {"message": "Feedback recorded. Continue the conversation."}

    setattr(state, flag_field, True)
    state.phase_history.append(f"{stage}_approved")

    # Advance phase BEFORE running the next agent. Otherwise the orchestrator
    # re-routes to the same gate agent (e.g. discovery) and Confirm appears stuck,
    # especially when missing_information is still non-empty.
    if stage == "profile":
        state = _finalize_profile_confirmation(state)
    elif stage == "evidence":
        state.phase = "ASSUMPTIONS_REVIEW"
    elif stage == "assumptions":
        state.phase = "READY_FOR_ANALYSIS"

    try:
        state = await run_study_step(state)
    except Exception as e:
        state.error = f"AI service error: {e}"

    _save_study(study_id, state.model_dump(), user_id)

    return _payload_from_state(study_id, state, record_meta=record)


@router.get("")
async def list_studies(user=Depends(get_current_user)):
    return {"studies": _list_user_studies(str(user.id))}
