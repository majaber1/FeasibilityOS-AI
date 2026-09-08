"""
Funding Readiness API (Phase 17): Live deterministic screening evaluation
of whether a study/company is prepared to approach debt funding providers.

Stateless live read over existing Study, CompanyFinancialPeriod, StudyAssumption,
and CollateralItem entities. Does NOT fabricate lender underwriting, approval,
or arbitrary percentage scores. Ownership follows the study's parent project
owner. Requires persistence (DATABASE_URL).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import UserOut, get_current_user
from app.api.collateral import _row_to_dict as collateral_row_to_dict
from app.api.company_financial_profile import _METRIC_FIELDS as PERIOD_METRIC_FIELDS
from app.db import DB_ENABLED, SessionLocal
from app.services.funding_readiness import evaluate_funding_readiness
from app.services.study_access import owned_study_or_error

router = APIRouter(prefix="/studies/{study_id}/funding-readiness", tags=["funding-readiness"])


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Funding readiness requires persistence (database not configured).")
    return SessionLocal()


class ActionableStepOut(BaseModel):
    key: str
    title_en: str
    title_ar: str
    action_target: str


class FundingReadinessOut(BaseModel):
    study_id: int
    status: str
    summary_en: str
    summary_ar: str
    positive_factors: List[str]
    positive_factors_ar: List[str]
    blocking_factors: List[str]
    blocking_factors_ar: List[str]
    missing_information: List[str]
    missing_information_ar: List[str]
    warnings: List[str]
    warnings_ar: List[str]
    actionable_steps: List[ActionableStepOut]
    financial_health_snapshot: Optional[Dict[str, Any]] = None
    funding_gap_snapshot: Optional[Dict[str, Any]] = None
    borrowing_capacity_snapshot: Optional[Dict[str, Any]] = None
    collateral_snapshot: Optional[Dict[str, Any]] = None
    documents_status: str = "NOT_EVALUATED"
    assumptions_used: Dict[str, Any]
    calculation_version: str


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


def _period_to_dict(row) -> dict:
    d = {"period": row.period, "source": row.source}
    for field in PERIOD_METRIC_FIELDS:
        d[field] = getattr(row, field)
    return d


@router.get("/", response_model=FundingReadinessOut)
@router.get("", response_model=FundingReadinessOut, include_in_schema=False)
def get_funding_readiness(
    study_id: int,
    period: Optional[str] = None,
    user: UserOut = Depends(get_current_user),
):
    from app import models

    db = _require_db()
    try:
        study = owned_study_or_error(db, models, study_id, user)
        project = db.get(models.Project, study.project_id)
        project_investment = float(project.investment or 0.0) if project else 0.0

        # Read active study assumptions
        capex_val = _active_assumption_value(db, models, study_id, "capex")
        owner_val = _active_assumption_value(db, models, study_id, "owner_contribution")
        facilities_val = _active_assumption_value(db, models, study_id, "existing_available_facilities")

        # Read financial periods
        period_rows = (
            db.query(models.CompanyFinancialPeriod)
            .filter(models.CompanyFinancialPeriod.study_id == study_id)
            .order_by(models.CompanyFinancialPeriod.period.asc())
            .all()
        )

        financial_period_dict = None
        prior_period_dict = None

        if period_rows:
            if period is not None:
                matches = [r for r in period_rows if r.period == period]
                if matches:
                    target_row = matches[0]
                    target_idx = period_rows.index(target_row)
                    financial_period_dict = _period_to_dict(target_row)
                    if target_idx > 0:
                        prior_period_dict = _period_to_dict(period_rows[target_idx - 1])
                else:
                    # Specific period requested but not found -> treat as missing
                    financial_period_dict = None
            else:
                target_row = period_rows[-1]
                financial_period_dict = _period_to_dict(target_row)
                if len(period_rows) > 1:
                    prior_period_dict = _period_to_dict(period_rows[-2])

        # Read collateral items
        collateral_rows = (
            db.query(models.CollateralItem)
            .filter(models.CollateralItem.study_id == study_id)
            .order_by(models.CollateralItem.id.asc())
            .all()
        )
        collateral_dicts = [collateral_row_to_dict(c) for c in collateral_rows]

        # Evaluate readiness
        result = evaluate_funding_readiness(
            study_id=study_id,
            project_investment=project_investment,
            capex_assumption=capex_val,
            owner_contribution=owner_val,
            existing_facilities=facilities_val,
            financial_period=financial_period_dict,
            prior_period=prior_period_dict,
            collateral_records=collateral_dicts,
        )
        return result
    finally:
        db.close()
