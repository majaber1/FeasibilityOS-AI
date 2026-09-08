"""
Extracted Financial Facts API: structured facts traced to a source document.

No automated OCR/document-understanding pipeline is configured in this
environment (see docs/architecture/CURRENT_STATE_AUDIT.md and the
ExtractedFinancialFact model docstring) -- every fact here is entered by a
human who read the source document. extraction_status/confidence/
review_status are always recorded so a low-confidence or unreviewed fact is
never presented as a verified figure. Every fact must reference a document
already linked to the same study; nothing here calculates or infers a value
that wasn't in the document.

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

router = APIRouter(prefix="/studies/{study_id}/extracted-facts", tags=["extracted-facts"])

REVIEW_STATUSES = ("unreviewed", "confirmed", "rejected")


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Extracted facts require persistence (database not configured).")
    return SessionLocal()


class ExtractedFactCreate(BaseModel):
    document_id: int
    field_name: str = Field(..., min_length=1, max_length=100)
    value_number: Optional[float] = None
    value_text: Optional[str] = Field(default=None, max_length=300)
    unit: Optional[str] = Field(default=None, max_length=50)
    period: Optional[str] = Field(default=None, max_length=50)
    source_location: Optional[str] = Field(default=None, max_length=200)
    confidence: str = Field(default="high")
    review_status: str = Field(default="confirmed")

    @model_validator(mode="after")
    def _validate(self):
        if self.confidence not in CONFIDENCE_LEVELS:
            raise ValueError(f"confidence must be one of {CONFIDENCE_LEVELS}")
        if self.review_status not in REVIEW_STATUSES:
            raise ValueError(f"review_status must be one of {REVIEW_STATUSES}")
        if self.value_number is None and not self.value_text:
            raise ValueError("value_number or value_text is required")
        return self


class ExtractedFactOut(BaseModel):
    id: int
    study_id: int
    document_id: int
    field_name: str
    value_number: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    period: Optional[str] = None
    source_location: Optional[str] = None
    extraction_status: str
    confidence: str
    review_status: str

    model_config = {"from_attributes": True}


@router.post("/", response_model=ExtractedFactOut, status_code=201)
def create_extracted_fact(study_id: int, data: ExtractedFactCreate, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        document = db.get(models.Document, data.document_id)
        if document is None or document.study_id != study_id:
            raise HTTPException(status_code=422, detail="document_id must reference a document already linked to this study")

        row = models.ExtractedFinancialFact(
            study_id=study_id,
            created_by=user.id,
            extraction_status="user_entered",
            **data.model_dump(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


@router.get("/", response_model=List[ExtractedFactOut])
def list_extracted_facts(study_id: int, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        rows = (
            db.query(models.ExtractedFinancialFact)
            .filter(models.ExtractedFinancialFact.study_id == study_id)
            .order_by(models.ExtractedFinancialFact.id.desc())
            .all()
        )
        return rows
    finally:
        db.close()


@router.delete("/{fact_id}", status_code=204)
def delete_extracted_fact(study_id: int, fact_id: int, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        row = db.get(models.ExtractedFinancialFact, fact_id)
        if row is None or row.study_id != study_id:
            raise HTTPException(status_code=404, detail="Extracted fact not found")
        db.delete(row)
        db.commit()
        return None
    finally:
        db.close()
