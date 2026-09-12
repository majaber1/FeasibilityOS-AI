"""Source Registry Admin API (Phase 7A).

Read endpoints for authenticated users; mutations are admin-only.
Never exposes secrets (connector_config is scrubbed).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import UserOut, get_current_user, require_roles
from app.db import DB_ENABLED, get_db
from app.services import source_registry_service as registry

router = APIRouter(prefix="/api/v2/sources", tags=["v2-sources"])


def _require_db() -> None:
    if not DB_ENABLED:
        raise HTTPException(503, "Database unavailable")


class SourceCreateIn(BaseModel):
    key: str = Field(..., min_length=2, max_length=80)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    source_type: str = "UNKNOWN"
    authority_type: str = "UNKNOWN"
    base_url: Optional[str] = None
    country: str = "SA"
    geography: Optional[str] = None
    sectors: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    trust_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    refresh_policy: Optional[str] = None
    refresh_interval_hours: Optional[int] = Field(default=None, ge=1)
    enabled: bool = False
    connector_type: str = "registry_only"
    connector_config: Dict[str, Any] = Field(default_factory=dict)


class SourcePatchIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    source_type: Optional[str] = None
    authority_type: Optional[str] = None
    base_url: Optional[str] = None
    country: Optional[str] = None
    geography: Optional[str] = None
    sectors: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    trust_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    refresh_policy: Optional[str] = None
    refresh_interval_hours: Optional[int] = Field(default=None, ge=1)
    enabled: Optional[bool] = None
    connector_type: Optional[str] = None
    connector_config: Optional[Dict[str, Any]] = None


@router.get("")
def list_sources(
    enabled_only: bool = Query(default=False),
    seed: bool = Query(default=True, description="Ensure Phase 7A seed definitions exist"),
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_db()
    if seed:
        registry.ensure_seed_sources(db)
    rows = registry.list_sources(db, enabled_only=enabled_only)
    return {"items": [registry.source_public_dict(r) for r in rows], "count": len(rows)}


@router.get("/{source_id}")
def get_source(
    source_id: str,
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_db()
    row = registry.get_source(db, source_id)
    if not row:
        raise HTTPException(404, "source not found")
    return registry.source_public_dict(row)


@router.get("/{source_id}/status")
def get_source_status(
    source_id: str,
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_db()
    try:
        return registry.source_status(db, source_id)
    except LookupError:
        raise HTTPException(404, "source not found") from None


@router.post("")
def create_source(
    body: SourceCreateIn,
    user: UserOut = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    _require_db()
    try:
        row = registry.create_source(db, body.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return registry.source_public_dict(row)


@router.patch("/{source_id}")
def patch_source(
    source_id: str,
    body: SourcePatchIn,
    user: UserOut = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    _require_db()
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    # Allow explicit null-ish clears only via fields that were set; enabled=False must stick.
    raw = body.model_dump(exclude_unset=True)
    try:
        row = registry.update_source(db, source_id, raw)
    except LookupError:
        raise HTTPException(404, "source not found") from None
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return registry.source_public_dict(row)


class SourceSyncIn(BaseModel):
    urls: Optional[List[str]] = None
    query: Optional[str] = None


@router.post("/{source_id}/sync")
def sync_source(
    source_id: str,
    body: SourceSyncIn = SourceSyncIn(),
    user: UserOut = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Admin-only: run the live source connector and ingest into Knowledge Layer."""
    _require_db()
    try:
        return registry.sync_source_documents(
            db,
            source_id=source_id,
            owner_id=user.id,
            urls=body.urls,
            query=body.query,
        )
    except LookupError:
        raise HTTPException(404, "source not found") from None
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/{source_id}/documents")
def list_source_documents(
    source_id: str,
    user: UserOut = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Admin-only: list Knowledge documents ingested from this registry source for the caller."""
    _require_db()
    try:
        items = registry.list_source_knowledge_documents(
            db, source_id=source_id, owner_id=user.id
        )
    except LookupError:
        raise HTTPException(404, "source not found") from None
    return {"items": items, "count": len(items)}

