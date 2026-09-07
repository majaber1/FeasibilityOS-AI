import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db import DB_ENABLED, SessionLocal, safe_backend
from app.api.projects import router as projects_router
from app.api.financial import router as financial_router
from app.api.funding import router as funding_router
from app.api.auth import router as auth_router
from app.api.feasibility import router as feasibility_router
from app.api.reports import router as reports_router
from app.api.ideas import router as ideas_router
from app.api.franchises import router as franchises_router
from app.api.auctions import router as auctions_router
from app.api.qualification import router as qualification_router
from app.api.admin import router as admin_router
from app.api.opportunities import router as opportunities_router
from app.api.leads import router as leads_router
from app.api.proposals import router as proposals_router
from app.api.entitlements import router as entitlements_router
from app.api.v2.study_engine import router as v2_study_router
from app.api.auth import UserOut, require_roles
from app.services.monitoring import metrics_snapshot, observe_request

app = FastAPI(
    title=settings.app_name,
    description="Saudi Business | سعودي بزنس — AI Operating System for Investment Decisions",
    version=settings.app_version,
    # The Next.js frontend proxies through a rewrite whose catch-all route
    # param strips trailing slashes when reconstructing the destination URL
    # (a Next.js routing characteristic, not a bug in either app). With the
    # default redirect_slashes=True, that mismatch produced a 307 pointing
    # directly at this backend's raw origin -- a cross-origin redirect that
    # both fetch() and curl correctly strip the Authorization header from,
    # silently 401-ing every authenticated collection endpoint through the
    # proxy. Disabling it means /x and /x/ are distinct routes with no
    # redirect; call sites (apps/web/lib/api.ts) already use the canonical
    # trailing-slash form that matches every router's @router.get("/").
    redirect_slashes=False,
)


@app.middleware("http")
async def request_observability(request, call_next):
    return await observe_request(request, call_next)

# CORS origins/credentials are resolved so a wildcard is never paired with
# credentials and production never serves "*" (see app.core.config.resolve_cors).
_cors_allow_origins, _cors_allow_credentials = settings.cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins,
    allow_credentials=_cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(financial_router)
app.include_router(funding_router)
app.include_router(feasibility_router)
app.include_router(reports_router)
app.include_router(ideas_router)
app.include_router(franchises_router)
app.include_router(auctions_router)
app.include_router(qualification_router)
app.include_router(admin_router)
app.include_router(opportunities_router)
app.include_router(leads_router)
app.include_router(proposals_router)
app.include_router(entitlements_router)
app.include_router(v2_study_router)

# Runs once per cold start (module import), not inside an ASGI lifespan
# startup event -- Vercel's Python runtime wrapper does not reliably invoke
# ASGI lifespan, but module-level code is guaranteed to run once when the
# module is first imported into a fresh Lambda container. Genuinely inert
# unless the account owner sets AUTO_MIGRATE_DB=true in Vercel -- see
# app.db.ensure_migrations_applied for why this exists, the off-by-default
# opt-in, and its safety guarantees (advisory-lock-guarded, idempotent,
# never raises).
from app.db import ensure_migrations_applied  # noqa: E402

ensure_migrations_applied()


def _db_ping() -> bool:
    """Attempt a trivial query to confirm live connectivity. Never raises."""
    if not DB_ENABLED:
        return False
    try:
        from sqlalchemy import text
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return True
        finally:
            db.close()
    except Exception:
        return False


def _persistence_label(backend: str, connected: bool) -> str:
    """Human-readable persistence descriptor derived from the *safe* backend
    name (never a URL). It tells the truth about four distinct states:

    1. Development demo file (sqlite:///./demo.db, DB_ENABLED=False):
       "sqlite demo fallback (local file, non-production)"
    2. In-memory sqlite (sqlite:///:memory:):
       "sqlite demo fallback (in-memory, non-persistent)"
    3. Production with NO engine/URL configured (engine is None):
       "disabled (database unconfigured)"
    4. A configured backend that fails the connectivity ping:
       "<backend> (unreachable)"
    5. A configured, reachable backend: the safe dialect name only.

    We NEVER claim durable/production storage for a demo fallback, and we NEVER
    say "in-memory" unless the engine URL is actually sqlite:///:memory:. No
    host, credentials, port, database name, or query string is ever exposed.
    """
    from app.db import DATABASE_URL as _DB_URL

    # No persistence enabled from an explicit env var.
    if not DB_ENABLED:
        if not _DB_URL:
            # No engine at all (production with neither Postgres URL present).
            return "disabled (database unconfigured)"
        if ":memory:" in _DB_URL:
            return "sqlite demo fallback (in-memory, non-persistent)"
        # Auto-generated local file demo (development only).
        return "sqlite demo fallback (local file, non-production)"

    # Persistence is configured from an env var.
    label = backend or "unknown"
    if not connected:
        return label + " (unreachable)"
    return label


@app.get("/health")
def health():
    """Liveness + database observability contract.

    Exposes only safe, non-sensitive fields. ``db_backend``/``persistence`` are
    derived from the SQLAlchemy dialect name only and never include host,
    credentials, port, database name, or query parameters.
    """
    connected = _db_ping()
    backend = safe_backend()
    return {
        "status": "running",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "db_enabled": DB_ENABLED,
        "db_backend": backend,
        "db_connected": connected,
        "persistence": _persistence_label(backend, connected),
    }


def _production_readiness(connected: bool) -> tuple[bool, list[str]]:
    production = settings.environment.strip().lower() in {"production", "prod"}
    failures = []
    if production and not connected:
        failures.append("database_unavailable")
    secret = os.getenv("JWT_SECRET", "")
    if production and (len(secret) < 32 or secret in {"replace-this-before-production", "dev-only-insecure-secret-change-me"}):
        failures.append("jwt_secret_insecure")
    verification = os.getenv("REQUIRE_EMAIL_VERIFICATION", "true" if production else "false").lower() in {"1", "true", "yes"}
    if production and verification and not (os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM")):
        failures.append("email_delivery_unconfigured")
    return not failures, failures


@app.get("/health/ready")
def readiness():
    """Deployment readiness gate with safe machine-readable failure codes."""
    connected = _db_ping()
    ready, failures = _production_readiness(connected)
    payload = {"status": "ready" if ready else "not_ready", "version": settings.app_version,
               "db_connected": connected, "checks": failures}
    return JSONResponse(payload, status_code=200 if ready else 503)


@app.get("/admin/metrics")
def application_metrics(user: UserOut = Depends(require_roles("admin"))):
    """Small protected operational snapshot; contains no URLs or credentials."""
    return metrics_snapshot()
