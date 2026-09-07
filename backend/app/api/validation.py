"""FastAPI Router for Wave 4 Validation OS.

Endpoints for managing market validation workspaces, hypotheses, experiments,
traceable evidence, and immutable validation decisions.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import db, models
from app.api.auth import get_current_user
from app.services.validation import (
    get_or_create_validation_workspace,
    evaluate_workspace_status,
    add_hypothesis,
    update_hypothesis,
    add_experiment,
    update_experiment,
    record_evidence,
    record_validation_decision,
)

router = APIRouter(prefix="/api/v1/validation", tags=["Validation OS (Wave 4)"])


# Pydantic Schemas
class HypothesisCreateIn(BaseModel):
    hypothesis_type: str = Field(..., description="CUSTOMER_PROBLEM, DEMAND, WILLINGNESS_TO_PAY, etc.")
    statement: str = Field(..., min_length=5)
    importance: str = Field("HIGH", description="CRITICAL, HIGH, MEDIUM, LOW")
    rationale: Optional[str] = None


class HypothesisUpdateIn(BaseModel):
    statement: Optional[str] = None
    importance: Optional[str] = None
    status: Optional[str] = None
    rationale: Optional[str] = None


class ExperimentCreateIn(BaseModel):
    experiment_type: str = Field(..., description="CUSTOMER_INTERVIEW, SURVEY, LANDING_PAGE, etc.")
    title: str = Field(..., min_length=3)
    objective: str
    method: str
    success_criteria: str
    hypothesis_id: Optional[int] = None
    planned_sample_size: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ExperimentUpdateIn(BaseModel):
    status: Optional[str] = None
    result_summary: Optional[str] = None


class EvidenceCreateIn(BaseModel):
    evidence_type: str = Field(..., description="USER_RECORDED, INTERVIEW, SURVEY, WAITLIST, etc.")
    title: str = Field(..., min_length=3)
    hypothesis_id: Optional[int] = None
    experiment_id: Optional[int] = None
    source_type: str = "USER_RECORDED"
    source_url: Optional[str] = None
    source_owner: Optional[str] = None
    notes: Optional[str] = None
    raw_value: Optional[float] = None
    unit: Optional[str] = None
    evidence_strength: str = "MODERATE"
    evidence_direction: Optional[str] = Field(None, description="SUPPORTING, REFUTING, NEUTRAL")
    is_simulated: bool = False
    structured_payload: Dict[str, Any] = Field(default_factory=dict)


class DecisionCreateIn(BaseModel):
    decision: str = Field(..., description="GO, GO_WITH_CONDITIONS, PIVOT, STOP")
    decision_reason: str = Field(..., min_length=10)
    conditions: List[str] = Field(default_factory=list)


def _serialize_workspace(ws: models.ValidationWorkspace, db_session: Session) -> Dict[str, Any]:
    eval_res = evaluate_workspace_status(ws)
    all_study_workspaces = (
        db_session.query(models.ValidationWorkspace.id)
        .filter_by(study_id=ws.study_id)
        .order_by(models.ValidationWorkspace.id.asc())
        .all()
    )
    all_ids = [row[0] for row in all_study_workspaces]
    current_cycle_number = (all_ids.index(ws.id) + 1) if ws.id in all_ids else 1
    is_current_cycle = (ws.id == all_ids[-1]) if all_ids else True

    return {
        "id": ws.id,
        "project_id": ws.project_id,
        "study_id": ws.study_id,
        "status": ws.status,
        "evaluation": eval_res,
        "cycle_number": current_cycle_number,
        "total_cycles": len(all_ids),
        "is_current_cycle": is_current_cycle,
        "historical_cycle_ids": all_ids,
        "created_at": ws.created_at.isoformat() if ws.created_at else None,
        "updated_at": ws.updated_at.isoformat() if ws.updated_at else None,
        "hypotheses": [
            {
                "id": h.id,
                "hypothesis_type": h.hypothesis_type,
                "statement": h.statement,
                "importance": h.importance,
                "status": h.status,
                "rationale": h.rationale,
                "created_at": h.created_at.isoformat() if h.created_at else None,
                "evidence_count": len(h.evidence),
            }
            for h in ws.hypotheses
        ],
        "experiments": [
            {
                "id": e.id,
                "hypothesis_id": e.hypothesis_id,
                "experiment_type": e.experiment_type,
                "title": e.title,
                "objective": e.objective,
                "method": e.method,
                "planned_sample_size": e.planned_sample_size,
                "success_criteria": e.success_criteria,
                "status": e.status,
                "start_date": e.start_date,
                "end_date": e.end_date,
                "result_summary": e.result_summary,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in ws.experiments
        ],
        "evidence": [
            {
                "id": ev.id,
                "hypothesis_id": ev.hypothesis_id,
                "experiment_id": ev.experiment_id,
                "evidence_type": ev.evidence_type,
                "title": ev.title,
                "notes": ev.notes,
                "source_type": ev.source_type,
                "source_url": ev.source_url,
                "source_owner": ev.source_owner,
                "raw_value": ev.raw_value,
                "unit": ev.unit,
                "captured_at": ev.captured_at.isoformat() if ev.captured_at else None,
                "evidence_strength": ev.evidence_strength,
                "evidence_direction": getattr(ev, "evidence_direction", "NEUTRAL") or "NEUTRAL",
                "is_simulated": ev.is_simulated,
                "structured_payload": ev.structured_payload or {},
            }
            for ev in ws.evidence
        ],
        "latest_decision": (
            {
                "id": ws.decisions[0].id,
                "decision": ws.decisions[0].decision,
                "decision_reason": ws.decisions[0].decision_reason,
                "conditions": ws.decisions[0].conditions,
                "evidence_snapshot": ws.decisions[0].evidence_snapshot,
                "decided_at": ws.decisions[0].decided_at.isoformat(),
                "decision_version": ws.decisions[0].decision_version,
            }
            if ws.decisions
            else None
        ),
    }


@router.get("/study/{study_id}", status_code=status.HTTP_200_OK)
def get_or_create_workspace(
    study_id: int,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Fetches or initializes the validation workspace for a study with ownership isolation."""
    try:
        ws = get_or_create_validation_workspace(db=db_session, user=user, study_id=study_id)
        return _serialize_workspace(ws, db_session)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/study/{study_id}/cycles", status_code=status.HTTP_200_OK)
