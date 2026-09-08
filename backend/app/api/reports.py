"""
Report generation & download API.

  GET /reports/study/{study_id}?fmt=pdf|docx&locale=ar|en
      -> streams a freshly generated bilingual feasibility report and records
         a Report row for audit/history.

Requires persistence. In demo mode returns 503 (no study to report on).
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from app.db import DB_ENABLED, SessionLocal
from app.api.auth import UserOut, get_current_user
from app.services.entitlements import require_service
from app.services.platform_events import record_event
from app.services.reporting import build_report_context, generate_pdf, generate_docx, generate_investor_package_pdf

router = APIRouter(prefix="/reports", tags=["reports"])


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Reports require persistence (database not configured).")
    return SessionLocal()


def _latest_result(db, models, study_id: int):
    row = (
        db.query(models.FinancialResult)
        .filter_by(study_id=study_id)
        .order_by(models.FinancialResult.id.desc())
        .first()
    )
    if row is None:
        return None
    detail = row.detail or {}
    return {
        "roi_percent": row.roi,
        "payback_years": row.payback_years,
        "npv": row.npv,
        "irr_percent": (row.irr * 100) if row.irr is not None else None,
        "verdict": row.verdict,
        "sensitivity": detail.get("sensitivity", []),
    }


@router.get("/study/{study_id}")
def download_report(
    study_id: int,
    fmt: str = Query("pdf", pattern="^(pdf|docx)$"),
    locale: str = Query("ar", pattern="^(ar|en)$"),
    user: UserOut = Depends(get_current_user),
):
    from app import models

    db = _require_db()
    try:
        study = db.get(models.FeasibilityStudy, study_id)
        if study is None:
            raise HTTPException(status_code=404, detail="Study not found")
        project = db.get(models.Project, study.project_id)
        # Ownership: a report exposes a study's full financials, so only the
        # study's project owner (or an admin) may download it.
        owner_id = project.owner_id if project is not None else None
        if user.role_key != "admin" and owner_id != user.id:
            raise HTTPException(status_code=403, detail="Not authorized for this study")
        result = _latest_result(db, models, study.id)
        ctx = build_report_context(study, result, project)

        if fmt == "pdf":
            data = generate_pdf(ctx, locale)
            media = "application/pdf"
            ext = "pdf"
        else:
            data = generate_docx(ctx, locale)
            media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ext = "docx"

        db.add(models.Report(study_id=study.id, fmt=ext, locale=locale, version="1.0"))
        db.add(models.AuditLog(actor_id=user.id, action="report.generate", entity="study",
                               entity_id=study.id, meta={"fmt": ext, "locale": locale}))
        db.commit()

        filename = "feasibility_%d_%s.%s" % (study.id, locale, ext)
        headers = {"Content-Disposition": "attachment; filename=" + filename}
        return Response(content=data, media_type=media, headers=headers)
    finally:
        db.close()


class InvestorPackageIn(BaseModel):
    study_id: Optional[int] = None
    proposal_id: Optional[int] = None
    project_id: Optional[int] = None
    include: List[str] = []
    locale: str = "ar"


@router.post("/investor-package")
def investor_package(body: InvestorPackageIn, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        require_service(db, user, "reports")
        if not body.study_id and not body.proposal_id and not body.project_id:
            raise HTTPException(400, "Select at least one source: feasibility, proposal, or business profile.")
        ctx = {"sources": [], "locale": body.locale}
        if body.project_id:
            project = db.get(models.Project, body.project_id)
            if project is None or (user.role_key != "admin" and project.owner_id != user.id):
                raise HTTPException(404, "Project not found")
            ctx["project"] = {"name": project.name, "industry": project.industry, "investment": project.investment, "stage": project.stage}
            ctx["sources"].append({"kind": "business_profile", "id": project.id, "label": project.name})
        if body.study_id:
            study = db.get(models.FeasibilityStudy, body.study_id)
            if study is None:
                raise HTTPException(404, "Study not found")
            project = db.get(models.Project, study.project_id)
            if user.role_key != "admin" and (project is None or project.owner_id != user.id):
                raise HTTPException(403, "Not authorized for this study")
            result = _latest_result(db, models, study.id)
            ctx["study"] = build_report_context(study, result, project)
            ctx["sources"].append({"kind": "feasibility", "id": study.id, "label": study.title})
        if body.proposal_id:
            proposal = db.get(models.Proposal, body.proposal_id)
            if proposal is None or (user.role_key != "admin" and proposal.owner_id != user.id):
                raise HTTPException(404, "Proposal not found")
            ctx["proposal"] = {"title": proposal.title, "type": proposal.proposal_type, **(proposal.payload or {})}
            ctx["sources"].append({"kind": "proposal", "id": proposal.id, "label": proposal.title})
        data = generate_investor_package_pdf(ctx, body.locale)
        record_event(db, user_id=user.id, event_type="report_generated", service_key="reports", entity="investor_package")
        db.commit()
        filename = "investor_package_%s.pdf" % body.locale
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=" + filename},
        )
    finally:
        db.close()
