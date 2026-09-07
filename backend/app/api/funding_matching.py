"""
Funding Matching API (Phase 19): Deterministic matching of a study against
verified Saudi funding programs, with rule-by-rule provenance.

Endpoints:
  GET /studies/{study_id}/funding-matches      – full matching summary
  GET /studies/{study_id}/funding-matches/{pid} – single program detail
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import UserOut, get_current_user
from app.api.collateral import _row_to_dict as collateral_row_to_dict
from app.api.company_financial_profile import _METRIC_FIELDS as PERIOD_METRIC_FIELDS
from app.db import DB_ENABLED, SessionLocal
from app.services.funding_matching import evaluate_study_funding_matches, evaluate_single_program_match
from app.services.study_access import owned_study_or_error

router = APIRouter(prefix="/studies/{study_id}/funding-matches", tags=["funding-matching"])


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Funding matching requires persistence (database not configured).")
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


class RuleEvaluationOut(BaseModel):
    rule_key: str
    rule_name_ar: str
    rule_name_en: str
    rule_type: str
    required_value: Any
    actual_value: Any
    result: str
    notes_ar: str
    notes_en: str
    source_url: str
    source_authority: str
    rule_version: str


class ProgramMatchOut(BaseModel):
    program_id: int
    program_slug: str
    provider: str
    provider_ar: str
    program_name_ar: str
    program_name_en: str
    program_type: str
    target_business_stage: str
    financing_min: Optional[float] = None
    financing_max: Optional[float] = None
    term_months: Optional[int] = None
    grace_period_months: Optional[int] = None
    official_source_url: str
    source_owner: str
    rule_version: str
    last_verified_at: Optional[str] = None
    overall_match_status: str
    status_reason_ar: str
    status_reason_en: str
    passed_rules: List[str]
    failed_rules: List[str]
    unknown_rules: List[str]
    missing_information: List[str]
    rule_evaluations: List[RuleEvaluationOut]


class StudyProfileSnapshot(BaseModel):
    project_name: str = ""
    sector: str = ""
    stage: str = ""
    total_project_requirement: float = 0.0
    owner_contribution: float = 0.0
    funding_gap: float = 0.0
    available_collateral: float = 0.0
    collateral_coverage_ratio: float = 0.0
    annual_revenue: Optional[float] = None
    safe_debt_capacity: float = 0.0
    financial_health_score: Optional[str] = None


class FundingMatchesOut(BaseModel):
    study_id: int
    study_profile_snapshot: StudyProfileSnapshot
    total_programs_evaluated: int
    matches_count: int
    possible_matches_count: int
    needs_information_count: int
    not_matched_count: int
    matches: List[ProgramMatchOut]
    disclaimer_ar: str
    disclaimer_en: str
    calculation_version: str


def _gather_study_data(db, models, study_id: int, user: UserOut, period: Optional[str] = None):
    """Shared data-fetching logic for matching endpoints."""
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

    return study, project, capex_val, owner_val, facilities_val, financial_period_dict, collateral_dicts


@router.get("/", response_model=FundingMatchesOut)
@router.get("", response_model=FundingMatchesOut, include_in_schema=False)
def get_funding_matches(
    study_id: int,
    period: Optional[str] = None,
    user: UserOut = Depends(get_current_user),
):
    from app import models
    from sqlalchemy.orm import joinedload

    db = _require_db()
    try:
        study, project, capex_val, owner_val, facilities_val, fp_dict, cd = \
            _gather_study_data(db, models, study_id, user, period)

        result = evaluate_study_funding_matches(
            db,
            study=study,
            project=project,
            owner_contribution=owner_val,
            capex_assumption=capex_val,
            existing_facilities=facilities_val,
            financial_period_dict=fp_dict,
            collateral_dicts=cd,
        )
        return result
    finally:
        db.close()


@router.get("/{program_id}", response_model=ProgramMatchOut)
def get_single_program_match(
    study_id: int,
    program_id: int,
    period: Optional[str] = None,
    user: UserOut = Depends(get_current_user),
):
    from app import models
    from sqlalchemy.orm import joinedload
    from app.services.funding_gap import compute_funding_gap
    from app.services.borrowing_capacity import estimate_borrowing_capacity

    db = _require_db()
    try:
        study, project, capex_val, owner_val, facilities_val, fp_dict, cd = \
            _gather_study_data(db, models, study_id, user, period)

        program = (
            db.query(models.FundingProgram)
            .options(joinedload(models.FundingProgram.rules))
            .filter(models.FundingProgram.id == program_id)
            .first()
        )
        if not program:
            raise HTTPException(status_code=404, detail=f"Funding program {program_id} not found.")

        project_investment = float(project.investment or 0.0) if project else 0.0
        gap_res = compute_funding_gap(
            capex_assumption=capex_val,
            project_investment=project_investment,
            owner_contribution=owner_val,
            existing_facilities=facilities_val,
        )
        total_cost = gap_res["total_project_requirement"]
        gap_amount = gap_res["funding_gap"]
        owner_cap = gap_res["owner_available_capital"]

        verified = [c for c in cd if c.get("verification_status") == "VERIFIED"]
        total_cv = sum(float(c.get("market_value", 0.0)) for c in verified)
        pledged = sum(float(c.get("pledged_amount", 0.0)) for c in verified)
        avail_c = max(0.0, total_cv - pledged)
        cov_ratio = (avail_c / gap_amount) if gap_amount > 0 else 0.0

        annual_rev = None
        safe_cap = 0.0
        if fp_dict:
            annual_rev = float(fp_dict.get("revenue") or 0.0)
            ebitda = float(fp_dict.get("ebitda") or 0.0)
            existing_debt = float(fp_dict.get("total_debt") or fp_dict.get("long_term_debt") or 0.0)
            debt_service = float(fp_dict.get("debt_service") or 0.0)
            cap_eval = estimate_borrowing_capacity(
                ebitda=ebitda if ebitda else None,
                existing_debt=existing_debt if existing_debt else None,
                annual_debt_service=debt_service if debt_service else None,
            )
            safe_cap = float(cap_eval.get("base_capacity") or 0.0) if cap_eval.get("status") == "CALCULATED" else 0.0

        sector = project.industry if project else "general"
        stage = project.stage if project else "startup"

        result = evaluate_single_program_match(
            program=program, study_id=study.id, study_sector=sector,
            study_stage=stage, project_cost=total_cost, owner_contribution=owner_cap,
            funding_gap=gap_amount, current_annual_revenue=annual_rev,
            available_collateral_value=avail_c, collateral_coverage_ratio=cov_ratio,
            safe_debt_capacity=safe_cap,
        )
        return result
    finally:
        db.close()
