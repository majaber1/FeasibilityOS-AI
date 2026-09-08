"""
Authentication & RBAC router: register, login, and profile.

Requires persistence (DATABASE_URL). In demo mode it returns 503 rather than
faking accounts, so nobody believes a login persisted when it did not.

Security note (public registration):
ROLES is the *canonical* RBAC catalog used to seed the roles table so user
foreign keys are always valid. It is NOT the set of roles a member of the
public may self-assign. Public /auth/register only accepts
PUBLIC_REGISTRATION_ROLES; privileged roles (admin, gov_reviewer) can never be
obtained through public registration and must be provisioned through the
authenticated admin-only endpoint (POST /admin/users) or a controlled DB
process -- never through this public router.
"""
from __future__ import annotations

import os
import re
from typing import Iterable, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from app import auth as security
from app.db import DB_ENABLED, SessionLocal

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)

# Canonical roles (key -> EN/AR label). Seeded on demand so user FKs are valid.
# NOTE: this is the full internal catalog, NOT the public-registration allowlist.
ROLES = {
    "entrepreneur": ("Entrepreneur", "رائد أعمال"),
    "consultant": ("Consultant", "مستشار"),
    "investor": ("Investor", "مستثمر"),
    "franchise_owner": ("Franchise Owner", "مانح امتياز"),
    "gov_reviewer": ("Government Reviewer", "مراجع حكومي"),
    "admin": ("Administrator", "مدير النظام"),
}

# Roles a member of the public may self-assign at registration time. Everything
# else in ROLES is privileged/internal and must never be reachable via the
# public endpoint.
PUBLIC_REGISTRATION_ROLES = frozenset(
    {"entrepreneur", "consultant", "investor", "franchise_owner"}
)
PRIVILEGED_ROLES = frozenset(set(ROLES) - PUBLIC_REGISTRATION_ROLES)  # admin, gov_reviewer

SUPPORTED_LOCALES = frozenset({"ar", "en"})
DEFAULT_ROLE = "entrepreneur"

# --- Password policy (subscription-free, no external services) --------------
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
# A small blocklist of trivially guessable passwords. Comparison is done
# case-insensitively and also strips trailing digits so "Password123" and
# "password" are both rejected.
_COMMON_PASSWORDS = frozenset(
    {
        "password",
        "passw0rd",
        "12345678",
        "123456789",
        "1234567890",
        "qwerty",
        "qwerty123",
        "qwertyuiop",
        "letmein",
        "welcome",
        "admin",
        "administrator",
        "iloveyou",
        "abc12345",
        "changeme",
        "secret",
        "monkey",
        "dragon",
    }
)


class PasswordPolicyError(ValueError):
    """Raised when a candidate password fails the policy. Message is safe to
    surface to the client (it never echoes the password)."""


def validate_password_policy(password: str) -> None:
    """Enforce a reasonable password policy at account-creation boundaries.

    Rules: length 8-128, at least one letter, at least one digit, not a common/
    trivial password. Symbols are allowed but not required (no arbitrary
    composition rules). Raises PasswordPolicyError with a safe message; never
    includes the password itself in the error.

    NOTE: this is applied at registration / password-change only, NEVER at
    login (so policy tightening cannot lock out existing valid accounts).
    """
    if not isinstance(password, str):
        raise PasswordPolicyError("Password must be a string")
    if len(password) < PASSWORD_MIN_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
        )
    if len(password) > PASSWORD_MAX_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at most {PASSWORD_MAX_LENGTH} characters"
        )
    if not re.search(r"[A-Za-z]", password):
        raise PasswordPolicyError("Password must contain at least one letter")
    if not re.search(r"[0-9]", password):
        raise PasswordPolicyError("Password must contain at least one number")
    lowered = password.strip().lower()
    stripped = lowered.rstrip("0123456789")
    if lowered in _COMMON_PASSWORDS or (stripped and stripped in _COMMON_PASSWORDS):
        raise PasswordPolicyError("Password is too common; choose a stronger password")