def list_validation_cycles(
    study_id: int,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Lists all validation cycles for a study with summary metadata."""
    study = db_session.query(models.FeasibilityStudy).filter_by(id=study_id).first()
    if not study:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feasibility study not found")
    if study.project.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    workspaces = (
        db_session.query(models.ValidationWorkspace)
        .filter_by(study_id=study_id)
        .order_by(models.ValidationWorkspace.id.asc())
        .all()
    )
    cycles = []
    for idx, w in enumerate(workspaces, start=1):
        latest_dec = w.decisions[0].decision if w.decisions else None
        cycles.append({
            "workspace_id": w.id,
            "cycle_number": idx,
            "is_current": (idx == len(workspaces)),
            "status": w.status,
            "latest_decision": latest_dec,
            "hypotheses_count": len(w.hypotheses),
            "evidence_count": len(w.evidence),
            "created_at": w.created_at.isoformat() if w.created_at else None,
        })
    cycles.reverse()
    return {"study_id": study_id, "cycles": cycles, "total_cycles": len(cycles)}


@router.get("/workspaces/{workspace_id}", status_code=status.HTTP_200_OK)
def get_workspace(
    workspace_id: int,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Retrieves full validation workspace by ID."""
    ws = db_session.query(models.ValidationWorkspace).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مساحة التحقق غير موجودة")
    if ws.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="غير مصرح لك بالوصول إلى هذه المساحة")
    return _serialize_workspace(ws, db_session)


