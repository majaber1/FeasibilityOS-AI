"""
Explainable Decision API (Phase 13): GO/CONDITIONAL_GO/NO_GO/
INSUFFICIENT_EVIDENCE derived deterministically from the study's evidence
count and its latest BASE/CONSERVATIVE scenario runs (see
app.services.decision_engine). The decision authority is deterministic
code, never an AI-generated score; a later AI Advisor phase may explain
this decision but must not override it.

POST computes and persists a new immutable decision snapshot (the study's
decision history is never overwritten). Ownership follows the study's
parent project owner. Requires persistence (DATABASE_URL).
"""
from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import DB_ENABLED, SessionLocal
from app.api.auth import UserOut, get_current_user
from app.services.study_access import owned_study_or_error
from app.services.decision_engine import evaluate_decision

router = APIRouter(prefix="/studies/{study_id}/decision", tags=["decision"])


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Decisions require persistence (database not configured).")
    return SessionLocal()


class DecisionOut(BaseModel):
    id: int
    study_id: int
    decision: str
    reason: str
    conditions: List[str]
    key_drivers: List[str]
    key_risks: List[str]
    evidence_references: List[int]
    scenario_references: Dict[str, Optional[int]]

    model_config = {"from_attributes": True}


def _latest_scenario(db, models, study_id: int, scenario_type: str):
    return (
        db.query(models.ScenarioRun)
        .filter(models.ScenarioRun.study_id == study_id, models.ScenarioRun.scenario_type == scenario_type)
        .order_by(models.ScenarioRun.id.desc())
        .first()
    )


def _scenario_dict(row) -> Optional[dict]:
    if row is None:
        return None
    return {
        "id": row.id,
        "financial_result_snapshot": row.financial_result_snapshot,
        "source_assumption_values": row.source_assumption_values,
    }


@router.post("/", response_model=DecisionOut, status_code=201)
def create_decision(study_id: int, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)

        evidence_count = db.query(models.EvidenceItem).filter(models.EvidenceItem.study_id == study_id).count()
        evidence_ids = [
            row.id
            for row in db.query(models.EvidenceItem.id).filter(models.EvidenceItem.study_id == study_id).all()
        ]

        base_row = _latest_scenario(db, models, study_id, "BASE")
        conservative_row = _latest_scenario(db, models, study_id, "CONSERVATIVE")
        optimistic_row = _latest_scenario(db, models, study_id, "OPTIMISTIC")

        outcome = evaluate_decision(
            evidence_count=evidence_count,
            base_scenario=_scenario_dict(base_row),
            conservative_scenario=_scenario_dict(conservative_row),
        )

        row = models.StudyDecision(
            study_id=study_id,
            created_by=user.id,
            decision=outcome["decision"],
            reason=outcome["reason"],
            conditions=outcome["conditions"],
            key_drivers=outcome["key_drivers"],
            key_risks=outcome["key_risks"],
            evidence_references=evidence_ids,
            scenario_references={
                "BASE": base_row.id if base_row else None,
                "CONSERVATIVE": conservative_row.id if conservative_row else None,
                "OPTIMISTIC": optimistic_row.id if optimistic_row else None,
            },
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


@router.get("/", response_model=DecisionOut)
def get_latest_decision(study_id: int, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        row = (
            db.query(models.StudyDecision)
            .filter(models.StudyDecision.study_id == study_id)
            .order_by(models.StudyDecision.id.desc())
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="No decision has been computed for this study yet")
        return row
    finally:
        db.close()


@router.get("/history", response_model=List[DecisionOut])
def list_decision_history(study_id: int, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        rows = (
            db.query(models.StudyDecision)
            .filter(models.StudyDecision.study_id == study_id)
            .order_by(models.StudyDecision.id.desc())
            .all()
        )
        return rows
    finally:
        db.close()