def _coerce_subject(raw) -> Optional[int]:
    """Safely turn a JWT ``sub`` claim into a positive user id.

    Any malformed value (None, "", non-numeric, negative, zero, wrong type)
    returns None so the caller can respond 401 WITHOUT letting a ValueError or
    TypeError bubble up as an HTTP 500. Tokens we mint always carry a positive
    integer id as a string, so a value that fails here is never one we issued.
    """
    if raw is None:
        return None
    if isinstance(raw, bool):  # bool is a subclass of int; reject explicitly
        return None
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return value


def _normalize_email(email: str) -> str:
    """Canonicalize an email for storage and lookup so uniqueness is
    case-insensitive. RFC technically allows a case-sensitive local part, but
    for account identity we treat addresses case-insensitively (and trim
    surrounding whitespace) so "A@X.com" and "a@x.com" are the same account."""
    return email.strip().lower()


class RegisterIn(BaseModel):
    # Strict: reject any unexpected field (e.g. is_admin, is_staff, is_superuser,
    # permissions, is_active, organization_id, owner_id) instead of silently
    # ignoring it. Privilege can never be smuggled through the public payload.
    model_config = {"extra": "forbid"}

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=200)
    role_key: str = Field(default=DEFAULT_ROLE)
    locale: str = Field(default="ar")


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role_key: str
    locale: str
    email_verified: bool = False


class EmailActionIn(BaseModel):
    email: EmailStr


class TokenIn(BaseModel):
    token: str = Field(..., min_length=20, max_length=200)


class PasswordResetIn(TokenIn):
    password: str = Field(..., min_length=8, max_length=128)


class ProfileUpdateIn(BaseModel):
    model_config = {"extra": "forbid"}

    full_name: Optional[str] = Field(default=None, max_length=200)
    locale: Optional[str] = None


class PasswordChangeIn(BaseModel):
    model_config = {"extra": "forbid"}

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class ActionAck(BaseModel):
    accepted: bool = True
    delivery_configured: bool = False
    dev_token: Optional[str] = None


def _require_db():
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Auth requires persistence (DATABASE_URL not set).")
    return SessionLocal()


def _ensure_roles(db) -> None:
    """Seed the full canonical role catalog (including privileged roles) so user
    foreign keys are valid. This is unrelated to the public-registration
    allowlist: seeding admin/gov_reviewer here does NOT make them publicly
    self-assignable."""
    from app import models

    existing = {r.key for r in db.query(models.Role).all()}
    for key, (en, ar) in ROLES.items():
        if key not in existing:
            db.add(models.Role(key=key, name_en=en, name_ar=ar, permissions={}))
    db.commit()


def _audit(db, actor_id: Optional[int], action: str, entity: str, entity_id: Optional[int]) -> None:
    from app import models

    db.add(models.AuditLog(actor_id=actor_id, action=action, entity=entity, entity_id=entity_id, meta={}))
    db.commit()


def _verification_required() -> bool:
    configured = os.getenv("REQUIRE_EMAIL_VERIFICATION")
    if configured is not None:
        return configured.strip().lower() in {"1", "true", "yes", "on"}
    # Email verification is an opt-in production capability.  Treating it as
    # implicitly enabled made a fresh production deployment impossible to use:
    # registration returned 503 until SMTP was configured, even though the rest
    # of the account flow and durable database were healthy.  Operators that
    # require verification still enable it explicitly together with SMTP.
    return False


def _is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").strip().lower() in {"production", "prod"}


def _email_delivery_configured() -> bool:
    """Return whether account-action email has a usable delivery target.

    Registration must not create an account that production immediately locks
    behind an undeliverable verification token. Development can still expose
    tokens explicitly for local testing.
    """
    return bool(os.getenv("SMTP_HOST", "").strip() and os.getenv("SMTP_FROM", "").strip())


def _expose_dev_token(raw: Optional[str]) -> Optional[str]:
    production = os.getenv("ENVIRONMENT", "development").strip().lower() in {"production", "prod"}
    enabled = os.getenv("EXPOSE_ACCOUNT_TOKENS", "false").strip().lower() in {"1", "true", "yes"}
    return raw if raw and enabled and not production else None


