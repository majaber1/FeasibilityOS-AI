"""
Study assumptions API: versioned, provenance-tagged inputs scoped to a study.

An assumption is a value the study's analysis *uses* (rent, headcount,
utilization...), distinct from an EvidenceItem (a sourced fact). Posting a new
assumption for a key that already has an active row retires the previous row
(is_active=False) and creates a new version rather than overwriting history,
so "what changed and why" stays inspectable (see the study's Version History
target in docs/architecture/CURRENT_STATE_AUDIT.md).

origin=AI_SUGGESTED is a required, explicit label -- never silently upgraded
to USER or treated as a verified market fact by any consumer. origin=
EVIDENCE_DERIVED must reference an evidence_id belonging to the same study.

Ownership follows the study's parent project owner (see
app.services.study_access). Requires persistence (DATABASE_URL).
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.db import DB_ENABLED, SessionLocal
from app.api.auth import UserOut, get_current_user
from app.services.study_access import owned_study_or_error
from app.services.source_registry import CONFIDENCE_LEVELS

router = APIRouter(prefix="/studies/{study_id}/assumptions", tags=["assumptions"])

ORIGINS = ("USER", "EVIDENCE_DERIVED", "AI_SUGGESTED", "DEFAULT")


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Assumptions require persistence (database not configured).")
    return SessionLocal()


class AssumptionCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=80)
    label_en: str = Field(..., min_length=1, max_length=200)
    label_ar: str = Field(..., min_length=1, max_length=200)
    value_number: Optional[float] = None
    value_text: Optional[str] = Field(default=None, max_length=300)
    unit: Optional[str] = Field(default=None, max_length=50)
    origin: str = Field(...)
    reason: Optional[str] = None
    confidence: str = Field(default="medium")
    evidence_id: Optional[int] = None

    @model_validator(mode="after")
    def _validate(self):
        if self.origin not in ORIGINS:
            raise ValueError(f"origin must be one of {ORIGINS}")
        if self.confidence not in CONFIDENCE_LEVELS:
            raise ValueError(f"confidence must be one of {CONFIDENCE_LEVELS}")
        if self.value_number is None and not self.value_text:
            raise ValueError("value_number or value_text is required")
        if self.evidence_id is not None and self.origin != "EVIDENCE_DERIVED":
            raise ValueError("evidence_id may only be set when origin=EVIDENCE_DERIVED")
        if self.origin == "EVIDENCE_DERIVED" and self.evidence_id is None:
            raise ValueError("origin=EVIDENCE_DERIVED requires evidence_id")
        return self


class AssumptionOut(BaseModel):
    id: int
    study_id: int
    key: str
    label_en: str
    label_ar: str
    value_number: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    origin: str
    reason: Optional[str] = None
    confidence: str
    evidence_id: Optional[int] = None
    version: int
    is_active: bool

    model_config = {"from_attributes": True}


@router.post("/", response_model=AssumptionOut, status_code=201)
def create_assumption(study_id: int, data: AssumptionCreate, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)

        if data.evidence_id is not None:
            evidence = db.get(models.EvidenceItem, data.evidence_id)
            if evidence is None or evidence.study_id != study_id:
                raise HTTPException(status_code=422, detail="evidence_id must reference evidence in this study")

        previous = (
            db.query(models.StudyAssumption)
            .filter(
                models.StudyAssumption.study_id == study_id,
                models.StudyAssumption.key == data.key,
                models.StudyAssumption.is_active.is_(True),
            )
            .first()
        )
        next_version = 1
        if previous is not None:
            previous.is_active = False
            next_version = previous.version + 1
            db.add(previous)

        row = models.StudyAssumption(
            study_id=study_id,
            created_by=user.id,
            version=next_version,
            is_active=True,
            **data.model_dump(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


@router.get("/", response_model=List[AssumptionOut])
def list_assumptions(study_id: int, include_inactive: bool = False, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        q = db.query(models.StudyAssumption).filter(models.StudyAssumption.study_id == study_id)
        if not include_inactive:
            q = q.filter(models.StudyAssumption.is_active.is_(True))
        rows = q.order_by(models.StudyAssumption.key.asc(), models.StudyAssumption.version.desc()).all()
        return rows
    finally:
        db.close()


@router.delete("/{assumption_id}", response_model=AssumptionOut)
def retire_assumption(study_id: int, assumption_id: int, user: UserOut = Depends(get_current_user)):
    """Soft-retire an assumption (is_active=False) without deleting its history."""
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        row = db.get(models.StudyAssumption, assumption_id)
        if row is None or row.study_id != study_id:
            raise HTTPException(status_code=404, detail="Assumption not found")
        row.is_active = False
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()
