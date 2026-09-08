import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import UserOut, get_current_user
from app.db import DB_ENABLED, get_db
from app.models import FinancialAnalysis, FinancialResult, Project
from app.services.entitlements import require_service
from app.services.platform_events import notify, record_event
from app.services.study_access import owned_study_or_error

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "financial-engine"))
from calculator import evaluate_feasibility, sensitivity_analysis  # noqa: E402

router = APIRouter(prefix="/financial", tags=["financial"])


class FeasibilityRequest(BaseModel):
    investment: float = Field(..., gt=0)
    annual_cash_flows: List[float] = Field(..., min_length=1)
    discount_rate: float = Field(default=0.10, ge=0, le=1)


class FeasibilityResponse(BaseModel):
    roi_percent: Optional[float]
    payback_years: Optional[float]
    npv: Optional[float]
    irr_percent: Optional[float]
    verdict: str


def _eval(investment: float, flows: List[float], discount_rate: float) -> dict:
    result = evaluate_feasibility(investment, flows, discount_rate)
    return {
        "roi_percent": round(result.roi_percent, 2) if result.roi_percent is not None else None,
        "payback_years": round(result.payback_years, 2) if result.payback_years is not None else None,
        "npv": round(result.npv_value, 2) if result.npv_value is not None else None,
        "irr_percent": round(result.irr_value * 100, 2) if result.irr_value is not None else None,
        "verdict": result.verdict,
    }


@router.post("/evaluate", response_model=FeasibilityResponse)
def evaluate(req: FeasibilityRequest):
    return FeasibilityResponse(**_eval(req.investment, req.annual_cash_flows, req.discount_rate))


@router.post("/sensitivity")
def sensitivity(req: FeasibilityRequest):
    return sensitivity_analysis(req.investment, req.annual_cash_flows, req.discount_rate)


class AnalysisCreate(BaseModel):
    title: str = "Financial analysis"
    investment: float = Field(..., gt=0)
    annual_cash_flows: List[float] = Field(..., min_length=1)
    discount_rate: float = Field(default=0.10, ge=0, le=1)
    project_id: Optional[int] = None
    feasibility_study_id: Optional[int] = None
    import_meta: dict = Field(default_factory=dict)


class AnalysisOut(BaseModel):
    id: int
    owner_id: int
    project_id: Optional[int]
    feasibility_study_id: Optional[int]
    title: str
    investment: float
    annual_cash_flows: list
    discount_rate: float
    result: dict
    import_meta: dict

    model_config = {"from_attributes": True}


class ImportPreview(BaseModel):
    study_id: int
    project_id: int
    project_name: Optional[str] = None
    investment: Optional[float] = None
    annual_cash_flows: List[float] = Field(default_factory=list)
    discount_rate: float = 0.10
    imported_fields: List[str]
    source_record: str
    last_sync: Optional[str] = None


@router.get("/analyses", response_model=list[AnalysisOut])
def list_analyses(
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
    project_id: Optional[int] = None,
):
    if not DB_ENABLED:
        return []
    require_service(db, user, "financial_analysis")
    q = db.query(FinancialAnalysis).filter(FinancialAnalysis.owner_id == user.id)
    if project_id:
        q = q.filter(FinancialAnalysis.project_id == project_id)
    return q.order_by(FinancialAnalysis.id.desc()).all()


@router.post("/analyses", response_model=AnalysisOut, status_code=201)
def create_analysis(
    body: AnalysisCreate,
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not DB_ENABLED:
        raise HTTPException(503, "Database unavailable")
    require_service(db, user, "financial_analysis")
    if body.project_id:
        project = db.get(Project, body.project_id)
        if project is None or (user.role_key != "admin" and project.owner_id != user.id):
            raise HTTPException(404, "Project not found")
    if body.feasibility_study_id:
        from app import models

        owned_study_or_error(db, models, body.feasibility_study_id, user)

    result = _eval(body.investment, body.annual_cash_flows, body.discount_rate)
    row = FinancialAnalysis(
        owner_id=user.id,
        project_id=body.project_id,
        feasibility_study_id=body.feasibility_study_id,
        title=body.title,
        investment=body.investment,
        annual_cash_flows=body.annual_cash_flows,
        discount_rate=body.discount_rate,
        result=result,
        import_meta=body.import_meta or {},
    )
    db.add(row)
    record_event(db, user_id=user.id, event_type="workflow_completed", service_key="financial_analysis", entity="financial_analysis")
    notify(
        db,
        user_id=user.id,
        kind="financial_ready",
        title_en="Financial analysis saved",
        title_ar="تم حفظ التحليل المالي",
        entity="financial_analysis",
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/analyses/{analysis_id}", response_model=AnalysisOut)
def get_analysis(
    analysis_id: int,
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not DB_ENABLED:
        raise HTTPException(503, "Database unavailable")
    row = db.get(FinancialAnalysis, analysis_id)
    if row is None or (user.role_key != "admin" and row.owner_id != user.id):
        raise HTTPException(404, "Analysis not found")
    return row


@router.get("/from-study/{study_id}", response_model=ImportPreview)
def import_preview_from_study(
    study_id: int,
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Optional import preview. Never auto-applies into a new analysis."""
    from app import models

    if not DB_ENABLED:
        raise HTTPException(503, "Database unavailable")
    study = owned_study_or_error(db, models, study_id, user)
    project = db.get(Project, study.project_id)
    latest = (
        db.query(FinancialResult)
        .filter(FinancialResult.study_id == study.id)
        .order_by(FinancialResult.id.desc())
        .first()
    )
    payload = study.payload or {}
    investment = float(payload.get("investment") or (project.investment if project else 0) or 0)
    flows = []
    discount = 0.10
    fields = ["project_name", "investment"]
    if latest and latest.detail:
        flows = list(latest.detail.get("annual_cash_flows") or [])
        discount = float(latest.detail.get("discount_rate") or 0.10)
        if flows:
            fields.append("annual_cash_flows")
            fields.append("discount_rate")
    last_sync = None
    if latest is not None and latest.updated_at is not None:
        last_sync = latest.updated_at.replace(tzinfo=timezone.utc).isoformat() if latest.updated_at.tzinfo is None else latest.updated_at.isoformat()
    elif study.updated_at is not None:
        last_sync = study.updated_at.isoformat()
    return ImportPreview(
        study_id=study.id,
        project_id=study.project_id,
        project_name=project.name if project else study.title,
        investment=investment or None,
        annual_cash_flows=flows,
        discount_rate=discount,
        imported_fields=fields,
        source_record=f"feasibility_study:{study.id}",
        last_sync=last_sync or datetime.now(timezone.utc).isoformat(),
    )
