from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app import auth as security
from app.db import DB_ENABLED, SessionLocal, safe_backend
from app.api.auth import (
    ROLES,
    SUPPORTED_LOCALES,
    PasswordPolicyError,
    UserOut,
    _audit,
    _ensure_roles,
    _normalize_email,
    require_roles,
    validate_password_policy,
)

router = APIRouter(prefix="/admin", tags=["admin"])


class AuditEntry(BaseModel):
    id: int
    actor_id: Optional[int] = None
    action: str
    entity: Optional[str] = None
    entity_id: Optional[int] = None
    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    db_enabled: bool
    db_backend: str
    users: int = 0
    projects: int = 0
    studies: int = 0
    ideas: int = 0
    franchises: int = 0
    reports: int = 0
    multazim_requirements: int = 0
    recent_activity: List[AuditEntry] = []


class AdminCreateUserIn(BaseModel):
    """Strict payload for admin-provisioned accounts.

    ``extra="forbid"`` blocks privilege/internal fields (id, is_active,
    is_admin, is_superuser, organization_id, hashed_password, ...) from being
    smuggled in. Only an authenticated admin may reach this schema; the role
    may be any canonical role INCLUDING the privileged ones (admin,
    gov_reviewer) that public registration forbids.
    """

    model_config = {"extra": "forbid"}

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role_key: str
    full_name: Optional[str] = Field(default=None, max_length=200)
    locale: str = Field(default="ar")


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(user: UserOut = Depends(require_roles("admin"))):
    """Administrator dashboard: platform-wide counts and recent audit activity."""
    if not DB_ENABLED:
        return DashboardStats(db_enabled=False, db_backend=safe_backend())
    from app import models
    db = SessionLocal()
    try:
        def _count(model):
            try:
                return db.query(model).count()
            except Exception:
                return 0
        recent = (
            db.query(models.AuditLog)
            .order_by(models.AuditLog.id.desc())
            .limit(20)
            .all()
        )
        return DashboardStats(
            db_enabled=True,
            db_backend=safe_backend(),
            users=_count(models.User),
            projects=_count(models.Project),
            studies=_count(models.FeasibilityStudy),
            ideas=_count(models.IdeaBankEntry),
            franchises=_count(models.FranchiseOpportunity),
            reports=_count(models.Report),
            multazim_requirements=_count(models.MultazimRequirement),
            recent_activity=recent,
        )
    finally:
        db.close()


@router.get("/audit", response_model=List[AuditEntry])
def audit_log(limit: int = 50, user: UserOut = Depends(require_roles("admin"))):
    """Recent audit log entries (admin only)."""
    if not DB_ENABLED:
        return []
    from app import models
    db = SessionLocal()
    try:
        limit = max(1, min(limit, 200))
        return (
            db.query(models.AuditLog)
            .order_by(models.AuditLog.id.desc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


@router.get("/users", response_model=List[UserOut])
def list_users(
    limit: int = 100,
    actor: UserOut = Depends(require_roles("admin")),
):
    """List accounts for protected administration; never returns hashes."""
    if not DB_ENABLED:
        return []
    from app import models
    db = SessionLocal()
    try:
        limit = max(1, min(limit, 500))
        rows = db.query(models.User).order_by(models.User.id.desc()).limit(limit).all()
        return [
            UserOut(id=row.id, email=row.email, full_name=row.full_name,
                    role_key=row.role_key, locale=row.locale,
                    email_verified=row.email_verified_at is not None)
            for row in rows
        ]
    finally:
        db.close()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    data: AdminCreateUserIn,
    actor: UserOut = Depends(require_roles("admin")),
):
    """Admin-only provisioning of accounts, including privileged roles.

    Access control (via require_roles("admin")):
      - anonymous / missing token -> 401
      - authenticated non-admin   -> 403
      - admin                     -> may create allowed roles

    Guarantees: strict schema (extra forbidden), role validated against the
    canonical catalog, password policy enforced, duplicate normalized email
    -> 409, password hash never returned, and an audit record is written. There
    is NO default/bootstrap credential and an admin cannot use this to modify or
    self-promote an existing account -- it only CREATES new users.
    """
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Auth requires persistence")

    if data.role_key not in ROLES:
        raise HTTPException(status_code=422, detail="Unknown role_key")
    if data.locale not in SUPPORTED_LOCALES:
        raise HTTPException(status_code=422, detail="Unsupported locale")
    try:
        validate_password_policy(data.password)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    email = _normalize_email(str(data.email))

    from app import models
    db = SessionLocal()
    try:
        _ensure_roles(db)
        if db.query(models.User).filter_by(email=email).first():
            raise HTTPException(status_code=409, detail="Email already registered")
        user = models.User(
            email=email,
            hashed_password=security.hash_password(data.password),
            full_name=data.full_name,
            role_key=data.role_key,
            locale=data.locale,
            is_active=True,
            email_verified_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        _audit(db, actor.id, "admin.user.create", "user", user.id)
        return UserOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role_key=user.role_key,
            locale=user.locale,
            email_verified=True,
        )
    finally:
        db.close()