def _send_token(db, models, user, purpose: str) -> tuple[bool, str]:
    from app.services.account_security import issue_token, public_account_url, send_account_email

    minutes = 24 * 60 if purpose == "verify_email" else 30
    path = "/verify-email" if purpose == "verify_email" else "/reset-password"
    raw = issue_token(db, models, user.id, purpose, minutes)
    delivered = False
    try:
        delivered = send_account_email(user.email, purpose, public_account_url(path, raw), user.locale)
    except Exception:
        # Do not leak SMTP failures or turn account creation into a 500. The
        # monitoring log records only delivery state, never the token.
        delivered = False
    return delivered, raw


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: RegisterIn, request: Request):
    from app import models
    from app.services.rate_limit import client_key, enforce
    enforce(client_key(request, "register", str(data.email)), 5, 3600)

    if _is_production() and _verification_required() and not _email_delivery_configured():
        raise HTTPException(
            status_code=503,
            detail="Account registration is temporarily unavailable because email delivery is not configured",
        )

    # Public registration may only assign a public role. Reject privileged roles
    # explicitly (403) and unknown roles (422) BEFORE opening a DB session, so a
    # rejected request never creates a user row or an audit record.
    if data.role_key in PRIVILEGED_ROLES:
        raise HTTPException(status_code=403, detail="This role cannot be self-assigned")
    if data.role_key not in PUBLIC_REGISTRATION_ROLES:
        raise HTTPException(status_code=422, detail="Unknown role_key")
    if data.locale not in SUPPORTED_LOCALES:
        raise HTTPException(status_code=422, detail="Unsupported locale")

    # Meaningful password policy (length 8 alone is NOT sufficient).
    try:
        validate_password_policy(data.password)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    email = _normalize_email(str(data.email))

    db = _require_db()
    try:
        _ensure_roles(db)
        if db.query(models.User).filter_by(email=email).first():
            raise HTTPException(status_code=409, detail="Email already registered")
        user = models.User(
            email=email,
            hashed_password=security.hash_password(data.password),
            full_name=data.full_name,
            role_key=data.role_key,  # validated public role only
            locale=data.locale,
            email_verified_at=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        _send_token(db, models, user, "verify_email")
        _audit(db, user.id, "user.register", "user", user.id)
        return UserOut(id=user.id, email=user.email, full_name=user.full_name,
                       role_key=user.role_key, locale=user.locale, email_verified=False)
    finally:
        db.close()


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, request: Request):
    from app import models
    from app.services.rate_limit import client_key, enforce
    enforce(client_key(request, "login", str(data.email)), 10, 300)

    db = _require_db()
    try:
        user = db.query(models.User).filter_by(email=_normalize_email(str(data.email))).first()
        if not user or not security.verify_password(data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account disabled")
        if _verification_required() and user.email_verified_at is None:
            raise HTTPException(status_code=403, detail="Email verification required")
        token = security.create_access_token(subject=user.id, extra={"role": user.role_key})
        _audit(db, user.id, "user.login", "user", user.id)
        return TokenOut(access_token=token)
    finally:
        db.close()


def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)):
    from app import models

    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = security.decode_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    # Never let a malformed/negative/non-numeric subject raise a 500.
    subject = _coerce_subject(payload.get("sub"))
    if subject is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Auth requires persistence")
    db = SessionLocal()
    try:
        user = db.get(models.User, subject)
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found")
        return UserOut(id=user.id, email=user.email, full_name=user.full_name,
                       role_key=user.role_key, locale=user.locale,
                       email_verified=user.email_verified_at is not None)
    finally:
        db.close()


def require_roles(*allowed: str):
    def _dep(user: UserOut = Depends(get_current_user)) -> UserOut:
        if user.role_key not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return _dep


