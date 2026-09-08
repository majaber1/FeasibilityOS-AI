"""Verified Opportunity & Franchise Registry API (Wave 3: Source Integrity Hardened).

Endpoints:
  GET    /api/v1/opportunities/                     List with verified filters & provenance
  GET    /api/v1/opportunities/compare             Factual side-by-side comparison
  GET    /api/v1/opportunities/{id}                 Detail with facts breakdown & version history
  POST   /api/v1/opportunities/{id}/create-study   Create persistent Study with source lineage
  POST   /api/v1/opportunities/admin/ingest        Explicit admin catalog ingestion/reconciliation
  POST   /api/v1/opportunities/                     Admin create verified opportunity
  PATCH  /api/v1/opportunities/{id}                 Admin update verified opportunity with versioning
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.auth import UserOut, get_current_user, require_roles
from app.db import DB_ENABLED, SessionLocal
from app.services.opportunities import (
    compare_verified_opportunities,
    create_study_from_opportunity,
    get_verified_opportunity,
    list_verified_opportunities,
    seed_verified_opportunities,
    validate_evidence_and_status,
    STATUS_UNVERIFIED,
    STATUS_VERIFIED_PARTIAL,
    STATUS_VERIFIED_CURRENT,
)
from app import models

router = APIRouter(prefix="/api/v1/opportunities", tags=["verified-opportunities"])


def _db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Verified Opportunity Registry requires database persistence.")
    return SessionLocal()


class VerifiedOpportunityOut(BaseModel):
    id: int
    slug: str
    title_ar: str
    title_en: str
    opportunity_type: str
    sector: str
    subsector: Optional[str] = None
    business_model: Optional[str] = None
    target_customer: Optional[str] = None
    geography: str
    city: Optional[str] = None
    region: Optional[str] = None
    investment_min: Optional[float] = None
    investment_max: Optional[float] = None
    franchise_fee: Optional[float] = None
    royalty_model: Optional[str] = None
    required_space: Optional[str] = None
    business_stage: Optional[str] = None
    description_ar: Optional[str] = None
    description_en: Optional[str] = None
    brand_name: Optional[str] = None
    official_source_url: str
    source_owner: str
    source_type: str
    source_evidence: Optional[Dict[str, Any]] = None
    first_seen_at: datetime
    last_checked_at: datetime
    last_verified_at: datetime
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    source_last_modified: Optional[str] = None
    verification_status: str
    data_version: str
    is_active: bool
    facts_breakdown: Optional[Dict[str, Any]] = None
    field_provenance: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class OpportunityVersionHistoryOut(BaseModel):
    id: int
    data_version: str
    snapshot: Dict[str, Any]
    changed_by: Optional[int] = None
    change_reason: str
    created_at: datetime

    model_config = {"from_attributes": True}


class VerifiedOpportunityDetailOut(VerifiedOpportunityOut):
    version_history: List[OpportunityVersionHistoryOut] = []


class CreateStudyFromOpportunityIn(BaseModel):
    custom_budget: Optional[float] = Field(default=None, ge=0)
    study_title: Optional[str] = Field(default=None, max_length=255)
    match_result_id: Optional[int] = Field(default=None)


class CreateStudyFromOpportunityOut(BaseModel):
    project_id: int
    study_id: int
    title: str
    opportunity_id: int
    lineage: Dict[str, Any]
    fit_snapshot: Optional[Dict[str, Any]] = None


class OpportunityCreateIn(BaseModel):
    slug: str = Field(..., min_length=2, max_length=120)
    title_ar: str = Field(..., min_length=2, max_length=255)
    title_en: str = Field(..., min_length=2, max_length=255)
    opportunity_type: str = Field(..., pattern="^(BUSINESS_OPPORTUNITY|FRANCHISE)$")
    sector: str = Field(..., min_length=2, max_length=100)
    subsector: Optional[str] = None
    business_model: Optional[str] = None
    target_customer: Optional[str] = None
    geography: str = Field(default="KSA_NATIONAL", max_length=100)
    city: Optional[str] = None
    region: Optional[str] = None
    investment_min: Optional[float] = None
    investment_max: Optional[float] = None
    franchise_fee: Optional[float] = None
    royalty_model: Optional[str] = None
    required_space: Optional[str] = None
    business_stage: Optional[str] = "STARTUP"
    description_ar: Optional[str] = None
    description_en: Optional[str] = None
    brand_name: Optional[str] = None
    official_source_url: str = Field(..., min_length=5, max_length=500)
    source_owner: str = Field(..., min_length=2, max_length=200)
    source_type: str = Field(default="OFFICIAL_GOVERNMENT")
    source_evidence: Optional[Dict[str, Any]] = None
    verification_status: str = Field(
        default=STATUS_UNVERIFIED,
        pattern="^(UNVERIFIED|VERIFIED_PARTIAL|VERIFIED_CURRENT|STALE|CHANGED|DISCONTINUED)$",
    )
    facts_breakdown: Optional[Dict[str, Any]] = None
    field_provenance: Optional[Dict[str, Any]] = None


class OpportunityUpdateIn(BaseModel):
    title_ar: Optional[str] = None
    title_en: Optional[str] = None
    sector: Optional[str] = None
    subsector: Optional[str] = None
    business_model: Optional[str] = None
    target_customer: Optional[str] = None
    geography: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    investment_min: Optional[float] = None
    investment_max: Optional[float] = None
    franchise_fee: Optional[float] = None
    royalty_model: Optional[str] = None
    required_space: Optional[str] = None
    description_ar: Optional[str] = None
    description_en: Optional[str] = None
    brand_name: Optional[str] = None
    official_source_url: Optional[str] = None
    source_owner: Optional[str] = None
    verification_status: Optional[str] = None
    facts_breakdown: Optional[Dict[str, Any]] = None
    field_provenance: Optional[Dict[str, Any]] = None
    change_reason: str = Field(..., min_length=3, max_length=255)


@router.get("/", response_model=List[VerifiedOpportunityOut])
def list_opportunities(
    type: Optional[str] = Query(None, description="BUSINESS_OPPORTUNITY | FRANCHISE"),
    sector: Optional[str] = Query(None),
    max_budget: Optional[float] = Query(None, ge=0),
    min_budget: Optional[float] = Query(None, ge=0),
    geography: Optional[str] = Query(None),
    verification_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    include_unverified: bool = Query(False),
):
    """List verified opportunities and franchises with genuine source provenance.

    Note: Read requests NEVER auto-seed or manufacture records. Ingestion is explicit.
    """
    db = _db()
    try:
        return list_verified_opportunities(
            db,
            opportunity_type=type,
            sector=sector,
            max_budget=max_budget,
            min_budget=min_budget,
            geography=geography,
            verification_status=verification_status,
            search=search,
            include_unverified=include_unverified,
        )
    finally:
        db.close()


@router.get("/compare", response_model=List[Dict[str, Any]])
def compare_opportunities(
    ids: str = Query(..., description="Comma-separated IDs of opportunities to compare"),
):
    """Compare multiple opportunities side-by-side based strictly on verified facts."""
    db = _db()
    try:
        id_list = []
        for raw_id in ids.split(","):
            val = raw_id.strip()
            if val.isdigit():
                id_list.append(int(val))
        if not id_list:
            raise HTTPException(status_code=400, detail="Invalid IDs provided")
        if len(id_list) > 4:
            raise HTTPException(status_code=400, detail="Maximum 4 opportunities can be compared simultaneously")

        return compare_verified_opportunities(db, id_list)
    finally:
        db.close()


@router.get("/{opportunity_id}", response_model=VerifiedOpportunityDetailOut)
def get_opportunity(opportunity_id: int):
    """Get complete opportunity details, known vs unknown facts breakdown, and version history."""
    db = _db()
    try:
        item = get_verified_opportunity(db, opportunity_id)
        if not item:
            raise HTTPException(status_code=404, detail="Verified opportunity not found")
        return item
    finally:
        db.close()


@router.post("/{opportunity_id}/create-study", response_model=CreateStudyFromOpportunityOut, status_code=201)
def create_study(
    opportunity_id: int,
    data: CreateStudyFromOpportunityIn,
    user: UserOut = Depends(get_current_user),
):
    """Create a real persistent Feasibility Study from this opportunity with verified provenance lineage."""
    db = _db()
    try:
        user_row = db.get(models.User, user.id)
        if not user_row:
            raise HTTPException(status_code=401, detail="User not found")

        result = create_study_from_opportunity(
            db=db,
            user=user_row,
            opportunity_id=opportunity_id,
            custom_budget=data.custom_budget,
            study_title=data.study_title,
            match_result_id=data.match_result_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/admin/ingest", status_code=200)
def ingest_catalog(
    force_refresh: bool = Query(False),
    user: UserOut = Depends(require_roles("admin")),
):
    """Admin endpoint: explicitly bootstrap or reconcile the verified opportunities catalog."""
    db = _db()
    try:
        count = seed_verified_opportunities(db, force_refresh=force_refresh)
        return {"status": "success", "total_records": count, "force_refresh": force_refresh}
    finally:
        db.close()


@router.post("/", response_model=VerifiedOpportunityOut, status_code=201)
def create_opportunity(
    data: OpportunityCreateIn,
    user: UserOut = Depends(require_roles("admin", "consultant")),
):
    """Admin endpoint: register a new verified opportunity with initial audit & version snapshot.

    Enforces that new records start as UNVERIFIED unless validated evidence supports the status.
    Cannot self-declare VERIFIED_CURRENT without evidence validation.
    """
    db = _db()
    try:
        existing = db.query(models.VerifiedOpportunity).filter_by(slug=data.slug).first()
        if existing:
            raise HTTPException(status_code=409, detail="Opportunity with this slug already exists")

        payload = data.model_dump()
        # Rule A: POST /opportunities is ALWAYS created as UNVERIFIED.
        # Self-certifying VERIFIED_CURRENT or self-promoting to VERIFIED_PARTIAL via API is strictly prohibited.
        if data.verification_status in (STATUS_VERIFIED_CURRENT, STATUS_VERIFIED_PARTIAL):
            raise HTTPException(
                status_code=422,
                detail="Cannot self-certify as VERIFIED_CURRENT or VERIFIED_PARTIAL. New opportunities created via API always start as UNVERIFIED.",
            )
        payload["verification_status"] = STATUS_UNVERIFIED
        payload["is_active"] = False
        if payload.get("field_provenance") is None:
            payload["field_provenance"] = {}

        item = models.VerifiedOpportunity(**payload)
        db.add(item)
        db.flush()

        v_entry = models.OpportunityVersionHistory(
            opportunity_id=item.id,
            data_version=item.data_version,
            snapshot=payload,
            changed_by=user.id,
            change_reason="Admin registry creation",
        )
        db.add(v_entry)
        db.add(
            models.AuditLog(
                actor_id=user.id,
                action="verified_opportunity.create",
                entity="verified_opportunity",
                entity_id=item.id,
                meta={"slug": item.slug, "status": item.verification_status},
            )
        )
        db.commit()
        db.refresh(item)
        return item
    finally:
        db.close()


@router.patch("/{opportunity_id}", response_model=VerifiedOpportunityDetailOut)
def update_opportunity(
    opportunity_id: int,
    data: OpportunityUpdateIn,
    user: UserOut = Depends(require_roles("admin")),
):
    """Admin endpoint: update opportunity details, bumping version and retaining snapshot history."""
    db = _db()
    try:
        item = get_verified_opportunity(db, opportunity_id)
        if not item:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        update_dict = data.model_dump(exclude_unset=True, exclude={"change_reason"})
        if not update_dict:
            return item

        # Validate requested status change (Rule A: cannot promote to VERIFIED_CURRENT or VERIFIED_PARTIAL via PATCH)
        if "verification_status" in update_dict:
            req_status = update_dict["verification_status"]
            if req_status in (STATUS_VERIFIED_CURRENT, STATUS_VERIFIED_PARTIAL):
                raise HTTPException(
                    status_code=422,
                    detail="Cannot self-promote to VERIFIED_CURRENT or VERIFIED_PARTIAL via PATCH. Promotion is restricted to server-controlled verification workflow.",
                )
            merged = {
                "opportunity_type": item.opportunity_type,
                "investment_min": update_dict.get("investment_min", item.investment_min),
                "investment_max": update_dict.get("investment_max", item.investment_max),
                "franchise_fee": update_dict.get("franchise_fee", item.franchise_fee),
                "royalty_model": update_dict.get("royalty_model", item.royalty_model),
                "required_space": update_dict.get("required_space", item.required_space),
                "geography": update_dict.get("geography", item.geography),
                "sector": update_dict.get("sector", item.sector),
                "official_source_url": update_dict.get("official_source_url", item.official_source_url),
                "field_provenance": update_dict.get("field_provenance", item.field_provenance),
                "last_checked_at": item.last_checked_at,
                "is_active": item.is_active,
            }
            try:
                validated_status = validate_evidence_and_status(merged, req_status, is_server_curated=False)
                update_dict["verification_status"] = validated_status
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))

        # Increment semantic data version: e.g. 1.0.0 -> 1.0.1
        parts = item.data_version.split(".")
        if len(parts) == 3 and parts[2].isdigit():
            new_version = f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
        else:
            new_version = "1.0.1"

        for k, v in update_dict.items():
            setattr(item, k, v)
        item.data_version = new_version
        item.last_verified_at = datetime.now(timezone.utc).replace(tzinfo=None)

        v_entry = models.OpportunityVersionHistory(
            opportunity_id=item.id,
            data_version=new_version,
            snapshot=update_dict,
            changed_by=user.id,
            change_reason=data.change_reason,
        )
        db.add(v_entry)
        db.add(
            models.AuditLog(
                actor_id=user.id,
                action="verified_opportunity.update",
                entity="verified_opportunity",
                entity_id=item.id,
                meta={"version": new_version, "reason": data.change_reason},
            )
        )
        db.commit()
        db.refresh(item)
        return item
    finally:
        db.close()
