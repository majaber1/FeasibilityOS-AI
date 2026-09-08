"""
Company Financial Profile API: period financial statements for an existing
business (Entry 4: "لدي شركة وأريد تمويل مشروع أو توسع").

One row per (study, period). Every metric is optional -- a metric the user
doesn't provide stays unknown, it is never defaulted to zero or estimated
(the Company Financial Health engine, a later phase, must report
MISSING_DATA rather than a fabricated ratio when a required metric is
absent). `source` records how trustworthy the whole period is; an optional
document_id traces it to a specific uploaded document.

PUT upserts by period (creates on first call for that period, partially
updates on later calls). Ownership follows the study's parent project
owner. Requires persistence (DATABASE_URL).
"""
from __future__ import annotations

from typing import List, Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.db import DB_ENABLED, SessionLocal
from app.api.auth import UserOut, get_current_user
from app.services.study_access import owned_study_or_error

router = APIRouter(prefix="/studies/{study_id}/financial-periods", tags=["company-financial-profile"])

SOURCE_VALUES = (
    "financial_statement", "bank_statement", "user_confirmed",
    "audited_statement", "management_account", "unverified",
)

_METRIC_FIELDS = (
    "revenue", "gross_profit", "ebitda", "operating_profit", "net_profit", "cash",
    "current_assets", "current_liabilities", "total_assets", "total_liabilities",
    "equity", "existing_debt", "annual_debt_service", "accounts_receivable",
    "inventory", "capital_expenditure",
)


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Company financial profile requires persistence (database not configured).")
    return SessionLocal()


class FinancialPeriodIn(BaseModel):
    model_config = {"extra": "forbid"}

    source: Optional[str] = None
    document_id: Optional[int] = None
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    ebitda: Optional[float] = None
    operating_profit: Optional[float] = None
    net_profit: Optional[float] = None
    cash: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    equity: Optional[float] = None
    existing_debt: Optional[float] = None
    annual_debt_service: Optional[float] = None
    accounts_receivable: Optional[float] = None
    inventory: Optional[float] = None
    capital_expenditure: Optional[float] = None
    interest_expense: Optional[float] = None

    @model_validator(mode="after")
    def _validate(self):
        if self.source is not None and self.source not in SOURCE_VALUES:
            raise ValueError(f"source must be one of {SOURCE_VALUES}")
        return self


class FinancialPeriodOut(BaseModel):
    id: int
    study_id: int
    period: str
    source: str
    document_id: Optional[int] = None
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    ebitda: Optional[float] = None
    operating_profit: Optional[float] = None
    net_profit: Optional[float] = None
    cash: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    equity: Optional[float] = None
    existing_debt: Optional[float] = None
    annual_debt_service: Optional[float] = None
    accounts_receivable: Optional[float] = None
    inventory: Optional[float] = None
    capital_expenditure: Optional[float] = None
    interest_expense: Optional[float] = None

    model_config = {"from_attributes": True}


def _get_period_or_404(db, models, study_id: int, period: str):
    row = (
        db.query(models.CompanyFinancialPeriod)
        .filter_by(study_id=study_id, period=unquote(period))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No financial data recorded for this period")
    return row


@router.get("/", response_model=List[FinancialPeriodOut])
def list_financial_periods(study_id: int, user: UserOut = Depends(get_current_user)):
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
        return rows
    finally:
        db.close()


@router.get("/{period}", response_model=FinancialPeriodOut)
def get_financial_period(study_id: int, period: str, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        return _get_period_or_404(db, models, study_id, period)
    finally:
        db.close()


@router.put("/{period}", response_model=FinancialPeriodOut)
def upsert_financial_period(study_id: int, period: str, data: FinancialPeriodIn, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        period_value = unquote(period)

        if data.document_id is not None:
            document = db.get(models.Document, data.document_id)
            if document is None or document.study_id != study_id:
                raise HTTPException(status_code=422, detail="document_id must reference a document already linked to this study")

        row = db.query(models.CompanyFinancialPeriod).filter_by(study_id=study_id, period=period_value).first()
        changes = data.model_dump(exclude_unset=True)
        if row is None:
            row = models.CompanyFinancialPeriod(
                study_id=study_id, period=period_value, created_by=user.id,
                source=changes.pop("source", None) or "unverified",
                **changes,
            )
            db.add(row)
        else:
            for field, value in changes.items():
                setattr(row, field, value)
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


@router.delete("/{period}", status_code=204)
def delete_financial_period(study_id: int, period: str, user: UserOut = Depends(get_current_user)):
    from app import models

    db = _require_db()
    try:
        owned_study_or_error(db, models, study_id, user)
        row = _get_period_or_404(db, models, study_id, period)
        db.delete(row)
        db.commit()
        return None
    finally:
        db.close()