@router.post("/workspaces/{workspace_id}/hypotheses", status_code=status.HTTP_201_CREATED)
def create_hypothesis(
    workspace_id: int,
    data: HypothesisCreateIn,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Adds a new hypothesis to the validation workspace."""
    try:
        h = add_hypothesis(
            db=db_session,
            workspace_id=workspace_id,
            user=user,
            hypothesis_type=data.hypothesis_type,
            statement=data.statement,
            importance=data.importance,
            rationale=data.rationale,
        )
        return {
            "id": h.id,
            "hypothesis_type": h.hypothesis_type,
            "statement": h.statement,
            "importance": h.importance,
            "status": h.status,
            "rationale": h.rationale,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/hypotheses/{hypothesis_id}", status_code=status.HTTP_200_OK)
def modify_hypothesis(
    hypothesis_id: int,
    data: HypothesisUpdateIn,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Updates a hypothesis. Enforces that SUPPORTED status cannot be set without real evidence."""
    h_item = db_session.query(models.ValidationHypothesis).filter_by(id=hypothesis_id).first()
    if not h_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الفرضية غير موجودة")
    if h_item.workspace.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="غير مصرح بالوصول إلى هذه الفرضية")
    try:
        h = update_hypothesis(
            db=db_session,
            hypothesis_id=hypothesis_id,
            user=user,
            statement=data.statement,
            importance=data.importance,
            status=data.status,
            rationale=data.rationale,
        )
        return {
            "id": h.id,
            "hypothesis_type": h.hypothesis_type,
            "statement": h.statement,
            "importance": h.importance,
            "status": h.status,
            "rationale": h.rationale,
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/workspaces/{workspace_id}/experiments", status_code=status.HTTP_201_CREATED)
def create_experiment(
    workspace_id: int,
    data: ExperimentCreateIn,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Creates a validation experiment."""
    ws = db_session.query(models.ValidationWorkspace).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مساحة التحقق غير موجودة")
    if ws.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="غير مصرح بالوصول إلى هذه المساحة")
    try:
        exp = add_experiment(
            db=db_session,
            workspace_id=workspace_id,
            user=user,
            experiment_type=data.experiment_type,
            title=data.title,
            objective=data.objective,
            method=data.method,
            success_criteria=data.success_criteria,
            hypothesis_id=data.hypothesis_id,
            planned_sample_size=data.planned_sample_size,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        return {
            "id": exp.id,
            "experiment_type": exp.experiment_type,
            "title": exp.title,
            "status": exp.status,
            "objective": exp.objective,
            "method": exp.method,
            "success_criteria": exp.success_criteria,
            "hypothesis_id": exp.hypothesis_id,
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/experiments/{experiment_id}", status_code=status.HTTP_200_OK)
def modify_experiment(
    experiment_id: int,
    data: ExperimentUpdateIn,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Updates status or results summary of an experiment."""
    exp_item = db_session.query(models.ValidationExperiment).filter_by(id=experiment_id).first()
    if not exp_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="التجربة غير موجودة")
    if exp_item.workspace.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="غير مصرح بالوصول إلى هذه التجربة")
    try:
        exp = update_experiment(
            db=db_session,
            experiment_id=experiment_id,
            user=user,
            status=data.status,
            result_summary=data.result_summary,
        )
        return {
            "id": exp.id,
            "status": exp.status,
            "result_summary": exp.result_summary,
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/workspaces/{workspace_id}/evidence", status_code=status.HTTP_201_CREATED)
def create_evidence(
    workspace_id: int,
    data: EvidenceCreateIn,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Records verifiable empirical evidence."""
    ws = db_session.query(models.ValidationWorkspace).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مساحة التحقق غير موجودة")
    if ws.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="غير مصرح بالوصول إلى هذه المساحة")
    if data.hypothesis_id and not data.evidence_direction:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="يجب تحديد أثر الدليل على الفرضية بشكل صريح (SUPPORTING, REFUTING, NEUTRAL).",
        )
    try:
        ev = record_evidence(
            db=db_session,
            workspace_id=workspace_id,
            user=user,
            evidence_type=data.evidence_type,
            title=data.title,
            hypothesis_id=data.hypothesis_id,
            experiment_id=data.experiment_id,
            source_type=data.source_type,
            source_url=data.source_url,
            source_owner=data.source_owner,
            notes=data.notes,
            raw_value=data.raw_value,
            unit=data.unit,
            evidence_strength=data.evidence_strength,
            evidence_direction=data.evidence_direction,
            is_simulated=data.is_simulated,
            structured_payload=data.structured_payload,
        )
        return {
            "id": ev.id,
            "evidence_type": ev.evidence_type,
            "title": ev.title,
            "notes": ev.notes,
            "source_type": ev.source_type,
            "source_url": ev.source_url,
            "source_owner": ev.source_owner,
            "raw_value": ev.raw_value,
            "unit": ev.unit,
            "evidence_strength": ev.evidence_strength,
            "evidence_direction": getattr(ev, "evidence_direction", "NEUTRAL") or "NEUTRAL",
            "is_simulated": ev.is_simulated,
            "structured_payload": ev.structured_payload,
            "captured_at": ev.captured_at.isoformat() if ev.captured_at else None,
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/workspaces/{workspace_id}/decision", status_code=status.HTTP_201_CREATED)
def create_decision(
    workspace_id: int,
    data: DecisionCreateIn,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Records an immutable validation decision."""
    ws = db_session.query(models.ValidationWorkspace).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مساحة التحقق غير موجودة")
    if ws.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="غير مصرح بالوصول إلى هذه المساحة")
    try:
        dec = record_validation_decision(
            db=db_session,
            workspace_id=workspace_id,
            user=user,
            decision=data.decision,
            decision_reason=data.decision_reason,
            conditions=data.conditions,
        )
        return {
            "id": dec.id,
            "decision": dec.decision,
            "decision_reason": dec.decision_reason,
            "conditions": dec.conditions,
            "evidence_snapshot": dec.evidence_snapshot,
            "decision_version": dec.decision_version,
            "decided_at": dec.decided_at.isoformat(),
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/workspaces/{workspace_id}/decisions", status_code=status.HTTP_200_OK)
def list_decisions(
    workspace_id: int,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Lists historical immutable validation decisions."""
    ws = db_session.query(models.ValidationWorkspace).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مساحة التحقق غير موجودة")
    if ws.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="غير مصرح بالوصول")
    return [
        {
            "id": d.id,
            "decision": d.decision,
            "decision_reason": d.decision_reason,
            "conditions": d.conditions,
            "evidence_snapshot": d.evidence_snapshot,
            "decision_version": d.decision_version,
            "decided_at": d.decided_at.isoformat(),
        }
        for d in ws.decisions
    ]
