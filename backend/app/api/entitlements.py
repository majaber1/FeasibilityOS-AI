from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.api.auth import UserOut, get_current_user
from app.db import DB_ENABLED, get_db
from app.models import ServiceEntitlement

router = APIRouter(prefix="/entitlements", tags=["entitlements"])

SERVICES = [
    "feasibility", "financial_analysis", "proposal", "funding",
    "qualification", "opportunities", "franchise", "reports",
    "ideas",
]


class EntitlementOut(BaseModel):
    service_key: str
    enabled: bool
    plan: str
    quota: Optional[int]
    used: int

    model_config = {"from_attributes": True}


def _demo_entitlements() -> list[EntitlementOut]:
    return [
        EntitlementOut(service_key=s, enabled=True, plan="starter", quota=None, used=0)
        for s in SERVICES
    ]


@router.get("/", response_model=list[EntitlementOut])
def list_entitlements(
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not DB_ENABLED:
        return _demo_entitlements()

    records = (
        db.query(ServiceEntitlement)
        .filter(ServiceEntitlement.user_id == user.id)
        .all()
    )

    if not records:
        return _demo_entitlements()

    existing_keys = {r.service_key for r in records}
    result = [EntitlementOut.model_validate(r) for r in records]
    for s in SERVICES:
        if s not in existing_keys:
            result.append(EntitlementOut(service_key=s, enabled=True, plan="starter", quota=None, used=0))
    return result
