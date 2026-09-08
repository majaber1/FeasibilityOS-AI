"""FastAPI Router for Wave 5 Launch Execution, Actuals & Reforecasting OS.

Endpoints for managing launch execution milestones, tasks, actual revenue/costs,
forecast vs actual variance tracking, explicit launch state transitions, and dynamic scenario reforecasting.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app import db, models
from app.api.auth import get_current_user
from app.services.launch import (
    get_or_create_launch_workspace,
    transition_launch_workspace_status,
    add_launch_milestone,
    update_launch_milestone,
    add_launch_task,
    update_launch_task,
    record_actual_period,
    evaluate_workspace_variances,
    generate_reforecast,
)

router = APIRouter(prefix="/api/v1/launch", tags=["Launch OS (Wave 5)"])

MilestoneStatus = Literal["PENDING", "IN_PROGRESS", "COMPLETED", "BLOCKED", "DELAYED"]
TaskStatus = Literal["PENDING", "IN_PROGRESS", "COMPLETED", "BLOCKED", "CANCELLED"]
WorkspaceStatus = Literal["PLANNED", "IN_PROGRESS", "BLOCKED", "LAUNCHED", "PAUSED", "CANCELLED"]


# Schemas
class MilestoneCreateIn(BaseModel):
    category: str = Field(..., description="REGULATORY, LOCATION, EQUIPMENT, TEAM, MARKETING, OPERATIONS")
    title: str = Field(..., min_length=3)
    description: Optional[str] = None
    due_date: Optional[str] = None
    budget_allocated: Optional[float] = None
    owner_name: Optional[str] = None
    dependency_milestone_id: Optional[int] = None
    is_suggested: bool = False
    status: Optional[MilestoneStatus] = "PENDING"


class MilestoneUpdateIn(BaseModel):
    status: Optional[MilestoneStatus] = None
    actual_cost: Optional[float] = None
    budget_allocated: Optional[float] = None
    completed_date: Optional[str] = None
    owner_name: Optional[str] = None
    due_date: Optional[str] = None


class TaskCreateIn(BaseModel):
    title: str = Field(..., min_length=3)
    milestone_id: Optional[int] = None
    description: Optional[str] = None
    owner_name: Optional[str] = None
    due_date: Optional[str] = None
    dependency_task_id: Optional[int] = None
    is_critical: bool = False
    status: Optional[TaskStatus] = "PENDING"


class TaskUpdateIn(BaseModel):
    status: Optional[TaskStatus] = None
    owner_name: Optional[str] = None
    due_date: Optional[str] = None
    completed_date: Optional[str] = None


class WorkspaceStatusUpdateIn(BaseModel):
    status: WorkspaceStatus = Field(..., description="PLANNED, IN_PROGRESS, BLOCKED, LAUNCHED, PAUSED, CANCELLED")
    actual_launch_date: Optional[str] = None
    target_launch_date: Optional[str] = None

    @model_validator(mode="after")
    def validate_actual_launch_date(self) -> WorkspaceStatusUpdateIn:
        if self.status != "LAUNCHED" and self.actual_launch_date is not None and self.actual_launch_date.strip() != "":
            raise ValueError(
                f"actual_launch_date cannot be set when status is '{self.status}'. It may be persisted only when status is LAUNCHED."
            )
        return self


class ActualPeriodIn(BaseModel):
    period_label: str = Field(..., min_length=2, description="e.g. M01, 2026-M01")
    period_order: int = Field(..., ge=1)
    actual_revenue: Optional[float] = None
    transactions_count: Optional[int] = None
    acquired_customers_count: Optional[int] = None
    average_ticket_size: Optional[float] = None
    actual_capex: Optional[float] = None
    actual_opex_salaries: Optional[float] = None
    actual_opex_rent: Optional[float] = None
    actual_opex_utilities: Optional[float] = None
    actual_opex_marketing: Optional[float] = None
    actual_opex_cogs: Optional[float] = None
    actual_opex_other: Optional[float] = None
    total_actual_opex: Optional[float] = None
    closing_cash_balance: Optional[float] = None
    source_type: str = Field(default="USER_ENTERED")
    source_reference: Optional[str] = None
    notes: Optional[str] = None


class ReforecastIn(BaseModel):
    reforecast_title: str = Field(..., min_length=3)
    adjustment_rationale: str = Field(..., min_length=5)
    growth_rate_adjustment_pct: float = Field(default=0.0)
    opex_adjustment_pct: float = Field(default=0.0)
    explicit_cash_balance: Optional[float] = None


def _serialize_workspace(ws: models.LaunchWorkspace, db_session: Optional[Session] = None) -> Dict[str, Any]:
    variances = evaluate_workspace_variances(ws)

    gate_decision = "UNKNOWN"
    gate_allowed = False
    gate_reason = "لم يتم تحديد قرار تحقق بعد."
    if db_session:
        val_ws = db_session.query(models.ValidationWorkspace).filter_by(study_id=ws.study_id).first()
        if val_ws and val_ws.decisions:
            latest_dec = val_ws.decisions[0]
            gate_decision = latest_dec.decision
            gate_allowed = latest_dec.decision in ("GO", "GO_WITH_CONDITIONS")
            gate_reason = latest_dec.decision_reason or (
                "بوابة الإطلاق مفتوحة بناءً على قرار التحقق." if gate_allowed else "بوابة الإطلاق مقفلة."
            )

    baseline_list = [
        {
            "id": s.id,
            "version": s.snapshot_version,
            "snapshot_version": s.snapshot_version,
            "is_frozen": True,
            "total_investment": s.total_investment,
            "monthly_projections": s.monthly_projections,
            "frozen_at": s.frozen_at.isoformat() if s.frozen_at else None,
            "source_study_revision": s.source_study_revision,
            "validation_decision_id": s.validation_decision_id,
            "validation_decision_version": s.validation_decision_version,
            "source_opportunity_id": s.source_opportunity_id,
            "source_opportunity_version": s.source_opportunity_version,
            "funding_context": s.funding_context,
            "calculation_version": s.calculation_version,
            "notes": s.notes,
        }
        for s in ws.baseline_snapshots
    ]

    reforecast_list = [
        {
            "id": r.id,
            "version": f"v{r.version_number}",
            "version_number": r.version_number,
            "reforecast_title": r.reforecast_title,
            "adjustment_rationale": r.adjustment_rationale,
            "growth_rate_adjustment_pct": r.growth_rate_adjustment_pct,
            "opex_adjustment_pct": r.opex_adjustment_pct,
            "monthly_burn_rate": r.monthly_burn_rate,
            "runway_months": r.remaining_runway_months,
            "remaining_runway_months": r.remaining_runway_months,
            "cash_flow_positive_month": r.cash_flow_positive_month,
            "financial_break_even_month": r.financial_break_even_month,
            "reforecast_payload": r.reforecast_payload,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in ws.reforecasts
    ]

    tasks_list = [
        {
            "id": t.id,
            "workspace_id": t.workspace_id,
            "milestone_id": t.milestone_id,
            "title": t.title,
            "description": t.description,
            "owner_name": t.owner_name,
            "due_date": t.due_date,
            "completed_date": t.completed_date,
            "status": t.status,
            "dependency_task_id": t.dependency_task_id,
            "is_critical": t.is_critical,
        }
        for t in ws.tasks
    ]

    milestones_list = [
        {
            "id": m.id,
            "category": m.category,
            "title": m.title,
            "description": m.description,
            "due_date": m.due_date,
            "completed_date": m.completed_date,
            "status": m.status,
            "budget_allocated": m.budget_allocated,
            "actual_cost": m.actual_cost,
            "owner_name": m.owner_name,
            "dependency_milestone_id": m.dependency_milestone_id,
            "is_suggested": m.is_suggested,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "owner_name": t.owner_name,
                    "due_date": t.due_date,
                    "completed_date": t.completed_date,
                    "status": t.status,
                    "dependency_task_id": t.dependency_task_id,
                    "is_critical": t.is_critical,
                }
                for t in m.tasks
            ],
        }
        for m in ws.milestones
    ]

    actual_periods_list = [
        {
            "id": a.id,
            "period_number": a.period_order,
            "period_label": a.period_label,
            "period_order": a.period_order,
            "actual_revenue": a.actual_revenue,
            "transactions_count": a.transactions_count,
            "average_ticket_size": a.average_ticket_size,
            "actual_capex": a.actual_capex,
            "actual_opex": a.total_actual_opex,
            "opex_breakdown": {
                "salaries": a.actual_opex_salaries,
                "rent": a.actual_opex_rent,
                "utilities_gov": a.actual_opex_utilities,
                "marketing": a.actual_opex_marketing,
                "inventory": a.actual_opex_cogs,
                "other": a.actual_opex_other,
            },
            "total_actual_opex": a.total_actual_opex,
            "net_cashflow": a.net_cashflow,
            "closing_cash_balance": a.closing_cash_balance,
            "source_type": a.source_type,
            "source_reference": a.source_reference,
            "notes": a.notes,
            "recorded_at": a.recorded_at.isoformat() if a.recorded_at else None,
        }
        for a in ws.actual_periods
    ]

    return {
        "workspace": {
            "id": ws.id,
            "study_id": ws.study_id,
            "project_id": ws.project_id,
            "status": ws.status,
            "target_launch_date": ws.target_launch_date,
            "actual_launch_date": ws.actual_launch_date,
            "created_at": ws.created_at.isoformat() if ws.created_at else None,
            "updated_at": ws.updated_at.isoformat() if ws.updated_at else None,
        },
        "id": ws.id,
        "study_id": ws.study_id,
        "project_id": ws.project_id,
        "status": ws.status,
        "decision_gate": {
            "decision": gate_decision,
            "is_allowed": gate_allowed,
            "reason": gate_reason,
        },
        "active_baseline": baseline_list[0] if baseline_list else None,
        "baseline_snapshots": baseline_list,
        "target_launch_date": ws.target_launch_date,
        "actual_launch_date": ws.actual_launch_date,
        "created_at": ws.created_at.isoformat() if ws.created_at else None,
        "updated_at": ws.updated_at.isoformat() if ws.updated_at else None,
        "variances_summary": variances,
        "variance_summary": variances,
        "milestones": milestones_list,
        "tasks": tasks_list,
        "actual_periods": actual_periods_list,
        "latest_reforecast": reforecast_list[0] if reforecast_list else None,
        "reforecasts": reforecast_list,
    }


@router.get("/study/{study_id}", status_code=status.HTTP_200_OK)
@router.get("/workspaces/study/{study_id}", status_code=status.HTTP_200_OK)
def get_or_create_workspace(
    study_id: int,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Fetches or initializes the launch execution workspace for a study."""
    try:
        ws = get_or_create_launch_workspace(db=db_session, user=user, study_id=study_id)
        return _serialize_workspace(ws, db_session=db_session)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/workspaces/{workspace_id}", status_code=status.HTTP_200_OK)
