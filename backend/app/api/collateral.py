"""
Collateral API (Phase 16): structured collateral records for a study, with
explicit verification/encumbrance state and a deterministic summary. See
app.services.collateral for the validation rules and the "market value is
not lendable value" principle -- no haircut or lendable amount is computed
here.

Ownership follows the study's parent project owner (see
app.services.study_access). Requires persistence (DATABASE_URL).
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.db import DB_ENABLED, SessionLocal
from app.api.auth import UserOut, get_current_user
from app.services.study_access import owned_study_or_error
from app.services.collateral import summarize_collateral, validate_consistency

router = APIRouter(prefix="/studies/{study_id}/collateral", tags=["collateral"])

_RECORD_FIELDS = (
    "collateral_type", "description", "reported_value", "verified_value", "currency",
    "valuation_date", "valuation_source", "ownership_status", "encumbrance_status",
    "encumbrance_amount", "lien_holder", "verification_status", "notes",
)


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Collateral requires persistence (database not configured).")
    return SessionLocal()


class CollateralCreate(BaseModel):
    collateral_type: str
    description: str = Field(..., min_length=1)
    reported_value: float
    verified_value: Optional[float] = None
    currency: str = Field(default="SAR", max_length=10)
    valuation_date: Optional[datetime] = None
    valuation_source: Optional[str] = Field(default=None, max_length=200)
    ownership_status: Optional[str] = Field(default=None, max_length=100)
    encumbrance_status: str = "UNKNOWN"
    encumbrance_amount: Optional[float] = None
    lien_holder: Optional[str] = Field(default=None, max_length=200)
    verification_status: str = "USER_REPORTED"
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _validate(self):
        try:
            validate_consistency(self.model_dump())
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        return self


class CollateralUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    collateral_type: Optional[str] = None
    description: Optional[str] = Field(default=None, min_length=1)
    reported_value: Optional[float] = None
    verified_value: Optional[float] = None
    currency: Optional[str] = Field(default=None, max_length=10)
    valuation_date: Optional[datetime] = None
    valuation_source: Optional[str] = Field(default=None, max_length=200)
    ownership_status: Optional[str] = Field(default=None, max_length=100)
    encumbrance_status: Optional[str] = None
    encumbrance_amount: Optional[float] = None
    lien_holder: Optional[str] = Field(default=None, max_length=200)
    verification_status: Optional[str] = None
    notes: Optional[str] = None


class CollateralOut(BaseModel):
    id: int
    study_id: int
    collateral_type: str
    description: str
    reported_value: float
    verified_value: Optional[float] = None
    currency: str
    valuation_date: Optional[datetime] = None
    valuation_source: Optional[str] = None
    ownership_status: Optional[str] = None
    encumbrance_status: str
    encumbrance_amount: Optional[float] = None
    lien_holder: Optional[str] = None
    verification_status: str
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class CollateralSummaryOut(BaseModel):
    record_count: int
    total_reported_value: float
    total_verified_value: float
    total_encumbered_value: float
    total_unencumbered_reported_value: float
    verified_record_count: int
    unverified_record_count: int
    unknown_encumbrance_count: int


def _row_to_dict(row) -> dict:
    return {field: getattr(row, field) for field in _RECORD_FIELDS}


def _get_or_404(db, models, study_id: int, collateral_id: int):
    row = db.get(models.CollateralItem, collateral_id)
    if row is None or row.study_id != study_id:
        raise HTTPException(status_code=404, detail="Collateral item not found")
    return row


@router.post("/", response_model=CollateralOut, status_code=201)
def create_collateral(study_id: int, data: CollateralCreate, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        row = models.CollateralItem(study_id=study_id, created_by=user.id, **data.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


@router.get("/", response_model=List[CollateralOut])
def list_collateral(study_id: int, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        rows = (
            db.query(models.CollateralItem)
            .filter(models.CollateralItem.study_id == study_id)
            .order_by(models.CollateralItem.id.asc())
            .all()
        )
        return rows
    finally:
        db.close()


@router.get("/summary", response_model=CollateralSummaryOut)
def get_collateral_summary(study_id: int, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        rows = db.query(models.CollateralItem).filter(models.CollateralItem.study_id == study_id).all()
        return summarize_collateral([_row_to_dict(row) for row in rows])
    finally:
        db.close()


@router.get("/{collateral_id}", response_model=CollateralOut)
def get_collateral(study_id: int, collateral_id: int, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        return _get_or_404(db, models, study_id, collateral_id)
    finally:
        db.close()


@router.patch("/{collateral_id}", response_model=CollateralOut)
def update_collateral(study_id: int, collateral_id: int, data: CollateralUpdate, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        row = _get_or_404(db, models, study_id, collateral_id)

        changes = data.model_dump(exclude_unset=True)
        merged = _row_to_dict(row)
        merged.update(changes)
        try:
            validate_consistency(merged)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        for field, value in changes.items():
            setattr(row, field, value)
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


@router.delete("/{collateral_id}", status_code=204)
def delete_collateral(study_id: int, collateral_id: int, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        row = _get_or_404(db, models, study_id, collateral_id)
        db.delete(row)
        db.commit()
        return None
    finally:
        db.close()
