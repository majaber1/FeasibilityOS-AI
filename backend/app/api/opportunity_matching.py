"""API router for Opportunity Fit & Matching (Wave 3B).

Endpoints:
- POST /fit-profile : Save or update user fit profile.
- GET  /fit-profile : Fetch existing user fit profile.
- POST /fit-evaluate: Run deterministic matching engine against actionable opportunities.
- GET  /fit-results : Retrieve results from latest match run.
- GET  /fit-results/{opp_id}: Retrieve detailed match breakdown for a specific opportunity.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import db, models
from app.api.auth import get_current_user
from app.services.opportunity_matching import (
    execute_match_run,
    get_latest_match_run,
    resolve_current_match_state,
    STATE_NOT_EVALUATED,
)
from app.services.opportunities import (
    STATUS_VERIFIED_PARTIAL,
    STATUS_VERIFIED_CURRENT,
)

router = APIRouter(prefix="/api/v1/opportunities", tags=["Opportunity Fit & Matching"])


class ConstraintStrength(str, Enum):
    HARD = "HARD"
    PREFERENCE = "PREFERENCE"


class FitProfileIn(BaseModel):
    available_capital: Optional[float] = Field(None, ge=0)
    capital_constraint_type: ConstraintStrength = ConstraintStrength.HARD
    preferred_sectors: List[str] = []
    excluded_sectors: List[str] = []
    preferred_opportunity_types: List[str] = []
    opportunity_type_constraint: ConstraintStrength = ConstraintStrength.PREFERENCE
    target_region: Optional[str] = None
    target_city: Optional[str] = None
    preferred_business_models: List[str] = []
    target_customer: Optional[str] = None
    experience_sectors: List[str] = []
    notes: Optional[str] = None


@router.post("/fit-profile", status_code=status.HTTP_200_OK)
def save_or_update_fit_profile(
    data: FitProfileIn,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Saves or updates the authenticated user's persistent Opportunity Fit Profile."""
    profile = (
        db_session.query(models.OpportunityFitProfile)
        .filter(models.OpportunityFitProfile.user_id == user.id)
        .first()
    )

    if profile:
        profile.available_capital = data.available_capital
        profile.capital_constraint_type = data.capital_constraint_type.value
        profile.preferred_sectors = data.preferred_sectors
        profile.excluded_sectors = data.excluded_sectors
        profile.preferred_opportunity_types = data.preferred_opportunity_types
        profile.opportunity_type_constraint = data.opportunity_type_constraint.value
        profile.target_region = data.target_region
        profile.target_city = data.target_city
        profile.preferred_business_models = data.preferred_business_models
        profile.target_customer = data.target_customer
        profile.experience_sectors = data.experience_sectors
        profile.notes = data.notes
        profile.version += 1
    else:
        profile = models.OpportunityFitProfile(
            user_id=user.id,
            available_capital=data.available_capital,
            capital_constraint_type=data.capital_constraint_type.value,
            preferred_sectors=data.preferred_sectors,
            excluded_sectors=data.excluded_sectors,
            preferred_opportunity_types=data.preferred_opportunity_types,
            opportunity_type_constraint=data.opportunity_type_constraint.value,
            target_region=data.target_region,
            target_city=data.target_city,
            preferred_business_models=data.preferred_business_models,
            target_customer=data.target_customer,
            experience_sectors=data.experience_sectors,
            notes=data.notes,
            version=1,
            is_active=True,
        )
        db_session.add(profile)

    db_session.commit()
    db_session.refresh(profile)

    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "available_capital": profile.available_capital,
        "capital_constraint_type": profile.capital_constraint_type,
        "preferred_sectors": profile.preferred_sectors,
        "excluded_sectors": profile.excluded_sectors,
        "preferred_opportunity_types": profile.preferred_opportunity_types,
        "opportunity_type_constraint": profile.opportunity_type_constraint,
        "target_region": profile.target_region,
        "target_city": profile.target_city,
        "preferred_business_models": profile.preferred_business_models,
        "target_customer": profile.target_customer,
        "experience_sectors": profile.experience_sectors,
        "notes": profile.notes,
        "version": profile.version,
    }


