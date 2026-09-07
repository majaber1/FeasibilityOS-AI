from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import get_current_user

router = APIRouter(prefix="/api/v2/studies", tags=["v2-studies"])


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


_studies: dict[str, dict] = {}


@router.post("")
async def create_study(req: StudyCreateRequest, user=Depends(get_current_user)):
    try:
        from ai_engine.models.study_state import StudyState
        from ai_engine.orchestrator import run_study_step
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="AI engine not available. Please install ai-engine dependencies.",
        )

    study_id = f"study_{uuid.uuid4().hex[:12]}"

    state = StudyState(
        study_id=study_id,
        project_id=req.project_id,
        user_id=str(user.id),
        language=req.language,
        phase="DRAFT",
    )

    if req.description:
        from langchain_core.messages import HumanMessage
        state.messages.append(HumanMessage(content=req.description))

        try:
            state = await run_study_step(state)
        except Exception as e:
            state.error = str(e)

    _studies[study_id] = {
        "state": state.model_dump(),
        "user_id": str(user.id),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "study_id": study_id,
        "phase": state.phase,
        "profile": state.profile.model_dump() if state.profile else None,
        "next_action": state.next_action,
        "error": state.error,
    }


@router.get("/{study_id}")
async def get_study(study_id: str, user=Depends(get_current_user)):
    record = _studies.get(study_id)
    if not record or record["user_id"] != str(user.id):
        raise HTTPException(status_code=404, detail="Study not found")

    from ai_engine.models.study_state import StudyState
    state = StudyState(**record["state"])

    return {
        "study_id": study_id,
        "phase": state.phase,
        "profile": state.profile.model_dump() if state.profile else None,
        "claims_count": len(state.claims),
        "assumptions_count": len(state.assumptions),
        "verdict": state.verdict,
        "decision_rationale": state.decision_rationale,
        "next_action": state.next_action,
        "error": state.error,
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
    }


@router.post("/{study_id}/message")
async def send_message(study_id: str, req: StudyMessageRequest, user=Depends(get_current_user)):
    record = _studies.get(study_id)
    if not record or record["user_id"] != str(user.id):
        raise HTTPException(status_code=404, detail="Study not found")

    try:
        from ai_engine.models.study_state import StudyState
        from ai_engine.orchestrator import run_study_step
    except ImportError:
        raise HTTPException(status_code=503, detail="AI engine not available.")

    state = StudyState(**record["state"])
    if req.language:
        state.language = req.language

    from langchain_core.messages import HumanMessage
    state.messages.append(HumanMessage(content=req.message))
    state.error = None

    try:
        state = await run_study_step(state)
    except Exception as e:
        state.error = str(e)

    record["state"] = state.model_dump()
    record["updated_at"] = datetime.now(timezone.utc).isoformat()

    last_ai_message = None
    for msg in reversed(state.messages):
        if hasattr(msg, "type") and msg.type == "ai":
            last_ai_message = msg.content
            break

    return {
        "phase": state.phase,
        "response": last_ai_message,
        "profile": state.profile.model_dump() if state.profile else None,
        "next_action": state.next_action,
        "error": state.error,
    }


@router.post("/{study_id}/approve/{stage}")
async def approve_stage(
    study_id: str,
    stage: str,
    req: StudyApprovalRequest,
    user=Depends(get_current_user),
):
    record = _studies.get(study_id)
    if not record or record["user_id"] != str(user.id):
        raise HTTPException(status_code=404, detail="Study not found")

    try:
        from ai_engine.models.study_state import StudyState
        from ai_engine.orchestrator import run_study_step
    except ImportError:
        raise HTTPException(status_code=503, detail="AI engine not available.")

    state = StudyState(**record["state"])

    valid_stages = {
        "profile": ("NEEDS_INFORMATION", "profile_confirmed"),
        "evidence": ("EVIDENCE_REVIEW", "evidence_approved"),
        "assumptions": ("ASSUMPTIONS_REVIEW", "assumptions_approved"),
    }

    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")

    expected_phase, flag_field = valid_stages[stage]

    if not req.approved:
        if req.feedback:
            from langchain_core.messages import HumanMessage
            state.messages.append(HumanMessage(content=req.feedback))
        record["state"] = state.model_dump()
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        return {"phase": state.phase, "message": "Feedback recorded. Continue the conversation."}

    setattr(state, flag_field, True)
    state.phase_history.append(f"{stage}_approved")

    try:
        state = await run_study_step(state)
    except Exception as e:
        state.error = str(e)

    record["state"] = state.model_dump()
    record["updated_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "phase": state.phase,
        "next_action": state.next_action,
        "error": state.error,
    }


@router.get("")
async def list_studies(user=Depends(get_current_user)):
    user_studies = []
    for sid, record in _studies.items():
        if record["user_id"] == str(user.id):
            from ai_engine.models.study_state import StudyState
            state = StudyState(**record["state"])
            user_studies.append({
                "study_id": sid,
                "phase": state.phase,
                "archetype": state.profile.archetype if state.profile else None,
                "verdict": state.verdict,
                "created_at": record["created_at"],
                "updated_at": record["updated_at"],
            })
    return {"studies": user_studies}
