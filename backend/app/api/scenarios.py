"""
Scenario Engine API (Phase 12): deterministic Conservative/Base/Optimistic
runs built from explicit assumption overrides, never a blanket +/-% shock.

POST computes a scenario by taking the study's current active assumptions
(the same canonical keys used by app.services.financial_projection),
layering the caller's explicit overrides on top, and running them through
the exact same deterministic engine as
POST /feasibility/{id}/compute-from-assumptions (Phase 10). The study's
actual assumptions are never modified -- overrides exist only for the
scenario computation. The result is stored as an immutable snapshot
(financial_result_snapshot) alongside exactly which values (base assumption
or override) produced it (source_assumption_values) and which calculation
engine version computed it (calculation_version), so a scenario stays
interpretable even after the study's assumptions later change.

Ownership follows the study's parent project owner. Requires persistence
(DATABASE_URL).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.db import DB_ENABLED, SessionLocal
from app.api.auth import UserOut, get_current_user
from app.services.study_access import owned_study_or_error
from app.services.financial_projection import (
    ALL_ASSUMPTION_KEYS,
    CALCULATION_VERSION,
    missing_required_keys,
    project_cash_flows,
)

# financial-engine/ lives at the repo root, three levels above this file
# (same convention as app/api/feasibility.py).
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "financial-engine"))
from calculator import evaluate_feasibility, sensitivity_analysis  # noqa: E402

router = APIRouter(prefix="/studies/{study_id}/scenarios", tags=["scenarios"])

SCENARIO_TYPES = ("CONSERVATIVE", "BASE", "OPTIMISTIC")


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Scenarios require persistence (database not configured).")
    return SessionLocal()


class ScenarioCreate(BaseModel):
    scenario_type: str
    scenario_name: Optional[str] = Field(default=None, max_length=200)
    assumption_overrides: Dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate(self):
        if self.scenario_type not in SCENARIO_TYPES:
            raise ValueError(f"scenario_type must be one of {SCENARIO_TYPES}")
        unknown = set(self.assumption_overrides) - set(ALL_ASSUMPTION_KEYS)
        if unknown:
            raise ValueError(f"Unknown assumption override keys: {sorted(unknown)}. Allowed: {ALL_ASSUMPTION_KEYS}")
        return self


class ScenarioOut(BaseModel):
    id: int
    study_id: int
    scenario_type: str
    scenario_name: str
    assumption_overrides: Dict[str, float]
    source_assumption_values: Dict[str, dict]
    financial_result_snapshot: dict
    calculation_version: str

    model_config = {"from_attributes": True}


def _base_assumption_values(db, models, study_id: int) -> dict[str, dict]:
    """Active StudyAssumption rows for the canonical keys, as {key: {id, version, value}}."""
    rows = (
        db.query(models.StudyAssumption)
        .filter(
            models.StudyAssumption.study_id == study_id,
            models.StudyAssumption.is_active.is_(True),
            models.StudyAssumption.key.in_(ALL_ASSUMPTION_KEYS),
        )
        .all()
    )
    return {row.key: {"id": row.id, "version": row.version, "value": row.value_number} for row in rows}


@router.post("/", response_model=ScenarioOut, status_code=201)
def create_scenario(study_id: int, data: ScenarioCreate, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)

        base = _base_assumption_values(db, models, study_id)
        values = {key: entry["value"] for key, entry in base.items()}
        values.update(data.assumption_overrides)

        missing = missing_required_keys(values)
        if missing:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "missing_assumptions",
                    "message": "Record or override these before running a scenario: " + ", ".join(missing),
                    "missing": missing,
                },
            )

        investment, cash_flows, discount_rate = project_cash_flows(values)

        res = evaluate_feasibility(investment, cash_flows, discount_rate)
        sens = sensitivity_analysis(investment, cash_flows, discount_rate)

        source_values = {
            key: (
                {"origin": "override", "value": values[key]}
                if key in data.assumption_overrides
                else {"origin": "assumption", "value": values[key], **base[key]}
            )
            for key in values
        }

        row = models.ScenarioRun(
            study_id=study_id,
            created_by=user.id,
            scenario_type=data.scenario_type,
            scenario_name=data.scenario_name or data.scenario_type.title(),
            assumption_overrides=data.assumption_overrides,
            source_assumption_values=source_values,
            financial_result_snapshot={
                "investment": investment,
                "annual_cash_flows": cash_flows,
                "discount_rate": discount_rate,
                "roi_percent": res.roi_percent,
                "npv": res.npv_value,
                "irr": res.irr_value,
                "payback_years": res.payback_years,
                "verdict": res.verdict,
                "sensitivity": sens,
            },
            calculation_version=CALCULATION_VERSION,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


@router.get("/", response_model=List[ScenarioOut])
def list_scenarios(study_id: int, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        rows = (
            db.query(models.ScenarioRun)
            .filter(models.ScenarioRun.study_id == study_id)
            .order_by(models.ScenarioRun.id.desc())
            .all()
        )
        return rows
    finally:
        db.close()


@router.get("/compare", response_model=Dict[str, Optional[ScenarioOut]])
def compare_scenarios(study_id: int, user: UserOut = Depends(get_current_user)):
    """The latest run per scenario_type, for a side-by-side comparison."""
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        result: Dict[str, Optional[ScenarioOut]] = {}
        for scenario_type in SCENARIO_TYPES:
            row = (
                db.query(models.ScenarioRun)
                .filter(models.ScenarioRun.study_id == study_id, models.ScenarioRun.scenario_type == scenario_type)
                .order_by(models.ScenarioRun.id.desc())
                .first()
            )
            result[scenario_type] = row
        return result
    finally:
        db.close()