@router.get("/fit-profile", status_code=status.HTTP_200_OK)
def get_fit_profile(
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Retrieves the authenticated user's current fit profile."""
    profile = (
        db_session.query(models.OpportunityFitProfile)
        .filter(models.OpportunityFitProfile.user_id == user.id)
        .first()
    )
    if not profile:
        return None

    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "available_capital": profile.available_capital,
        "capital_constraint_type": profile.capital_constraint_type,
        "preferred_sectors": profile.preferred_sectors or [],
        "excluded_sectors": profile.excluded_sectors or [],
        "preferred_opportunity_types": profile.preferred_opportunity_types or [],
        "opportunity_type_constraint": profile.opportunity_type_constraint,
        "target_region": profile.target_region,
        "target_city": profile.target_city,
        "preferred_business_models": profile.preferred_business_models or [],
        "target_customer": profile.target_customer,
        "experience_sectors": profile.experience_sectors or [],
        "notes": profile.notes,
        "version": profile.version,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


@router.post("/fit-evaluate", status_code=status.HTTP_200_OK)
def run_evaluation(
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Executes the deterministic matching engine against all actionable opportunities."""
    profile = (
        db_session.query(models.OpportunityFitProfile)
        .filter(models.OpportunityFitProfile.user_id == user.id)
        .first()
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="يرجى إدخال وتحديد تفضيلات وقيود المستثمر أولاً (Fit Profile required).",
        )

    match_run = execute_match_run(db=db_session, user=user, fit_profile=profile)

    return format_match_run_response(match_run, db_session)


@router.get("/fit-results", status_code=status.HTTP_200_OK)
def get_fit_results(
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Returns the latest match results for the current user."""
    match_run = get_latest_match_run(db=db_session, user_id=user.id)
    if not match_run:
        return None

    return format_match_run_response(match_run, db_session)


@router.get("/fit-results/history", status_code=status.HTTP_200_OK)
def get_fit_results_history(
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Returns past match runs history for the current user."""
    runs = (
        db_session.query(models.OpportunityMatchRun)
        .filter(models.OpportunityMatchRun.user_id == user.id)
        .order_by(models.OpportunityMatchRun.id.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "id": r.id,
            "evaluated_at": r.evaluated_at.isoformat() if r.evaluated_at else None,
            "calculation_version": r.calculation_version,
            "fit_profile_version": r.fit_profile_version,
            "fit_profile_snapshot": r.fit_profile_snapshot,
            "results_count": len(r.results),
        }
        for r in runs
    ]


@router.get("/fit-results/{opp_id}", status_code=status.HTTP_200_OK)
def get_single_fit_result(
    opp_id: int,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Returns detailed match criteria for a specific opportunity in the latest match run."""
    match_run = get_latest_match_run(db=db_session, user_id=user.id)
    if not match_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="لا يوجد تقييم سابق متاح")

    res = (
        db_session.query(models.OpportunityMatchResult)
        .filter(
            models.OpportunityMatchResult.match_run_id == match_run.id,
            models.OpportunityMatchResult.opportunity_id == opp_id,
        )
        .first()
    )
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="لم يتم العثور على نتيجة تقييم لهذه الفرصة")

    opp = res.opportunity
    current_state, requires_re_eval, stale_reason = resolve_current_match_state(res, opp)
    summary_reason = stale_reason if requires_re_eval else res.summary_reason

    return {
        "result_id": res.id,
        "match_run_id": match_run.id,
        "opportunity_id": opp.id,
        "slug": opp.slug,
        "title_ar": opp.title_ar,
        "title_en": opp.title_en,
        "brand_name": opp.brand_name,
        "sector": opp.sector,
        "opportunity_type": opp.opportunity_type,
        "match_state": current_state,
        "original_match_state": res.match_state,
        "is_version_stale": requires_re_eval,
        "requires_re_evaluation": requires_re_eval,
        "summary_reason": summary_reason,
        "missing_information": res.missing_information,
        "criteria_evaluations": res.criteria_evaluations,
        "opportunity_version_at_eval": res.opportunity_version,
        "current_data_version": opp.data_version,
        "current_verification_status": opp.verification_status,
        "evaluated_at": match_run.evaluated_at.isoformat() if match_run.evaluated_at else None,
    }


def format_match_run_response(match_run: models.OpportunityMatchRun, db_session: Session) -> Dict[str, Any]:
    """Helper to format match run and attached opportunity items, checking version freshness."""
    results_out = []
    for r in match_run.results:
        opp = r.opportunity
        current_state, requires_re_eval, stale_reason = resolve_current_match_state(r, opp)
        current_reason = stale_reason if requires_re_eval else r.summary_reason

        results_out.append({
            "result_id": r.id,
            "opportunity_id": opp.id,
            "slug": opp.slug,
            "title_ar": opp.title_ar,
            "title_en": opp.title_en,
            "brand_name": opp.brand_name,
            "sector": opp.sector,
            "opportunity_type": opp.opportunity_type,
            "investment_min": opp.investment_min,
            "investment_max": opp.investment_max,
            "franchise_fee": opp.franchise_fee,
            "geography": opp.geography,
            "official_source_url": opp.official_source_url,
            "verification_status": opp.verification_status,
            "verification_status_at_eval": r.verification_status_at_eval,
            "is_active": opp.is_active,
            "match_state": current_state,
            "original_match_state": r.match_state,
            "is_version_stale": requires_re_eval,
            "requires_re_evaluation": requires_re_eval,
            "summary_reason": current_reason,
            "missing_information": r.missing_information,
            "criteria_evaluations": r.criteria_evaluations,
            "opportunity_version_at_eval": r.opportunity_version,
            "current_data_version": opp.data_version,
        })

    return {
        "id": match_run.id,
        "evaluated_at": match_run.evaluated_at.isoformat() if match_run.evaluated_at else None,
        "calculation_version": match_run.calculation_version,
        "fit_profile_version": match_run.fit_profile_version,
        "fit_profile_snapshot": match_run.fit_profile_snapshot,
        "results_count": len(results_out),
        "results": results_out,
    }
