"""FastAPI Router for Wave 6 Growth OS (Business Health, Trends, Unit Economics, Risks, Scenarios, Readiness, Decisions).

Endpoints:
- GET  /api/v1/growth/study/{study_id}
- GET  /api/v1/growth/workspaces/{workspace_id}
- POST /api/v1/growth/workspaces/{workspace_id}/scenarios
- POST /api/v1/growth/workspaces/{workspace_id}/what-if
- POST /api/v1/growth/workspaces/{workspace_id}/reviews
- POST /api/v1/growth/workspaces/{workspace_id}/decisions
- POST /api/v1/growth/workspaces/{workspace_id}/actions
- PATCH /api/v1/growth/actions/{action_id}
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import db, models
from app.api.auth import get_current_user
from app.services.growth import (
    get_or_create_growth_workspace,
    evaluate_all_trends,
    calculate_unit_economics,
    evaluate_business_health,
    detect_growth_risks,
    evaluate_expansion_readiness,
    get_growth_funding_context,
    execute_what_if_scenario,
    create_monthly_business_review,
    record_growth_decision,
    VALID_GROWTH_DECISIONS,
    SCENARIO_TYPES,
)

router = APIRouter(prefix="/api/v1/growth", tags=["Growth OS (Wave 6)"])

GrowthDecisionType = Literal["SCALE", "FIX", "PIVOT", "HOLD", "STOP", "NEEDS_INFORMATION"]
ActionStatus = Literal["PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"]


# --- Schemas ---

class ScenarioCreateIn(BaseModel):
    name: str = Field(..., min_length=2)
    scenario_type: str = Field(..., description="NEW_BRANCH, CAPACITY_EXPANSION, PRODUCT_EXPANSION, PRICE_OPTIMIZATION, COST_REDUCTION, DIGITAL_TRANSFORMATION, FRANCHISE_EXPANSION, OTHER")
    description: Optional[str] = None
    target_horizon_months: int = Field(default=12, ge=1, le=60)
    capex_required: Optional[float] = Field(default=None, ge=0)
    additional_monthly_opex: Optional[float] = Field(default=None, ge=0)
    expected_monthly_revenue_uplift: Optional[float] = Field(default=None, ge=0)
    target_capacity_increase_pct: Optional[float] = Field(default=None, ge=0)
    user_assumptions: Optional[Dict[str, Any]] = None


class WhatIfRunIn(BaseModel):
    scenario_id: Optional[int] = None
    scenario_name: str = Field(default="سيناريو افتراضي جديد", min_length=2)
    scenario_type: str = Field(default="OTHER")
    target_horizon_months: int = Field(default=12, ge=1, le=60)
    capex_required: Optional[float] = Field(default=None, ge=0)
    additional_monthly_opex: Optional[float] = Field(default=None, ge=0)
    expected_monthly_revenue_uplift: Optional[float] = Field(default=None, ge=0)
    target_capacity_increase_pct: Optional[float] = Field(default=None, ge=0)
    user_assumptions: Optional[Dict[str, Any]] = None


class MonthlyReviewIn(BaseModel):
    review_period: str = Field(..., min_length=2, description="e.g. 2026-M01 or M01")
    review_notes: Optional[str] = None
    target_next_month: Optional[str] = None


class DecisionRecordIn(BaseModel):
    decision: GrowthDecisionType = Field(..., description="SCALE, FIX, PIVOT, HOLD, STOP, NEEDS_INFORMATION")
    decision_reason: str = Field(..., min_length=5)
    growth_scenario_id: Optional[int] = Field(default=None, description="Required for SCALE decisions")
    user_assumptions: Optional[Dict[str, Any]] = None
    conditions: Optional[List[str]] = None
    re_evaluation_date: Optional[str] = None


class ActionCreateIn(BaseModel):
    title: str = Field(..., min_length=3)
    action_type: str = Field(default="REMEDIATION", description="REMEDIATION, EXPANSION, EXPERIMENT, REGULATORY, OPERATIONAL")
    category: str = Field(default="OPERATIONS", description="OPERATIONS, MARKETING, FINANCE, LEGAL, TECH")
    priority: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH, CRITICAL")
    owner_name: Optional[str] = None
    due_date: Optional[str] = None
    decision_id: Optional[int] = None


class ActionUpdateIn(BaseModel):
    status: Optional[ActionStatus] = None
    notes: Optional[str] = None
    due_date: Optional[str] = None
    owner_name: Optional[str] = None


# --- Helpers ---

def _verify_growth_workspace_ownership(
    session: Session,
    workspace_id: int,
    user: models.User,
) -> models.GrowthWorkspace:
    ws = session.query(models.GrowthWorkspace).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Growth workspace {workspace_id} not found",
        )
    if ws.project.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this growth workspace",
        )
    return ws


def _serialize_growth_workspace_full(
    ws: models.GrowthWorkspace,
    session: Session,
) -> Dict[str, Any]:
    launch_ws = session.query(models.LaunchWorkspace).filter_by(study_id=ws.study_id).first()
    actual_periods = (
        session.query(models.LaunchActualPeriod)
        .filter_by(workspace_id=launch_ws.id)
        .order_by(models.LaunchActualPeriod.period_order.asc())
        .all()
        if launch_ws
        else []
    )
    latest_actual = actual_periods[-1] if actual_periods else None

    # Compute analytical blocks
    health = evaluate_business_health(ws, launch_ws)
    trends = evaluate_all_trends(actual_periods)
    unit_econ = calculate_unit_economics(latest_actual)
    risks = detect_growth_risks(launch_ws)
    expansion_readiness = evaluate_expansion_readiness(ws, launch_ws)
    growth_funding = get_growth_funding_context(ws, launch_ws)

    # Fetch entities
    scenarios = (
        session.query(models.GrowthScenario)
        .filter_by(workspace_id=ws.id)
        .order_by(models.GrowthScenario.created_at.desc())
        .all()
    )
    what_if_models = (
        session.query(models.GrowthWhatIfModel)
        .filter_by(workspace_id=ws.id)
        .order_by(models.GrowthWhatIfModel.created_at.desc())
        .all()
    )
    reviews = (
        session.query(models.GrowthMonthlyReview)
        .filter_by(workspace_id=ws.id)
        .order_by(models.GrowthMonthlyReview.version_number.desc())
        .all()
    )
    decisions = (
        session.query(models.GrowthDecision)
        .filter_by(workspace_id=ws.id)
        .order_by(models.GrowthDecision.decision_version.desc())
        .all()
    )
    actions = (
        session.query(models.GrowthAction)
        .filter_by(workspace_id=ws.id)
        .order_by(models.GrowthAction.created_at.desc())
        .all()
    )

    return {
        "workspace": {
            "id": ws.id,
            "study_id": ws.study_id,
            "project_id": ws.project_id,
            "user_id": ws.user_id,
            "status": ws.status,
            "current_health_state": health.get("health_state", health.get("overall_state")),
            "current_health_summary_ar": health.get("health_summary_ar", health.get("summary_ar")),
            "created_at": ws.created_at.isoformat() if ws.created_at else None,
            "updated_at": ws.updated_at.isoformat() if ws.updated_at else None,
        },
        "business_health": health,
        "trends": trends,
        "unit_economics": unit_econ,
        "risks": risks,
        "expansion_readiness": expansion_readiness,
        "growth_funding": growth_funding,
        "actual_periods_count": len(actual_periods),
        "scenarios": [
            {
                "id": s.id,
                "workspace_id": s.workspace_id,
                "name": s.title,
                "title": s.title,
                "scenario_type": s.scenario_type,
                "description": s.reason,
                "reason": s.reason,
                "target_horizon_months": (s.capacity_assumptions or {}).get("target_horizon_months", 12),
                "capex_required": s.investment_required,
                "investment_required": s.investment_required,
                "additional_monthly_opex": (s.cost_assumptions or {}).get("additional_monthly_opex"),
                "expected_monthly_revenue_uplift": (s.revenue_assumptions or {}).get("expected_monthly_revenue_uplift"),
                "target_capacity_increase_pct": (s.capacity_assumptions or {}).get("target_capacity_increase_pct"),
                "user_assumptions": {
                    **(s.cost_assumptions or {}),
                    **(s.revenue_assumptions or {}),
                    **(s.capacity_assumptions or {}),
                },
                "status": s.status,
                "is_active": s.status != "REJECTED",
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in scenarios
        ],
        "what_if_models": [
            {
                "id": m.id,
                "workspace_id": m.workspace_id,
                "scenario_id": m.scenario_id,
                "scenario_name": m.title,
                "title": m.title,
                "model_type": m.model_type,
                "assumptions_summary": m.user_assumptions,
                "baseline_snapshot": m.baseline_inputs,
                "derived_monthly_projections": (m.derived_outputs or {}).get("monthly_forward_projections", []),
                "estimated_cash_payback_months": (m.derived_outputs or {}).get("estimated_cash_payback_months"),
                "estimated_net_runway_impact_months": (m.derived_outputs or {}).get("estimated_net_runway_impact_months"),
                "minimum_cash_required": (m.derived_outputs or {}).get("minimum_cash_required") or (m.user_assumptions or {}).get("capex_required"),
                "provenance": {
                    "actuals_baseline": "ACTUAL",
                    "capex_required": "USER_ASSUMPTION",
                    "monthly_projections": "PLATFORM_DERIVED",
                },
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in what_if_models
        ],
        "monthly_reviews": [
            {
                "id": r.id,
                "workspace_id": r.workspace_id,
                "review_period": r.review_period,
                "review_version": r.version_number,
                "version_number": r.version_number,
                "frozen_metrics": {
                    "health": r.health_snapshot,
                    "trends": r.trend_summary,
                    "unit_economics": r.unit_economics_snapshot,
                    "risks": r.risks_snapshot,
                },
                "review_notes": r.review_notes,
                "target_next_month": None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reviews
        ],
        "decisions": [
            {
                "id": d.id,
                "workspace_id": d.workspace_id,
                "growth_scenario_id": d.growth_scenario_id,
                "decision": d.decision,
                "decision_version": d.decision_version,
                "decision_reason": d.decision_reason,
                "supporting_facts": d.supporting_facts,
                "contradicting_facts": d.contradicting_facts,
                "unknowns": d.unknowns,
                "user_assumptions": d.user_assumptions,
                "risks": d.risks,
                "conditions": d.conditions,
                "recommended_next_actions": d.recommended_next_actions,
                "pivot_validation_workspace_id": d.pivot_validation_workspace_id,
                "re_evaluation_date": d.re_evaluation_date,
                "decided_at": d.decided_at.isoformat() if d.decided_at else None,
            }
            for d in decisions
        ],
        "actions": [
            {
                "id": a.id,
                "workspace_id": a.workspace_id,
                "decision_id": a.decision_id,
                "title": a.title,
                "action_type": a.action_type,
                "category": a.category,
                "priority": a.priority,
                "status": a.status,
                "owner_name": a.owner_name,
                "due_date": a.due_date,
                "notes": a.notes,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            }
            for a in actions
        ],
    }


# --- Endpoints ---

@router.get("/study/{study_id}")
def get_study_growth_workspace(
    study_id: int,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    """Retrieves or initializes the Growth OS workspace for a feasibility study."""
    try:
        ws = get_or_create_growth_workspace(session, current_user, study_id)
        return _serialize_growth_workspace_full(ws, session)
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/study/{study_id}/funding-context")
def get_study_growth_funding_context(
    study_id: int,
    scenario_id: Optional[int] = None,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    """Retrieves growth funding context for a feasibility study."""
    try:
        ws = get_or_create_growth_workspace(session, current_user, study_id)
        launch_ws = session.query(models.LaunchWorkspace).filter_by(study_id=study_id).first()
        scenario = None
        if scenario_id:
            scenario = session.query(models.GrowthScenario).filter_by(id=scenario_id, workspace_id=ws.id).first()
        return {"funding_context": get_growth_funding_context(ws, launch_ws, scenario=scenario)}
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/workspaces/{workspace_id}")
def get_growth_workspace_by_id(
    workspace_id: int,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    """Retrieves a specific Growth workspace by its ID."""
    ws = _verify_growth_workspace_ownership(session, workspace_id, current_user)
    return _serialize_growth_workspace_full(ws, session)


@router.post("/workspaces/{workspace_id}/scenarios", status_code=status.HTTP_201_CREATED)
def create_growth_scenario(
    workspace_id: int,
    payload: ScenarioCreateIn,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    """Creates an expansion / what-if scenario parameter template."""
    ws = _verify_growth_workspace_ownership(session, workspace_id, current_user)

    if payload.scenario_type not in SCENARIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid scenario_type '{payload.scenario_type}'. Allowed: {sorted(list(SCENARIO_TYPES))}",
        )

    scenario = models.GrowthScenario(
        workspace_id=ws.id,
        title=payload.name,
        reason=payload.description or payload.name,
        scenario_type=payload.scenario_type,
        investment_required=payload.capex_required,
        capacity_assumptions={
            "target_capacity_increase_pct": payload.target_capacity_increase_pct,
            "target_horizon_months": payload.target_horizon_months,
        },
        revenue_assumptions={
            "expected_monthly_revenue_uplift": payload.expected_monthly_revenue_uplift,
        },
        cost_assumptions={
            "additional_monthly_opex": payload.additional_monthly_opex,
            **(payload.user_assumptions or {}),
        },
        status="PROPOSED",
        created_by=current_user.id,
    )
    session.add(scenario)
    session.commit()
    session.refresh(scenario)

    return {
        "message": "Growth scenario created successfully",
        "scenario": {
            "id": scenario.id,
            "workspace_id": scenario.workspace_id,
            "name": scenario.title,
            "title": scenario.title,
            "scenario_type": scenario.scenario_type,
            "description": scenario.reason,
            "target_horizon_months": payload.target_horizon_months,
            "capex_required": scenario.investment_required,
            "additional_monthly_opex": payload.additional_monthly_opex,
            "expected_monthly_revenue_uplift": payload.expected_monthly_revenue_uplift,
            "target_capacity_increase_pct": payload.target_capacity_increase_pct,
            "user_assumptions": payload.user_assumptions or {},
            "is_active": True,
            "created_at": scenario.created_at.isoformat() if scenario.created_at else None,
        },
    }


@router.post("/workspaces/{workspace_id}/what-if", status_code=status.HTTP_201_CREATED)
def run_growth_what_if_model(
    workspace_id: int,
    payload: WhatIfRunIn,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    """Executes a transparent deterministic What-If expansion model without overwriting actuals."""
    ws = _verify_growth_workspace_ownership(session, workspace_id, current_user)

    # If scenario_id provided, verify it belongs to this workspace
    if payload.scenario_id is not None:
        scen = session.query(models.GrowthScenario).filter_by(id=payload.scenario_id).first()
        if not scen:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scenario {payload.scenario_id} not found",
            )
        if scen.workspace_id != ws.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scenario {payload.scenario_id} belongs to a different workspace",
            )

    try:
        model = execute_what_if_scenario(
            growth_ws=ws,
            user=current_user,
            scenario_name=payload.scenario_name,
            scenario_type=payload.scenario_type,
            target_horizon_months=payload.target_horizon_months,
            capex_required=payload.capex_required,
            additional_monthly_opex=payload.additional_monthly_opex,
            expected_monthly_revenue_uplift=payload.expected_monthly_revenue_uplift,
            target_capacity_increase_pct=payload.target_capacity_increase_pct,
            user_assumptions=payload.user_assumptions,
            scenario_id=payload.scenario_id,
        )
        return {
            "message": "What-If simulation executed successfully",
            "model": {
                "id": model.id,
                "workspace_id": model.workspace_id,
                "scenario_id": model.scenario_id,
                "scenario_name": model.title,
                "assumptions_summary": model.user_assumptions,
                "baseline_inputs": model.baseline_inputs,
                "actual_inputs": model.actual_inputs,
                "derived_outputs": model.derived_outputs,
                "baseline_snapshot": model.baseline_inputs,
                "derived_monthly_projections": (model.derived_outputs or {}).get("monthly_forward_projections", []),
                "estimated_cash_payback_months": (model.derived_outputs or {}).get("estimated_cash_payback_months"),
                "estimated_net_runway_impact_months": (model.derived_outputs or {}).get("estimated_net_runway_impact_months"),
                "minimum_cash_required": (model.derived_outputs or {}).get("minimum_cash_required") or (model.user_assumptions or {}).get("capex_required"),
                "provenance": {
                    "actuals_baseline": "ACTUAL",
                    "capex_required": "USER_ASSUMPTION",
                    "monthly_projections": "PLATFORM_DERIVED",
                },
                "created_at": model.created_at.isoformat() if model.created_at else None,
            },
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/workspaces/{workspace_id}/reviews", status_code=status.HTTP_201_CREATED)
def create_monthly_review(
    workspace_id: int,
    payload: MonthlyReviewIn,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    """Freezes an immutable monthly operational review snapshot."""
    ws = _verify_growth_workspace_ownership(session, workspace_id, current_user)

    try:
        review = create_monthly_business_review(
            growth_ws=ws,
            user=current_user,
            review_period=payload.review_period,
            review_notes=payload.review_notes,
        )
        return {
            "message": f"Monthly review for {review.review_period} frozen successfully (v{review.version_number})",
            "review": {
                "id": review.id,
                "workspace_id": review.workspace_id,
                "review_period": review.review_period,
                "review_version": review.version_number,
                "version_number": review.version_number,
                "frozen_metrics": {
                    "health": review.health_snapshot,
                    "trends": review.trend_summary,
                    "unit_economics": review.unit_economics_snapshot,
                    "risks": review.risks_snapshot,
                },
                "review_notes": review.review_notes,
                "target_next_month": payload.target_next_month,
                "created_at": review.created_at.isoformat() if review.created_at else None,
            },
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/workspaces/{workspace_id}/decisions", status_code=status.HTTP_201_CREATED)
def record_decision(
    workspace_id: int,
    payload: DecisionRecordIn,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    """Records an explicit strategic decision (SCALE, FIX, PIVOT, HOLD, STOP, NEEDS_INFORMATION) with strict governance."""
    ws = _verify_growth_workspace_ownership(session, workspace_id, current_user)

    try:
        decision = record_growth_decision(
            growth_ws=ws,
            user=current_user,
            decision=payload.decision,
            decision_reason=payload.decision_reason,
            user_assumptions=payload.user_assumptions,
            conditions=payload.conditions,
            re_evaluation_date=payload.re_evaluation_date,
            growth_scenario_id=payload.growth_scenario_id,
        )
        return {
            "message": f"Strategic decision '{decision.decision}' recorded successfully (v{decision.decision_version})",
            "decision": {
                "id": decision.id,
                "workspace_id": decision.workspace_id,
                "growth_scenario_id": decision.growth_scenario_id,
                "decision": decision.decision,
                "decision_version": decision.decision_version,
                "decision_reason": decision.decision_reason,
                "supporting_facts": decision.supporting_facts,
                "contradicting_facts": decision.contradicting_facts,
                "unknowns": decision.unknowns,
                "user_assumptions": decision.user_assumptions,
                "risks": decision.risks,
                "conditions": decision.conditions,
                "recommended_next_actions": decision.recommended_next_actions,
                "pivot_validation_workspace_id": decision.pivot_validation_workspace_id,
                "re_evaluation_date": decision.re_evaluation_date,
                "decided_at": decision.decided_at.isoformat() if decision.decided_at else None,
            },
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/workspaces/{workspace_id}/actions", status_code=status.HTTP_201_CREATED)
def create_growth_action(
    workspace_id: int,
    payload: ActionCreateIn,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    """Creates a trackable growth or remediation action item."""
    ws = _verify_growth_workspace_ownership(session, workspace_id, current_user)

    if payload.decision_id is not None:
        dec = session.query(models.GrowthDecision).filter_by(id=payload.decision_id).first()
        if not dec or dec.workspace_id != ws.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Decision {payload.decision_id} does not belong to this workspace",
            )

    action = models.GrowthAction(
        workspace_id=ws.id,
        decision_id=payload.decision_id,
        title=payload.title,
        action_type=payload.action_type,
        category=payload.category,
        priority=payload.priority,
        status="PENDING",
        owner_name=payload.owner_name,
        due_date=payload.due_date,
    )
    session.add(action)
    session.commit()
    session.refresh(action)

    return {
        "message": "Growth action created successfully",
        "action": {
            "id": action.id,
            "workspace_id": action.workspace_id,
            "decision_id": action.decision_id,
            "title": action.title,
            "action_type": action.action_type,
            "category": action.category,
            "priority": action.priority,
            "status": action.status,
            "owner_name": action.owner_name,
            "due_date": action.due_date,
            "notes": action.notes,
            "created_at": action.created_at.isoformat() if action.created_at else None,
            "completed_at": action.completed_at.isoformat() if action.completed_at else None,
        },
    }


@router.patch("/actions/{action_id}")
def update_growth_action(
    action_id: int,
    payload: ActionUpdateIn,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    """Updates a growth action's status, notes, due date, or owner."""
    action = session.query(models.GrowthAction).filter_by(id=action_id).first()
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action {action_id} not found",
        )
    if action.workspace.project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this action",
        )

    if payload.status is not None:
        action.status = payload.status
        if payload.status == "COMPLETED" and not action.completed_at:
            action.completed_at = datetime.now(timezone.utc)
        elif payload.status != "COMPLETED":
            action.completed_at = None

    if payload.notes is not None:
        action.notes = payload.notes
    if payload.due_date is not None:
        action.due_date = payload.due_date
    if payload.owner_name is not None:
        action.owner_name = payload.owner_name

    session.commit()
    session.refresh(action)

    return {
        "message": "Action updated successfully",
        "action": {
            "id": action.id,
            "workspace_id": action.workspace_id,
            "decision_id": action.decision_id,
            "title": action.title,
            "action_type": action.action_type,
            "category": action.category,
            "priority": action.priority,
            "status": action.status,
            "owner_name": action.owner_name,
            "due_date": action.due_date,
            "notes": action.notes,
            "created_at": action.created_at.isoformat() if action.created_at else None,
            "completed_at": action.completed_at.isoformat() if action.completed_at else None,
        },
    }
