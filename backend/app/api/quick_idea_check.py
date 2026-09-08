"""
Quick Idea Check API (Entry 1: "لدي فكرة مشروع").

Turns a one-sentence idea into a persistent Project + Study and a
deterministic readiness classification (see app.services.quick_idea_check)
-- never a fabricated percentage score. Reuses the same idempotent
project/study creation and ownership rules as the feasibility router: a
project may only ever have one study, and re-posting for the same
project_id updates the recorded idea rather than creating a duplicate.

Requires persistence (DATABASE_URL); demo mode returns 503.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db import DB_ENABLED, SessionLocal
from app.api.auth import UserOut, get_current_user
from app.services.study_access import can_access_owner, owned_study_or_error
from app.services.quick_idea_check import build_check, classify_industry

router = APIRouter(prefix="/quick-idea-check", tags=["quick-idea-check"])


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Quick idea check requires persistence (database not configured).")
    return SessionLocal()


class QuickIdeaCheckIn(BaseModel):
    idea_text: str = Field(..., min_length=3, max_length=500)
    estimated_capital: float = Field(..., gt=0)
    city: Optional[str] = Field(default=None, max_length=100)
    region: Optional[str] = Field(default=None, max_length=100)
    customer_segment: Optional[str] = Field(default=None, max_length=200)
    goal: Optional[str] = Field(default=None, max_length=200)
    is_existing_business: bool = False
    project_id: Optional[int] = None


class QuickIdeaCheckOut(BaseModel):
    project_id: int
    study_id: int
    status: str
    industry_guess: Optional[str] = None
    regulatory_complexity_hint: str
    known_fields: List[str]
    missing_fields: List[str]
    evidence_coverage: int
    assumption_coverage: int
    main_uncertainties: List[str]
    recommended_next_step: str


def _counts(db, models, study_id: int) -> tuple[int, int]:
    evidence_count = db.query(models.EvidenceItem).filter(models.EvidenceItem.study_id == study_id).count()
    assumption_count = (
        db.query(models.StudyAssumption)
        .filter(models.StudyAssumption.study_id == study_id, models.StudyAssumption.is_active.is_(True))
        .count()
    )
    return evidence_count, assumption_count


@router.post("/", response_model=QuickIdeaCheckOut, status_code=201)
def create_quick_idea_check(body: QuickIdeaCheckIn, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        industry = classify_industry(body.idea_text) or "technology"

        if body.project_id is not None:
            project = db.get(models.Project, body.project_id)
            if project is None:
                raise HTTPException(status_code=404, detail="Project not found")
            if not can_access_owner(user, project.owner_id):
                raise HTTPException(status_code=403, detail="Not authorized for this project")
        else:
            project = models.Project(
                name=body.idea_text[:200],
                industry=industry,
                investment=body.estimated_capital,
                stage="idea",
                workflow_status="quick_idea_check",
                owner_id=user.id,
            )
            db.add(project)
            db.commit()
            db.refresh(project)

        # A project is the persistent root aggregate and has one study (same
        # invariant as POST /feasibility/): reuse it instead of duplicating.
        study = (
            db.query(models.FeasibilityStudy)
            .filter(models.FeasibilityStudy.project_id == project.id)
            .order_by(models.FeasibilityStudy.id.asc())
            .first()
        )
        if study is None:
            study = models.FeasibilityStudy(
                project_id=project.id,
                title=body.idea_text[:255],
                study_type="general",
                status="draft",
                current_step=1,
                payload={"industry": industry, "investment": body.estimated_capital},
            )
            db.add(study)
            db.commit()
            db.refresh(study)

        payload = dict(study.payload or {})
        payload["quick_idea_check"] = {
            "idea_text": body.idea_text,
            "city": body.city,
            "region": body.region,
            "estimated_capital": body.estimated_capital,
            "customer_segment": body.customer_segment,
            "goal": body.goal,
            "is_existing_business": body.is_existing_business,
        }
        study.payload = payload
        study.revision += 1
        db.add(study)
        db.commit()

        evidence_count, assumption_count = _counts(db, models, study.id)
        check = build_check(
            idea_text=body.idea_text,
            city=body.city,
            region=body.region,
            estimated_capital=body.estimated_capital,
            customer_segment=body.customer_segment,
            goal=body.goal,
            is_existing_business=body.is_existing_business,
            evidence_count=evidence_count,
            assumption_count=assumption_count,
        )
        return QuickIdeaCheckOut(project_id=project.id, study_id=study.id, **check)
    finally:
        db.close()


@router.get("/{study_id}", response_model=QuickIdeaCheckOut)
def get_quick_idea_check(study_id: int, user: UserOut = Depends(get_current_user)):
    """Recompute the check live from current evidence/assumption coverage."""
    from app import models

    db = _require_db()
    try:
        study = owned_study_or_error(db, models, study_id, user)
        stored = (study.payload or {}).get("quick_idea_check")
        if not stored:
            raise HTTPException(status_code=404, detail="No quick idea check recorded for this study")
        evidence_count, assumption_count = _counts(db, models, study.id)
        check = build_check(
            idea_text=stored.get("idea_text", ""),
            city=stored.get("city"),
            region=stored.get("region"),
            estimated_capital=stored.get("estimated_capital"),
            customer_segment=stored.get("customer_segment"),
            goal=stored.get("goal"),
            is_existing_business=bool(stored.get("is_existing_business")),
            evidence_count=evidence_count,
            assumption_count=assumption_count,
        )
        return QuickIdeaCheckOut(project_id=study.project_id, study_id=study.id, **check)
    finally:
        db.close()
