import sys
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

# financial-engine/ lives at the repo root, one level above backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "financial-engine"))
from calculator import evaluate_feasibility, sensitivity_analysis  # noqa: E402

router = APIRouter(prefix="/financial", tags=["financial"])


class FeasibilityRequest(BaseModel):
    investment: float = Field(..., gt=0)
    annual_cash_flows: List[float] = Field(..., min_length=1)
    discount_rate: float = Field(default=0.10, ge=0, le=1)


_IRR_UNAVAILABLE = (
    "IRR cannot be calculated for these cash flows "
    "(no valid internal rate of return in range)."
)


class FeasibilityResponse(BaseModel):
    roi_percent: Optional[float]
    payback_years: Optional[float]
    npv: Optional[float]
    irr_percent: Optional[float]
    irr_display: str
    irr_available: bool
    verdict: str


@router.post("/evaluate", response_model=FeasibilityResponse)
def evaluate(req: FeasibilityRequest):
    result = evaluate_feasibility(req.investment, req.annual_cash_flows, req.discount_rate)
    irr_pct = round(result.irr_value * 100, 2) if result.irr_value is not None else None
    return FeasibilityResponse(
        roi_percent=round(result.roi_percent, 2) if result.roi_percent is not None else None,
        payback_years=round(result.payback_years, 2) if result.payback_years is not None else None,
        npv=round(result.npv_value, 2) if result.npv_value is not None else None,
        irr_percent=irr_pct,
        irr_display=f"{irr_pct:.1f}%" if irr_pct is not None else _IRR_UNAVAILABLE,
        irr_available=result.irr_value is not None,
        verdict=result.verdict,
    )


@router.post("/sensitivity")
def sensitivity(req: FeasibilityRequest):
    return sensitivity_analysis(req.investment, req.annual_cash_flows, req.discount_rate)
