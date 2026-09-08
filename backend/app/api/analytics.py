from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import UserOut, get_current_user
from app.db import get_db
from app.services.platform_events import record_event

router = APIRouter(prefix="/analytics", tags=["analytics"])

ALLOWED_EVENTS = {
    "tool_opened",
    "workflow_started",
    "workflow_completed",
    "report_generated",
    "service_linked",
}


class AnalyticsIn(BaseModel):
    event_type: str = Field(..., max_length=100)
    service_key: Optional[str] = Field(default=None, max_length=50)
    entity: Optional[str] = Field(default=None, max_length=100)
    entity_id: Optional[int] = None


@router.post("/events", status_code=202)
def track_event(
    body: AnalyticsIn,
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.event_type not in ALLOWED_EVENTS:
        return {"accepted": False, "reason": "event_type_not_allowlisted"}
    record_event(
        db,
        user_id=user.id,
        event_type=body.event_type,
        service_key=body.service_key,
        entity=body.entity,
        entity_id=body.entity_id,
    )
    db.commit()
    return {"accepted": True}
