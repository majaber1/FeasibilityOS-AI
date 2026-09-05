"""
Company Financial Health API (Phase 11): deterministic ratios computed only
from a study's recorded CompanyFinancialPeriod rows (Phase 5). No AI, no
invented values -- see app.services.financial_health for the calculation
rules and the CALCULATED/MISSING_DATA/NOT_APPLICABLE contract every metric
returns.

Periods are ordered lexicographically by their `period` label (e.g.
"FY2024" < "FY2025"), which only produces a meaningful "prior period" when
period labels are named consistently by the caller -- documented, not
inferred.

Ownership follows the study's parent project owner. Requires persistence
(DATABASE_URL).
"""
from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import DB_ENABLED, SessionLocal
from app.api.auth import UserOut, get_current_user
from app.services.study_access import owned_study_or_error
from app.services.financial_health import Metric, compute_metrics, summarize

router = APIRouter(prefix="/studies/{study_id}/financial-health", tags=["financial-health"])

_METRIC_FIELDS = (
    "revenue", "gross_profit", "ebitda", "operating_profit", "net_profit", "cash",
    "current_assets", "current_liabilities", "total_assets", "total_liabilities",
    "equity", "existing_debt", "annual_debt_service", "accounts_receivable",
    "inventory", "capital_expenditure", "interest_expense",
)


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Financial health requires persistence (database not configured).")
    return SessionLocal()


class MetricOut(BaseModel):
    status: str
    value: Optional[float] = None
    unit: Optional[str] = None


class FinancialHealthOut(BaseModel):
    study_id: int
    period: str
    prior_period: Optional[str] = None
    metrics: Dict[str, MetricOut]
    summary: Dict[str, str]
    data_status: str = "CALCULATED"  # NO_PERIODS_RECORDED when no CompanyFinancialPeriod rows exist


def _row_to_dict(row) -> dict:
    return {field: getattr(row, field) for field in _METRIC_FIELDS}


def _metrics_out(metrics: dict[str, Metric]) -> Dict[str, MetricOut]:
    return {key: MetricOut(status=metric.status, value=metric.value, unit=metric.unit) for key, metric in metrics.items()}


@router.get("/", response_model=FinancialHealthOut)
def get_financial_health(study_id: int, period: Optional[str] = None, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        rows = (
            db.query(models.CompanyFinancialPeriod)
            .filter(models.CompanyFinancialPeriod.study_id == study_id)
            .order_by(models.CompanyFinancialPeriod.period.asc())
            .all()
        )
        if not rows:
            # Return 200 with explicit NOT_AVAILABLE semantics. Missing financial data
            # is a valid domain state (user hasn't recorded any periods yet) — not an error.
            # The browser must not see a 404 during normal navigation.
            metrics = compute_metrics({})
            return FinancialHealthOut(
                study_id=study_id,
                period="NO_DATA",
                prior_period=None,
                metrics=_metrics_out(metrics),
                summary=summarize(metrics),
                data_status="NO_PERIODS_RECORDED",
            )

        if period is not None:
            matches = [r for r in rows if r.period == period]
            if not matches:
                raise HTTPException(status_code=404, detail=f"No financial data recorded for period '{period}'")
            target = matches[0]
        else:
            target = rows[-1]  # latest period in lexicographic order

        index = rows.index(target)
        prior = rows[index - 1] if index > 0 else None

        metrics = compute_metrics(_row_to_dict(target), _row_to_dict(prior) if prior else None)
        summary = summarize(metrics)

        return FinancialHealthOut(
            study_id=study_id,
            period=target.period,
            prior_period=prior.period if prior else None,
            metrics=_metrics_out(metrics),
            summary=summary,
        )
    finally:
        db.close()
