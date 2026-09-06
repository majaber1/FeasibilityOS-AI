"""
Business Profile API: structured, reusable business facts for a Study.

One profile per study. PUT upserts (creates on first call, partially updates
on later calls) so both the feasibility flow and the funding flow can read
and extend the same record without ever re-asking for data the user already
gave. Ownership follows the study's parent project owner (see
app.services.study_access). Requires persistence (DATABASE_URL).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db import DB_ENABLED, SessionLocal
from app.api.auth import UserOut, get_current_user
from app.services.study_access import owned_study_or_error

router = APIRouter(prefix="/studies/{study_id}/business-profile", tags=["business-profile"])


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Business profile requires persistence (database not configured).")
    return SessionLocal()


class BusinessProfileIn(BaseModel):
    model_config = {"extra": "forbid"}

    business_activity: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=100)
    region: Optional[str] = Field(default=None, max_length=100)
    customer_segment: Optional[str] = Field(default=None, max_length=200)
    capacity_value: Optional[float] = None
    capacity_unit: Optional[str] = Field(default=None, max_length=50)
    legal_entity_type: Optional[str] = Field(default=None, max_length=50)
    ownership_notes: Optional[str] = None
    is_existing_business: Optional[bool] = None
    company_age_years: Optional[float] = Field(default=None, ge=0)
    current_revenue: Optional[float] = Field(default=None, ge=0)


class BusinessProfileOut(BaseModel):
    study_id: int
    business_activity: Optional[str] = None
    description: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    customer_segment: Optional[str] = None
    capacity_value: Optional[float] = None
    capacity_unit: Optional[str] = None
    legal_entity_type: Optional[str] = None
    ownership_notes: Optional[str] = None
    is_existing_business: bool
    company_age_years: Optional[float] = None
    current_revenue: Optional[float] = None

    model_config = {"from_attributes": True}


@router.get("/", response_model=BusinessProfileOut)
def get_business_profile(study_id: int, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        profile = db.query(models.BusinessProfile).filter_by(study_id=study_id).first()
        if profile is None:
            # Missing profile is a valid empty state, not a navigation error.
            return BusinessProfileOut(study_id=study_id, is_existing_business=False)
        return profile
    finally:
        db.close()


@router.put("/", response_model=BusinessProfileOut)
def upsert_business_profile(study_id: int, data: BusinessProfileIn, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        profile = db.query(models.BusinessProfile).filter_by(study_id=study_id).first()
        changes = data.model_dump(exclude_unset=True)
        if profile is None:
            profile = models.BusinessProfile(study_id=study_id, **changes)
            db.add(profile)
        else:
            for field, value in changes.items():
                setattr(profile, field, value)
        db.commit()
        db.refresh(profile)
        return profile
    finally:
        db.close()
