"""
Study evidence API: sourced facts with provenance, scoped to a study.

Every evidence item traces a claim back to a source_type and, when a URL is
given, to the Saudi source authority registry (app.services.source_registry).
authority_level is ALWAYS computed server-side from source_type/source_url --
never accepted from the client -- so nothing can self-certify as an official
source. AI-produced claims (source_type="ai_inference") can never be marked
verification_status="verified".

Ownership is enforced identically to feasibility studies: derived from the
study's parent project owner (see app.services.study_access).

Requires persistence (DATABASE_URL); demo mode returns 503 rather than
faking evidence storage.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.db import DB_ENABLED, SessionLocal
from app.api.auth import UserOut, get_current_user
from app.services.study_access import owned_study_or_error
from app.services.source_registry import (
    AUTHORITY_LEVELS,
    SOURCE_TYPES,
    VERIFICATION_STATUSES,
    CONFIDENCE_LEVELS,
    classify_authority,
    registry_entries,
)

router = APIRouter(tags=["evidence"])


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Evidence requires persistence (database not configured).")
    return SessionLocal()


class EvidenceCreate(BaseModel):
    source_type: str = Field(..., description="One of: " + ", ".join(SOURCE_TYPES))
    source_name: Optional[str] = Field(default=None, max_length=200)
    source_url: Optional[str] = Field(default=None, max_length=500)
    publisher: Optional[str] = Field(default=None, max_length=200)

    title: str = Field(..., min_length=1, max_length=300)
    claim: str = Field(..., min_length=1)
    value_number: Optional[float] = None
    value_text: Optional[str] = Field(default=None, max_length=300)
    unit: Optional[str] = Field(default=None, max_length=50)

    geography: Optional[str] = Field(default=None, max_length=100)
    sector: Optional[str] = Field(default=None, max_length=100)

    published_at: Optional[datetime] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None

    confidence: str = Field(default="medium")
    verification_status: str = Field(default="unverified")

    snapshot_text: Optional[str] = None

    @model_validator(mode="after")
    def _validate_enums_and_guards(self):
        if self.source_type not in SOURCE_TYPES:
            raise ValueError(f"source_type must be one of {SOURCE_TYPES}")
        if self.confidence not in CONFIDENCE_LEVELS:
            raise ValueError(f"confidence must be one of {CONFIDENCE_LEVELS}")
        if self.verification_status not in VERIFICATION_STATUSES:
            raise ValueError(f"verification_status must be one of {VERIFICATION_STATUSES}")
        if self.source_type == "ai_inference" and self.verification_status == "verified":
            raise ValueError("AI-produced evidence can never be marked verified")
        if self.verification_status == "verified" and not self.source_url:
            raise ValueError("verification_status=verified requires a source_url")
        return self


class EvidenceUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    claim: Optional[str] = Field(default=None, min_length=1)
    value_number: Optional[float] = None
    value_text: Optional[str] = Field(default=None, max_length=300)
    unit: Optional[str] = Field(default=None, max_length=50)
    geography: Optional[str] = Field(default=None, max_length=100)
    sector: Optional[str] = Field(default=None, max_length=100)
    published_at: Optional[datetime] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    confidence: Optional[str] = None
    verification_status: Optional[str] = None
    source_url: Optional[str] = Field(default=None, max_length=500)
    source_name: Optional[str] = Field(default=None, max_length=200)
    publisher: Optional[str] = Field(default=None, max_length=200)
    snapshot_text: Optional[str] = None
    superseded_by_id: Optional[int] = None

    @model_validator(mode="after")
    def _validate_enums(self):
        if self.confidence is not None and self.confidence not in CONFIDENCE_LEVELS:
            raise ValueError(f"confidence must be one of {CONFIDENCE_LEVELS}")
        if self.verification_status is not None and self.verification_status not in VERIFICATION_STATUSES:
            raise ValueError(f"verification_status must be one of {VERIFICATION_STATUSES}")
        return self


class EvidenceOut(BaseModel):
    id: int
    study_id: int
    source_type: str
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    publisher: Optional[str] = None
    title: str
    claim: str
    value_number: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    geography: Optional[str] = None
    sector: Optional[str] = None
    published_at: Optional[datetime] = None
    retrieved_at: datetime
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    superseded_by_id: Optional[int] = None
    confidence: str
    verification_status: str
    authority_level: str
    snapshot_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RegistryOut(BaseModel):
    authority_levels: List[str]
    sources: List[dict]


@router.get("/sources/registry", response_model=RegistryOut)
def get_source_registry(user: UserOut = Depends(get_current_user)):
    """The maintainable Saudi authority registry used to classify evidence."""
    return RegistryOut(authority_levels=list(AUTHORITY_LEVELS), sources=registry_entries())


@router.post("/studies/{study_id}/evidence", response_model=EvidenceOut, status_code=201)
def create_evidence(study_id: int, data: EvidenceCreate, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        authority_level, _matched_key = classify_authority(data.source_url, data.source_type)
        row = models.EvidenceItem(
            study_id=study_id,
            created_by=user.id,
            authority_level=authority_level,
            **data.model_dump(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


@router.get("/studies/{study_id}/evidence", response_model=List[EvidenceOut])
def list_evidence(
    study_id: int,
    verification_status: Optional[str] = None,
    user: UserOut = Depends(get_current_user),
):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        q = db.query(models.EvidenceItem).filter(models.EvidenceItem.study_id == study_id)
        if verification_status is not None:
            q = q.filter(models.EvidenceItem.verification_status == verification_status)
        rows = q.order_by(models.EvidenceItem.id.desc()).all()
        return rows
    finally:
        db.close()


def _get_evidence_or_404(db, models, study_id: int, evidence_id: int):
    row = db.get(models.EvidenceItem, evidence_id)
    if row is None or row.study_id != study_id:
        raise HTTPException(status_code=404, detail="Evidence item not found")
    return row


@router.get("/studies/{study_id}/evidence/{evidence_id}", response_model=EvidenceOut)
def get_evidence(study_id: int, evidence_id: int, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        return _get_evidence_or_404(db, models, study_id, evidence_id)
    finally:
        db.close()


@router.patch("/studies/{study_id}/evidence/{evidence_id}", response_model=EvidenceOut)
def update_evidence(study_id: int, evidence_id: int, data: EvidenceUpdate, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        row = _get_evidence_or_404(db, models, study_id, evidence_id)
        changes = data.model_dump(exclude_unset=True)
        if changes.get("verification_status") == "verified":
            new_url = changes.get("source_url", row.source_url)
            if not new_url:
                raise HTTPException(status_code=422, detail="verification_status=verified requires a source_url")
        for field, value in changes.items():
            setattr(row, field, value)
        if "source_url" in changes or "source_type" in changes:
            authority_level, _matched_key = classify_authority(row.source_url, row.source_type)
            row.authority_level = authority_level
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


@router.delete("/studies/{study_id}/evidence/{evidence_id}", status_code=204)
def delete_evidence(study_id: int, evidence_id: int, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        row = _get_evidence_or_404(db, models, study_id, evidence_id)
        referencing = (
            db.query(models.StudyAssumption)
            .filter(models.StudyAssumption.evidence_id == evidence_id, models.StudyAssumption.is_active.is_(True))
            .count()
        )
        if referencing:
            raise HTTPException(
                status_code=409,
                detail=f"Evidence is referenced by {referencing} active assumption(s); retire those first.",
            )
        db.delete(row)
        db.commit()
        return None
    finally:
        db.close()
