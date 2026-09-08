"""In-app notifications and privacy-conscious product analytics.

Analytics events never store business content (names, descriptions, numbers).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db import DB_ENABLED
from app.models import AnalyticsEvent, Notification


def record_event(
    db: Optional[Session],
    *,
    user_id: Optional[int],
    event_type: str,
    service_key: Optional[str] = None,
    entity: Optional[str] = None,
    entity_id: Optional[int] = None,
) -> None:
    if not DB_ENABLED or db is None:
        return
    db.add(
        AnalyticsEvent(
            user_id=user_id,
            event_type=event_type,
            service_key=service_key,
            entity=entity,
            entity_id=entity_id,
            meta={"recorded_at": datetime.now(timezone.utc).isoformat()},
        )
    )


def notify(
    db: Optional[Session],
    *,
    user_id: int,
    kind: str,
    title_en: str,
    title_ar: str,
    body: Optional[str] = None,
    entity: Optional[str] = None,
    entity_id: Optional[int] = None,
) -> None:
    if not DB_ENABLED or db is None:
        return
    db.add(
        Notification(
            user_id=user_id,
            kind=kind,
            title_en=title_en,
            title_ar=title_ar,
            body=body,
            entity=entity,
            entity_id=entity_id,
        )
    )