@router.get("/me", response_model=UserOut)
def me(user: UserOut = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(data: ProfileUpdateIn, user: UserOut = Depends(get_current_user)):
    """Update only safe, user-owned profile fields; role/email remain controlled."""
    from app import models

    if data.locale is not None and data.locale not in SUPPORTED_LOCALES:
        raise HTTPException(status_code=422, detail="Unsupported locale")
    db = _require_db()
    try:
        row = db.get(models.User, user.id)
        if row is None or not row.is_active:
            raise HTTPException(status_code=401, detail="User not found")
        if "full_name" in data.model_fields_set:
            normalized_name = data.full_name.strip() if data.full_name else None
            row.full_name = normalized_name or None
        if data.locale is not None:
            row.locale = data.locale
        db.commit()
        db.refresh(row)
        _audit(db, row.id, "user.profile.update", "user", row.id)
        return UserOut(
            id=row.id, email=row.email, full_name=row.full_name,
            role_key=row.role_key, locale=row.locale,
            email_verified=row.email_verified_at is not None,
        )
    finally:
        db.close()


@router.post("/password/change", response_model=ActionAck)
def change_password(
    data: PasswordChangeIn,
    request: Request,
    user: UserOut = Depends(get_current_user),
):
    """Change a signed-in user's password after re-authenticating them."""
    from app import models
    from app.services.rate_limit import client_key, enforce

    enforce(client_key(request, "password_change", str(user.id)), 5, 3600)
    try:
        validate_password_policy(data.new_password)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if data.current_password == data.new_password:
        raise HTTPException(status_code=422, detail="New password must be different")

    db = _require_db()
    try:
        row = db.get(models.User, user.id)
        if row is None or not row.is_active:
            raise HTTPException(status_code=401, detail="User not found")
        if not security.verify_password(data.current_password, row.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        row.hashed_password = security.hash_password(data.new_password)
        # Any outstanding reset links should no longer be usable after an
        # authenticated password change.
        db.query(models.AccountToken).filter(
            models.AccountToken.user_id == row.id,
            models.AccountToken.purpose == "reset_password",
            models.AccountToken.consumed_at.is_(None),
        ).delete(synchronize_session=False)
        db.commit()
        _audit(db, row.id, "user.password.change", "user", row.id)
        return ActionAck()
    finally:
        db.close()


@router.post("/verification/request", response_model=ActionAck, status_code=202)
def request_verification(data: EmailActionIn, request: Request):
    """Resend verification without revealing whether an account exists."""
    from app.services.rate_limit import client_key, enforce
    enforce(client_key(request, "verify_request", str(data.email)), 5, 900)
    db = _require_db()
    try:
        from app import models
        user = db.query(models.User).filter_by(email=_normalize_email(str(data.email))).first()
        delivered, raw = (False, None)
        if user and user.is_active and user.email_verified_at is None:
            delivered, raw = _send_token(db, models, user, "verify_email")
        return ActionAck(delivery_configured=delivered, dev_token=_expose_dev_token(raw))
    finally:
        db.close()


@router.post("/verification/confirm", response_model=ActionAck)
def confirm_verification(data: TokenIn):
    from app import models
    from app.services.account_security import consume_token, utc_now_naive
    db = _require_db()
    try:
        row = consume_token(db, models, data.token, "verify_email")
        if row is None:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        user = db.get(models.User, row.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        user.email_verified_at = utc_now_naive()
        db.commit()
        _audit(db, user.id, "user.email.verify", "user", user.id)
        return ActionAck()
    finally:
        db.close()


@router.post("/password/forgot", response_model=ActionAck, status_code=202)
def forgot_password(data: EmailActionIn, request: Request):
    """Issue a short-lived reset token; response prevents account enumeration."""
    from app.services.rate_limit import client_key, enforce
    enforce(client_key(request, "password_forgot", str(data.email)), 5, 900)
    db = _require_db()
    try:
        from app import models
        user = db.query(models.User).filter_by(email=_normalize_email(str(data.email))).first()
        delivered, raw = (False, None)
        if user and user.is_active:
            delivered, raw = _send_token(db, models, user, "reset_password")
        return ActionAck(delivery_configured=delivered, dev_token=_expose_dev_token(raw))
    finally:
        db.close()


@router.post("/password/reset", response_model=ActionAck)
def reset_password(data: PasswordResetIn):
    try:
        validate_password_policy(data.password)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    from app import models
    from app.services.account_security import consume_token
    db = _require_db()
    try:
        row = consume_token(db, models, data.token, "reset_password")
        if row is None:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        user = db.get(models.User, row.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        user.hashed_password = security.hash_password(data.password)
        db.commit()
        _audit(db, user.id, "user.password.reset", "user", user.id)
        return ActionAck()
    finally:
        db.close()
