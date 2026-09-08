from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from datetime import datetime, timezone

from app.api.auth import UserOut, get_current_user
from app.db import DB_ENABLED, get_db
from app.models import Proposal, Project
from app.services.entitlements import require_service
from app.services.platform_events import notify, record_event
from app.services.reporting import build_proposal_context, generate_proposal_docx, generate_proposal_pdf
from app.services.study_access import owned_study_or_error

router = APIRouter(prefix="/proposals", tags=["proposals"])


class ProposalCreate(BaseModel):
    title: str
    proposal_type: str = "commercial"
    locale: str = "ar"
    project_id: Optional[int] = None
    feasibility_study_id: Optional[int] = None
    payload: dict = {}


class ProposalUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    payload: Optional[dict] = None
    version: Optional[str] = None


class ProposalOut(BaseModel):
    id: int
    owner_id: Optional[int]
    project_id: Optional[int]
    title: str
    proposal_type: str
    status: str
    locale: str
    payload: dict
    version: str
    feasibility_study_id: Optional[int]

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[ProposalOut])
def list_proposals(
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not DB_ENABLED:
        return []
    return db.query(Proposal).filter(Proposal.owner_id == user.id).all()


@router.post("/", response_model=ProposalOut, status_code=201)
def create_proposal(
    body: ProposalCreate,
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not DB_ENABLED:
        raise HTTPException(503, "Database unavailable")
    require_service(db, user, "proposal")
    if body.project_id:
        project = db.get(Project, body.project_id)
        if project is None or (user.role_key != "admin" and project.owner_id != user.id):
            raise HTTPException(404, "Project not found")
    if body.feasibility_study_id:
        from app import models

        owned_study_or_error(db, models, body.feasibility_study_id, user)
    proposal = Proposal(
        owner_id=user.id,
        project_id=body.project_id,
        title=body.title,
        proposal_type=body.proposal_type,
        locale=body.locale,
        payload=body.payload,
        feasibility_study_id=body.feasibility_study_id,
    )
    db.add(proposal)
    record_event(db, user_id=user.id, event_type="workflow_completed", service_key="proposal", entity="proposal")
    notify(
        db,
        user_id=user.id,
        kind="proposal_ready",
        title_en="Proposal saved",
        title_ar="تم حفظ العرض",
        entity="proposal",
    )
    db.commit()
    db.refresh(proposal)
    return proposal


class ImportFromStudyOut(BaseModel):
    study_id: int
    project_id: int
    project_name: Optional[str] = None
    industry: Optional[str] = None
    investment: Optional[float] = None
    study_title: str
    verdict: Optional[str] = None
    imported_fields: list[str]
    source_record: str
    last_sync: Optional[str] = None


@router.get("/from-study/{study_id}", response_model=ImportFromStudyOut)
def import_from_study(
    study_id: int,
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app import models

    if not DB_ENABLED:
        raise HTTPException(503, "Database unavailable")
    study = owned_study_or_error(db, models, study_id, user)
    project = db.get(Project, study.project_id)
    latest = (
        db.query(models.FinancialResult)
        .filter(models.FinancialResult.study_id == study.id)
        .order_by(models.FinancialResult.id.desc())
        .first()
    )
    fields = ["study_title", "project_name", "industry", "investment"]
    if latest is not None:
        fields.append("verdict")
    last_sync = (latest.updated_at if latest is not None else study.updated_at)
    return ImportFromStudyOut(
        study_id=study.id,
        project_id=study.project_id,
        project_name=project.name if project else None,
        industry=project.industry if project else None,
        investment=project.investment if project else None,
        study_title=study.title,
        verdict=latest.verdict if latest is not None else None,
        imported_fields=fields,
        source_record=f"feasibility_study:{study.id}",
        last_sync=last_sync.isoformat() if last_sync is not None else datetime.now(timezone.utc).isoformat(),
    )


@router.get("/{proposal_id}", response_model=ProposalOut)
def get_proposal(
    proposal_id: int,
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not DB_ENABLED:
        raise HTTPException(503, "Database unavailable")
    proposal = db.get(Proposal, proposal_id)
    if not proposal or proposal.owner_id != user.id:
        raise HTTPException(404, "Proposal not found")
    return proposal


@router.patch("/{proposal_id}", response_model=ProposalOut)
def update_proposal(
    proposal_id: int,
    body: ProposalUpdate,
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not DB_ENABLED:
        raise HTTPException(503, "Database unavailable")
    proposal = db.get(Proposal, proposal_id)
    if not proposal or proposal.owner_id != user.id:
        raise HTTPException(404, "Proposal not found")
    if body.title is not None:
        proposal.title = body.title
    if body.status is not None:
        proposal.status = body.status
    if body.payload is not None:
        merged = {**(proposal.payload or {}), **body.payload}
        proposal.payload = merged
    if body.version is not None:
        proposal.version = body.version
    db.commit()
    db.refresh(proposal)
    return proposal


@router.get("/{proposal_id}/export")
def export_proposal(
    proposal_id: int,
    fmt: str = Query("pdf", pattern="^(pdf|docx)$"),
    locale: str = Query("ar", pattern="^(ar|en)$"),
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    proposal = db.get(Proposal, proposal_id)
    if not proposal or (user.role_key != "admin" and proposal.owner_id != user.id):
        raise HTTPException(404, "Proposal not found")
    ctx = build_proposal_context(proposal)
    if fmt == "pdf":
        data, media = generate_proposal_pdf(ctx, locale), "application/pdf"
    else:
        data, media = generate_proposal_docx(ctx, locale), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return Response(data, media_type=media, headers={"Content-Disposition": f'attachment; filename="proposal_{proposal.id}_{locale}.{fmt}"'})


@router.delete("/{proposal_id}", status_code=204)
def delete_proposal(
    proposal_id: int,
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not DB_ENABLED:
        raise HTTPException(503, "Database unavailable")
    proposal = db.get(Proposal, proposal_id)
    if not proposal or proposal.owner_id != user.id:
        raise HTTPException(404, "Proposal not found")
    db.delete(proposal)
    db.commit()