def get_workspace(
    workspace_id: int,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Retrieves a launch workspace by its ID."""
    ws = db_session.query(models.LaunchWorkspace).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Launch workspace not found")
    if ws.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return _serialize_workspace(ws, db_session=db_session)


@router.patch("/workspaces/{workspace_id}/status", status_code=status.HTTP_200_OK)
def update_workspace_status(
    workspace_id: int,
    payload: WorkspaceStatusUpdateIn,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Explicitly transitions launch workspace status (e.g. to LAUNCHED)."""
    try:
        ws = transition_launch_workspace_status(
            db=db_session,
            workspace_id=workspace_id,
            user=user,
            target_status=payload.status,
            actual_launch_date=payload.actual_launch_date,
            target_launch_date=payload.target_launch_date,
        )
        return _serialize_workspace(ws, db_session=db_session)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/workspaces/{workspace_id}/milestones", status_code=status.HTTP_201_CREATED)
def create_milestone(
    workspace_id: int,
    payload: MilestoneCreateIn,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Adds a new milestone to the launch workspace."""
    try:
        m = add_launch_milestone(
            db=db_session,
            workspace_id=workspace_id,
            user=user,
            category=payload.category,
            title=payload.title,
            description=payload.description,
            due_date=payload.due_date,
            budget_allocated=payload.budget_allocated,
            owner_name=payload.owner_name,
            dependency_milestone_id=payload.dependency_milestone_id,
            is_suggested=payload.is_suggested,
            status=payload.status,
        )
        return {
            "id": m.id,
            "category": m.category,
            "title": m.title,
            "description": m.description,
            "due_date": m.due_date,
            "completed_date": m.completed_date,
            "status": m.status,
            "budget_allocated": m.budget_allocated,
            "actual_cost": m.actual_cost,
            "owner_name": m.owner_name,
            "dependency_milestone_id": m.dependency_milestone_id,
            "is_suggested": m.is_suggested,
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        if "status" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/milestones/{milestone_id}", status_code=status.HTTP_200_OK)
def update_milestone(
    milestone_id: int,
    payload: MilestoneUpdateIn,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Updates status or cost of a launch milestone."""
    try:
        m = update_launch_milestone(
            db=db_session,
            milestone_id=milestone_id,
            user=user,
            status=payload.status,
            actual_cost=payload.actual_cost,
            budget_allocated=payload.budget_allocated,
            completed_date=payload.completed_date,
            owner_name=payload.owner_name,
            due_date=payload.due_date,
        )
        return {
            "id": m.id,
            "category": m.category,
            "title": m.title,
            "description": m.description,
            "due_date": m.due_date,
            "completed_date": m.completed_date,
            "status": m.status,
            "budget_allocated": m.budget_allocated,
            "actual_cost": m.actual_cost,
            "owner_name": m.owner_name,
            "dependency_milestone_id": m.dependency_milestone_id,
            "is_suggested": m.is_suggested,
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        if "status" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/workspaces/{workspace_id}/tasks", status_code=status.HTTP_201_CREATED)
def create_task(
    workspace_id: int,
    payload: TaskCreateIn,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Adds an execution task to a launch milestone or workspace."""
    try:
        t = add_launch_task(
            db=db_session,
            workspace_id=workspace_id,
            user=user,
            title=payload.title,
            milestone_id=payload.milestone_id,
            description=payload.description,
            owner_name=payload.owner_name,
            due_date=payload.due_date,
            dependency_task_id=payload.dependency_task_id,
            is_critical=payload.is_critical,
            status=payload.status,
        )
        return {
            "id": t.id,
            "workspace_id": t.workspace_id,
            "milestone_id": t.milestone_id,
            "title": t.title,
            "description": t.description,
            "owner_name": t.owner_name,
            "due_date": t.due_date,
            "completed_date": t.completed_date,
            "status": t.status,
            "dependency_task_id": t.dependency_task_id,
            "is_critical": t.is_critical,
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        if "status" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/tasks/{task_id}", status_code=status.HTTP_200_OK)
def update_task(
    task_id: int,
    payload: TaskUpdateIn,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Updates status or owner of a launch task."""
    try:
        t = update_launch_task(
            db=db_session,
            task_id=task_id,
            user=user,
            status=payload.status,
            owner_name=payload.owner_name,
            due_date=payload.due_date,
            completed_date=payload.completed_date,
        )
        return {
            "id": t.id,
            "workspace_id": t.workspace_id,
            "milestone_id": t.milestone_id,
            "title": t.title,
            "description": t.description,
            "owner_name": t.owner_name,
            "due_date": t.due_date,
            "completed_date": t.completed_date,
            "status": t.status,
            "dependency_task_id": t.dependency_task_id,
            "is_critical": t.is_critical,
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        if "status" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/workspaces/{workspace_id}/actuals", status_code=status.HTTP_201_CREATED)
def record_actuals(
    workspace_id: int,
    payload: ActualPeriodIn,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Records operational actual revenue, capex, and opex for a period."""
    try:
        p = record_actual_period(
            db=db_session,
            workspace_id=workspace_id,
            user=user,
            period_label=payload.period_label,
            period_order=payload.period_order,
            actual_revenue=payload.actual_revenue,
            transactions_count=payload.transactions_count,
            acquired_customers_count=payload.acquired_customers_count,
            average_ticket_size=payload.average_ticket_size,
            actual_capex=payload.actual_capex,
            actual_opex_salaries=payload.actual_opex_salaries,
            actual_opex_rent=payload.actual_opex_rent,
            actual_opex_utilities=payload.actual_opex_utilities,
            actual_opex_marketing=payload.actual_opex_marketing,
            actual_opex_cogs=payload.actual_opex_cogs,
            actual_opex_other=payload.actual_opex_other,
            total_actual_opex=payload.total_actual_opex,
            closing_cash_balance=payload.closing_cash_balance,
            source_type=payload.source_type,
            source_reference=payload.source_reference,
            notes=payload.notes,
        )
        return {
            "id": p.id,
            "period_label": p.period_label,
            "period_order": p.period_order,
            "actual_revenue": p.actual_revenue,
            "transactions_count": p.transactions_count,
            "acquired_customers_count": p.acquired_customers_count,
            "average_ticket_size": p.average_ticket_size,
            "actual_capex": p.actual_capex,
            "total_actual_opex": p.total_actual_opex,
            "net_cashflow": p.net_cashflow,
            "closing_cash_balance": p.closing_cash_balance,
            "source_type": p.source_type,
            "source_reference": p.source_reference,
            "notes": p.notes,
            "recorded_at": p.recorded_at.isoformat() if p.recorded_at else None,
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/workspaces/{workspace_id}/variances", status_code=status.HTTP_200_OK)
def get_variances(
    workspace_id: int,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Retrieves full forecast vs actual variance analysis with alerts."""
    ws = db_session.query(models.LaunchWorkspace).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Launch workspace not found")
    if ws.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return evaluate_workspace_variances(ws)


@router.post("/workspaces/{workspace_id}/reforecast", status_code=status.HTTP_201_CREATED)
def create_reforecast(
    workspace_id: int,
    payload: ReforecastIn,
    user: models.User = Depends(get_current_user),
    db_session: Session = Depends(db.get_db),
):
    """Creates a new forward-looking reforecast scenario."""
    try:
        r = generate_reforecast(
            db=db_session,
            workspace_id=workspace_id,
            user=user,
            reforecast_title=payload.reforecast_title,
            adjustment_rationale=payload.adjustment_rationale,
            growth_rate_adjustment_pct=payload.growth_rate_adjustment_pct,
            opex_adjustment_pct=payload.opex_adjustment_pct,
            explicit_cash_balance=payload.explicit_cash_balance,
        )
        return {
            "id": r.id,
            "version_number": r.version_number,
            "reforecast_title": r.reforecast_title,
            "adjustment_rationale": r.adjustment_rationale,
            "growth_rate_adjustment_pct": r.growth_rate_adjustment_pct,
            "opex_adjustment_pct": r.opex_adjustment_pct,
            "monthly_burn_rate": r.monthly_burn_rate,
            "remaining_runway_months": r.remaining_runway_months,
            "cash_flow_positive_month": r.cash_flow_positive_month,
            "financial_break_even_month": r.financial_break_even_month,
            "reforecast_payload": r.reforecast_payload,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
