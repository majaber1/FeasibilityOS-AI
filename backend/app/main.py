import os

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
from app.api.documents import router as documents_router
from app.api.qualification import router as qualification_router
from app.api.admin import router as admin_router
from app.api.opportunities import router as opportunities_router
from app.api.leads import router as leads_router
from app.api.proposals import router as proposals_router
from app.api.entitlements import router as entitlements_router
from app.api.evidence import router as evidence_router
from app.api.assumptions import router as assumptions_router
from app.api.quick_idea_check import router as quick_idea_check_router
from app.api.business_profile import router as business_profile_router
from app.api.extracted_facts import router as extracted_facts_router
from app.api.company_financial_profile import router as company_financial_profile_router
from app.api.financial_health import router as financial_health_router
from app.api.scenarios import router as scenarios_router
from app.api.decision import router as decision_router
from app.api.funding_gap import router as funding_gap_router
from app.api.borrowing_capacity import router as borrowing_capacity_router
from app.api.collateral import router as collateral_router
from app.api.funding_readiness import router as funding_readiness_router
from app.api.funding_programs import router as funding_programs_router
from app.api.funding_matching import router as funding_matching_router
from app.api.financing_structure import router as financing_structure_router
from app.api.verified_opportunities import router as verified_opportunities_router
from app.api.opportunity_matching import router as opportunity_matching_router
from app.api.validation import router as validation_router
from app.api.launch import router as launch_router
from app.api.growth import router as growth_router
from app.api.auth import UserOut, require_roles
from app.services.monitoring import metrics_snapshot, observe_request

app = FastAPI(
    title=settings.app_name,
    description="Saudi Business | سعودي بزنس — AI Operating System for Investment Decisions",
    version=settings.app_version,
    redirect_slashes=False,
)


@app.middleware("http")
async def request_observability(request, call_next):
    return await observe_request(request, call_next)


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
app.include_router(documents_router)
app.include_router(qualification_router)
app.include_router(admin_router)
app.include_router(opportunities_router)
app.include_router(leads_router)
app.include_router(proposals_router)
app.include_router(entitlements_router)
app.include_router(evidence_router)
app.include_router(assumptions_router)
app.include_router(quick_idea_check_router)
app.include_router(business_profile_router)
app.include_router(extracted_facts_router)
app.include_router(company_financial_profile_router)
app.include_router(financial_health_router)
app.include_router(scenarios_router)
app.include_router(decision_router)
app.include_router(funding_gap_router)
app.include_router(borrowing_capacity_router)
app.include_router(collateral_router)
app.include_router(funding_readiness_router)
app.include_router(funding_programs_router)
app.include_router(funding_matching_router)
app.include_router(financing_structure_router)
app.include_router(opportunity_matching_router)
app.include_router(verified_opportunities_router)
app.include_router(validation_router)
app.include_router(launch_router)
app.include_router(growth_router)

from app.db import ensure_migrations_applied, init_db  # noqa: E402

ensure_migrations_applied()
if (settings.environment or "").strip().lower() not in {"production", "prod"}:
    init_db()


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
    """Return a safe persistence description without exposing connection data."""
    from app.db import DATABASE_URL as _DB_URL

    if not DB_ENABLED:
        if not _DB_URL:
            return "disabled (database unconfigured)"
        if ":memory:" in _DB_URL:
            return "sqlite demo fallback (in-memory, non-persistent)"
        return "sqlite demo fallback (local file, non-production)"

    label = backend or "unknown"
    if not connected:
        return label + " (unreachable)"
    return label


def _r2_configured() -> bool:
    """Report configuration presence only; never expose Cloudflare credentials."""
    return all(
        os.getenv(name)
        for name in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME")
    )


@app.get("/health")
def health():
    """Liveness + dependency observability contract with safe fields only."""
    connected = _db_ping()
    backend = safe_backend()
    r2 = _r2_configured()
    return {
        "status": "running",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "db_enabled": DB_ENABLED,
        "db_backend": backend,
        "db_connected": connected,
        "persistence": _persistence_label(backend, connected),
        "object_storage": "configured" if r2 else "not_configured",
        "storage_provider": "cloudflare-r2" if r2 else "none",
    }


def _production_readiness(connected: bool) -> tuple[bool, list[str]]:
    production = settings.environment.strip().lower() in {"production", "prod"}
    failures = []
    if production and not connected:
        failures.append("database_unavailable")
    secret = os.getenv("JWT_SECRET", "")
    if production and (len(secret) < 32 or secret in {"replace-this-before-production", "dev-only-insecure-secret-change-me"}):
        failures.append("jwt_secret_insecure")
    verification = os.getenv("REQUIRE_EMAIL_VERIFICATION", "false").lower() in {"1", "true", "yes"}
    if production and verification and not (os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM")):
        failures.append("email_delivery_unconfigured")
    return not failures, failures


@app.get("/health/ready")
def readiness():
    """Deployment readiness gate with safe machine-readable failure codes."""
    connected = _db_ping()
    ready, failures = _production_readiness(connected)
    payload = {
        "status": "ready" if ready else "not_ready",
        "version": settings.app_version,
        "db_connected": connected,
        "checks": failures,
        "object_storage": "configured" if _r2_configured() else "not_configured",
        "storage_provider": "cloudflare-r2" if _r2_configured() else "none",
    }
    return JSONResponse(payload, status_code=200 if ready else 503)


@app.get("/admin/metrics")
def application_metrics(user: UserOut = Depends(require_roles("admin"))):
    """Small protected operational snapshot; contains no URLs or credentials."""
    return metrics_snapshot()
