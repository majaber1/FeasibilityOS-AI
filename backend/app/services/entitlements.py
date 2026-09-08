"""Demo-safe entitlement checks. No fake payment success."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.auth import UserOut
from app.db import DB_ENABLED
from app.models import ServiceEntitlement

KNOWN_SERVICES = (
    "feasibility",
    "financial_analysis",
    "proposal",
    "funding",
    "qualification",
    "opportunities",
    "franchise",
    "reports",
    "ideas",
)


def demo_entitlement(service_key: str) -> dict:
    return {
        "service_key": service_key,
        "enabled": True,
        "plan": "starter",
        "quota": None,
        "used": 0,
        "upgrade_required": False,
    }


def resolve_entitlement(db: Optional[Session], user: UserOut, service_key: str) -> dict:
    if service_key not in KNOWN_SERVICES:
        raise HTTPException(400, f"Unknown service: {service_key}")
    if not DB_ENABLED or db is None:
        return demo_entitlement(service_key)

    row = (
        db.query(ServiceEntitlement)
        .filter(ServiceEntitlement.user_id == user.id, ServiceEntitlement.service_key == service_key)
        .first()
    )
    if row is None:
        return demo_entitlement(service_key)
    enabled = bool(row.enabled)
    quota_exceeded = row.quota is not None and row.used >= row.quota
    return {
        "service_key": service_key,
        "enabled": enabled and not quota_exceeded,
        "plan": row.plan,
        "quota": row.quota,
        "used": row.used,
        "upgrade_required": (not enabled) or quota_exceeded,
    }


def require_service(db: Optional[Session], user: UserOut, service_key: str) -> dict:
    entitlement = resolve_entitlement(db, user, service_key)
    if entitlement["upgrade_required"] or not entitlement["enabled"]:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "upgrade_required",
                "service_key": service_key,
                "message": "This service is not enabled on the current plan. No payment was processed.",
            },
        )
    return entitlement
