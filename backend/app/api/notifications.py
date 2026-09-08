from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import UserOut, get_current_user
from app.db import DB_ENABLED, get_db
from app.models import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: int
    kind: str
    title_en: str
    title_ar: str
    body: Optional[str] = None
    entity: Optional[str] = None
    entity_id: Optional[int] = None
    is_read: bool

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[NotificationOut])
def list_notifications(
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not DB_ENABLED:
        return []
    return (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.id.desc())
        .limit(50)
        .all()
    )


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: int,
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not DB_ENABLED:
        raise HTTPException(503, "Database unavailable")
    row = db.get(Notification, notification_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    row.is_read = True
    db.commit()
    db.refresh(row)
    return row
