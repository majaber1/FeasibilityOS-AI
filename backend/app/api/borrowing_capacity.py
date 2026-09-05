"""
Borrowing Capacity API (Phase 15): a documented, deterministic *range*
estimate of additional debt capacity computed from a study's recorded
CompanyFinancialPeriod data (Phase 5). See
app.services.borrowing_capacity for the formulas, thresholds, and the
explicit disclaimer that this is a screening estimate, never an approval.

Stateless, like Financial Health (Phase 11): a cheap, always-current read
over the latest (or an explicit ?period=) financial period. Ownership
follows the study's parent project owner. Requires persistence
(DATABASE_URL).
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import DB_ENABLED, SessionLocal
from app.api.auth import UserOut, get_current_user
from app.services.study_access import owned_study_or_error
from app.services.borrowing_capacity import estimate_borrowing_capacity

router = APIRouter(prefix="/studies/{study_id}/borrowing-capacity", tags=["borrowing-capacity"])


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Borrowing capacity requires persistence (database not configured).")
    return SessionLocal()


class BorrowingCapacityOut(BaseModel):
    study_id: int
    period: str
    status: str
    base_capacity: Optional[float] = None
    stress_capacity: Optional[float] = None
    primary_constraint: Optional[str] = None
    secondary_constraint: Optional[str] = None
    financial_support: str
    missing_inputs: List[str]
    missing_underwriting_inputs: List[str]
    assumptions_used: dict
    disclaimer: str = "Estimate only, not an approval. Final financing decisions require lender underwriting."


@router.get("/", response_model=BorrowingCapacityOut)
def get_borrowing_capacity(study_id: int, period: Optional[str] = None, user: UserOut = Depends(get_current_user)):
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
            # Return 200 with explicit INSUFFICIENT_DATA semantics. Missing financial data
            # is a valid domain state (user hasn't recorded company periods yet) — not an error.
            # The browser must not see a 404 during normal navigation.
            return BorrowingCapacityOut(
                study_id=study_id,
                period="NO_DATA",
                status="INSUFFICIENT_DATA",
                base_capacity=None,
                stress_capacity=None,
                primary_constraint=None,
                secondary_constraint=None,
                financial_support="لا توجد فترات مالية مسجلة لهذه الدراسة. أضف بيانات الفترات المالية للحصول على تقدير القدرة الاقتراضية.",
                missing_inputs=["all_company_financial_period_data"],
                missing_underwriting_inputs=["all_company_financial_period_data"],
                assumptions_used={},
            )

        if period is not None:
            matches = [r for r in rows if r.period == period]
            if not matches:
                raise HTTPException(status_code=404, detail=f"No financial data recorded for period '{period}'")
            target = matches[0]
        else:
            target = rows[-1]

        result = estimate_borrowing_capacity(
            ebitda=target.ebitda, existing_debt=target.existing_debt, annual_debt_service=target.annual_debt_service
        )
        return BorrowingCapacityOut(study_id=study_id, period=target.period, **result)
    finally:
        db.close()
