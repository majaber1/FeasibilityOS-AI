"""Verified Funding Program Registry API (Wave 2: Funding Intelligence).

Public / authenticated read endpoints to explore official Saudi funding programs,
inspect verifiable program terms, and trace rule provenance to official sources.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import funding_programs as fp_service

router = APIRouter(prefix="/funding-programs", tags=["funding-programs"])


# ==============================================================================
# SCHEMAS
# ==============================================================================

class FundingProgramRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    program_id: int
    rule_key: str
    rule_type: str
    structured_value: Dict[str, Any]
    description_ar: Optional[str] = None
    description_en: Optional[str] = None
    source_url: str
    source_reference: Optional[str] = None
    source_authority: str
    verified_at: datetime
    rule_version: str
    is_active: bool


class FundingProgramOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    provider: str
    provider_ar: str
    program_name_ar: str
    program_name_en: str
    description_ar: Optional[str] = None
    description_en: Optional[str] = None
    program_type: str
    target_business_stage: str
    target_sectors: List[str]
    financing_min: Optional[float] = None
    financing_max: Optional[float] = None
    currency: str
    term_months: Optional[int] = None
    grace_period_months: Optional[int] = None
    owner_contribution_rule: Optional[Dict[str, Any]] = None
    collateral_rule: Optional[Dict[str, Any]] = None
    guarantee_rule: Optional[Dict[str, Any]] = None
    revenue_rule: Optional[Dict[str, Any]] = None
    business_age_rule: Optional[Dict[str, Any]] = None
    other_eligibility_rules: Optional[List[Any]] = None
    official_source_url: str
    source_type: str
    source_owner: str
    first_seen_at: datetime
    last_checked_at: datetime
    last_verified_at: datetime
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    verification_status: str
    rule_version: str
    rules: List[FundingProgramRuleOut] = []


class RegistrySummaryOut(BaseModel):
    total_programs: int
    verified_current_count: int
    providers_breakdown: Dict[str, int]
    program_types_breakdown: Dict[str, int]
    all_providers: List[str]


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get("/", response_model=List[FundingProgramOut])
def list_programs(
    provider: Optional[str] = Query(None, description="Filter by provider name"),
    program_type: Optional[str] = Query(None, description="DIRECT_LOAN | GUARANTEE | CO_FINANCING | WORKING_CAPITAL"),
    verification_status: Optional[str] = Query(None, description="VERIFIED_CURRENT | VERIFIED_PARTIAL"),
    target_business_stage: Optional[str] = Query(None, description="STARTUP | EXISTING | EXPANSION | ALL"),
    sector: Optional[str] = Query(None, description="Filter by target sector"),
    db: Session = Depends(get_db),
):
    """List verified Saudi funding programs from official development institutions."""
    # Ensure seed catalog is present in the database
    fp_service.ensure_seed_programs(db)

    return fp_service.list_funding_programs(
        db,
        provider=provider,
        program_type=program_type,
        verification_status=verification_status,
        target_business_stage=target_business_stage,
        sector=sector,
    )


@router.get("/summary", response_model=RegistrySummaryOut)
def get_registry_summary(db: Session = Depends(get_db)):
    """Return overview metrics and provider breakdowns for the verified funding registry."""
    fp_service.ensure_seed_programs(db)
    return fp_service.summarize_registry(db)


@router.get("/{program_id}", response_model=FundingProgramOut)
def get_program_details(program_id: int, db: Session = Depends(get_db)):
    """Retrieve detailed program record along with all verified rule provenance evidence."""
    fp_service.ensure_seed_programs(db)
    prog = fp_service.get_funding_program(db, program_id)
    if not prog:
        raise HTTPException(status_code=404, detail="Funding program not found.")
    return prog
