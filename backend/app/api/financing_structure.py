"""
Financing Structure API (Phase 20: Wave 2 — Funding Intelligence Capstone).

Endpoints:
  GET /studies/{study_id}/financing-structure
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import UserOut, get_current_user
from app.api.collateral import _row_to_dict as collateral_row_to_dict
from app.api.company_financial_profile import _METRIC_FIELDS as PERIOD_METRIC_FIELDS
from app.db import DB_ENABLED, SessionLocal
from app.services.financing_structure import compute_financing_structure
from app.services.study_access import owned_study_or_error

router = APIRouter(prefix="/studies/{study_id}/financing-structure", tags=["financing-structure"])


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Financing structure requires database persistence.")
    return SessionLocal()


def _period_to_dict(row) -> dict:
    d = {"period": row.period, "source": row.source}
    for field in PERIOD_METRIC_FIELDS:
        d[field] = getattr(row, field)
    return d


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


class FinancingSourceOut(BaseModel):
    source_key: str
    name_ar: str
    name_en: str
    source_type: str
    amount: float
    percentage: float
    is_secured: bool
    program_slug: Optional[str] = None
    official_source_url: Optional[str] = None


class FinancingUseOut(BaseModel):
    category_key: str
    name_ar: str
    name_en: str
    amount: float
    percentage: float


class ProgramAllocationOut(BaseModel):
    program_id: int
    program_slug: str
    provider: str
    provider_ar: str
    program_name_ar: str
    program_name_en: str
    program_type: str
    match_status: str
    allocated_amount: Optional[float] = None
    allocation_status: Optional[str] = None
    term_months: Optional[int] = None
    grace_period_months: Optional[int] = None
    official_source_url: Optional[str] = None


class CreditEnhancementOut(BaseModel):
    program_id: int
    program_slug: str
    provider: str
    provider_ar: str
    program_name_ar: str
    program_name_en: str
    program_type: str
    match_status: str
    cash_contribution: float = 0.0
    role_ar: str
    role_en: str
    max_guarantee_amount: Optional[float] = None
    coverage_ratio: Optional[float] = None
    official_source_url: Optional[str] = None


class ConfirmedSourcesOut(BaseModel):
    owner_equity: float
    existing_debt: float
    total_confirmed: float
    coverage_percentage: float


class FinancingWarningOut(BaseModel):
    code: str
    severity: str
    title_ar: str
    title_en: str
    message_ar: str
    message_en: str


class NextActionOut(BaseModel):
    step_number: int
    title_ar: str
    title_en: str
    status: str
    description_ar: str
    description_en: str


class FinancingStructureOut(BaseModel):
    study_id: int
    project_name: str
    sector: str
    stage: str
    total_project_requirement: float
    owner_equity: float
    existing_debt: float
    total_confirmed_sources: Optional[float] = None
    confirmed_sources: Optional[ConfirmedSourcesOut] = None
    initial_funding_gap: Optional[float] = None
    confirmed_funding_gap: Optional[float] = None
    potential_residual_gap: Optional[float] = None
    potential_program_capacity: Optional[float] = None
    allocated_program_debt: float
    internal_screening_debt_capacity: Optional[float] = None
    safe_debt_capacity: float
    capacity_status: str
    total_identified_sources: float
    residual_gap: float
    surplus: float
    equity_percentage: float
    debt_percentage: float
    debt_to_equity_ratio: Optional[float] = None
    collateral_coverage_ratio: float
    sources: List[FinancingSourceOut]
    uses: List[FinancingUseOut]
    program_allocations: List[ProgramAllocationOut]
    credit_enhancements: Optional[List[CreditEnhancementOut]] = []
    warnings: List[FinancingWarningOut]
    next_actions: List[NextActionOut]
    disclaimer_ar: str
    disclaimer_en: str
    version: str


@router.get("/", response_model=FinancingStructureOut)
@router.get("", response_model=FinancingStructureOut, include_in_schema=False)
def get_financing_structure(
    study_id: int,
    period: Optional[str] = None,
    user: UserOut = Depends(get_current_user),
):
    from app import models

    db = _require_db()
    try:
        study = owned_study_or_error(db, models, study_id, user)
        project = db.get(models.Project, study.project_id)

        capex_val = _active_assumption_value(db, models, study_id, "capex")
        owner_val = _active_assumption_value(db, models, study_id, "owner_contribution")
        facilities_val = _active_assumption_value(db, models, study_id, "existing_available_facilities")

        period_rows = (
            db.query(models.CompanyFinancialPeriod)
            .filter(models.CompanyFinancialPeriod.study_id == study_id)
            .order_by(models.CompanyFinancialPeriod.period.asc())
            .all()
        )
        financial_period_dict = None
        if period_rows:
            if period is not None:
                matches = [r for r in period_rows if r.period == period]
                if matches:
                    financial_period_dict = _period_to_dict(matches[0])
            else:
                financial_period_dict = _period_to_dict(period_rows[-1])

        collateral_rows = (
            db.query(models.CollateralItem)
            .filter(models.CollateralItem.study_id == study_id)
            .order_by(models.CollateralItem.id.asc())
            .all()
        )
        collateral_dicts = [collateral_row_to_dict(c) for c in collateral_rows]

        result = compute_financing_structure(
            db,
            study=study,
            project=project,
            owner_contribution=owner_val,
            capex_assumption=capex_val,
            existing_facilities=facilities_val,
            financial_period_dict=financial_period_dict,
            collateral_dicts=collateral_dicts,
        )
        return result
    finally:
        db.close()
