"""
Funding Gap API (Phase 14): computed live from data the study already has
-- never re-asks for information stored elsewhere. See
app.services.funding_gap for the calculation and which assumption keys it
reads.

Stateless by design: unlike Scenarios/Decisions (which freeze a snapshot
because the calculation is comparatively expensive and history matters),
funding gap is a cheap, always-current read over Project + StudyAssumption,
so it is not persisted separately here. Ownership follows the study's
parent project owner. Requires persistence (DATABASE_URL).
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import DB_ENABLED, SessionLocal
from app.api.auth import UserOut, get_current_user
from app.services.study_access import owned_study_or_error
from app.services.funding_gap import (
    EXISTING_FACILITIES_KEY,
    OWNER_CONTRIBUTION_KEY,
    REQUIREMENT_ASSUMPTION_KEY,
    compute_funding_gap,
)

router = APIRouter(prefix="/studies/{study_id}/funding-gap", tags=["funding-gap"])


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Funding gap requires persistence (database not configured).")
    return SessionLocal()


class FundingGapOut(BaseModel):
    study_id: int
    total_project_requirement: float
    requirement_source: str
    owner_available_capital: float
    owner_available_capital_status: str
    existing_available_facilities: float
    existing_available_facilities_status: str
    funding_gap: float
    missing_inputs: List[str]


def _active_assumption_value(db, models, study_id: int, key: str) -> Optional[float]:
    row = (
        db.query(models.StudyAssumption)
        .filter(
            models.StudyAssumption.study_id == study_id,
            models.StudyAssumption.is_active.is_(True),
            models.StudyAssumption.key == key,
        )
        .first()
    )
    return row.value_number if row else None


@router.get("/", response_model=FundingGapOut)
def get_funding_gap(study_id: int, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        study = owned_study_or_error(db, models, study_id, user)
        project = db.get(models.Project, study.project_id)

        result = compute_funding_gap(
            capex_assumption=_active_assumption_value(db, models, study_id, REQUIREMENT_ASSUMPTION_KEY),
            project_investment=float(project.investment) if project else 0.0,
            owner_contribution=_active_assumption_value(db, models, study_id, OWNER_CONTRIBUTION_KEY),
            existing_facilities=_active_assumption_value(db, models, study_id, EXISTING_FACILITIES_KEY),
        )
        return FundingGapOut(study_id=study_id, **result)
    finally:
        db.close()
