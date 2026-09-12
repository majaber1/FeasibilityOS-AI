"""Governed Source Registry persistence (Phase 7A).

Distinct from app.services.source_registry (domain→authority classifier).
This service owns knowledge_sources rows and connector status metadata.
Secrets must never be stored in connector_config.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app import models
from app.integrations.sources.base import ConnectorHealth, ConnectorStatus
from app.integrations.sources.fixture_connector import FixtureSaudiOpenDataConnector

# Keys that must never persist inside connector_config JSON.
_SECRET_KEY_RE = re.compile(
    r"(password|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|credential|auth)",
    re.IGNORECASE,
)

# Registry definitions for future Saudi sources — not live connectors in 7A.
SEED_SOURCES: List[Dict[str, Any]] = [
    {
        "key": "gastat",
        "name": "GASTAT — General Authority for Statistics",
        "description": "Official Saudi statistics authority.",
        "source_type": "official_statistic",
        "authority_type": "OFFICIAL_PRIMARY",
        "base_url": "https://www.stats.gov.sa",
        "trust_score": 0.95,
        "connector_type": "registry_only",
        "enabled": False,
        "refresh_policy": "manual",
        "languages": ["ar", "en"],
    },
    {
        "key": "monshaat",
        "name": "Monsha'at — Small & Medium Enterprises General Authority",
        "description": "SME programs, indicators, and support resources.",
        "source_type": "funding_program",
        "authority_type": "OFFICIAL_PRIMARY",
        "base_url": "https://www.monshaat.gov.sa",
        "trust_score": 0.9,
        "connector_type": "registry_only",
        "enabled": False,
        "refresh_policy": "manual",
        "languages": ["ar", "en"],
    },
    {
        "key": "misa",
        "name": "MISA — Ministry of Investment",
        "description": "Investment regulations and opportunity guidance.",
        "source_type": "regulation",
        "authority_type": "OFFICIAL_PRIMARY",
        "base_url": "https://misa.gov.sa",
        "trust_score": 0.9,
        "connector_type": "registry_only",
        "enabled": False,
        "refresh_policy": "manual",
        "languages": ["ar", "en"],
    },
    {
        "key": "sama",
        "name": "SAMA — Saudi Central Bank",
        "description": "Monetary policy, banking regulation, financial sector data.",
        "source_type": "regulation",
        "authority_type": "REGULATOR",
        "base_url": "https://www.sama.gov.sa",
        "trust_score": 0.95,
        "connector_type": "registry_only",
        "enabled": False,
        "refresh_policy": "manual",
        "languages": ["ar", "en"],
    },
    {
        "key": "nca",
        "name": "NCA — National Cybersecurity Authority",
        "description": "Cybersecurity controls and compliance frameworks.",
        "source_type": "regulation",
        "authority_type": "REGULATOR",
        "base_url": "https://nca.gov.sa",
        "trust_score": 0.9,
        "connector_type": "registry_only",
        "enabled": False,
        "refresh_policy": "manual",
        "languages": ["ar", "en"],
    },
    {
        "key": "zatca",
        "name": "ZATCA — Zakat, Tax and Customs Authority",
        "description": "Tax, zakat, and customs rules and guidance.",
        "source_type": "regulation",
        "authority_type": "REGULATOR",
        "base_url": "https://zatca.gov.sa",
        "trust_score": 0.95,
        "connector_type": "registry_only",
        "enabled": False,
        "refresh_policy": "manual",
        "languages": ["ar", "en"],
    },
    {
        "key": "saudi_open_data",
        "name": "Saudi Open Data Portal",
        "description": "National open data portal. Phase 7A ships a fixture connector only.",
        "source_type": "open_data",
        "authority_type": "OFFICIAL_PRIMARY",
        "base_url": "https://data.gov.sa",
        "trust_score": 0.9,
        "connector_type": "fixture",
        "enabled": True,
        "refresh_policy": "on_demand",
        "refresh_interval_hours": None,
        "languages": ["ar", "en"],
        "connector_config": {"fixture": True, "live": False},
    },
]


def scrub_connector_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Strip secret-like keys. Never persist credentials in the registry."""
    if not config:
        return {}
    clean: Dict[str, Any] = {}
    for k, v in config.items():
        if _SECRET_KEY_RE.search(str(k)):
            continue
        if isinstance(v, dict):
            clean[k] = scrub_connector_config(v)
        else:
            clean[k] = v
    return clean


def source_public_dict(row: models.KnowledgeSource) -> Dict[str, Any]:
    """Serialize a registry row. Never includes secrets (already scrubbed at write)."""
    return {
        "id": row.id,
        "key": row.key,
        "name": row.name,
        "description": row.description,
        "source_type": row.source_type,
        "authority_type": row.authority_type,
        "base_url": row.base_url,
        "country": row.country,
        "geography": row.geography,
        "sectors": row.sectors or [],
        "languages": row.languages or [],
        "trust_score": row.trust_score,
        "quality_score": row.quality_score,
        "refresh_policy": row.refresh_policy,
        "refresh_interval_hours": row.refresh_interval_hours,
        "enabled": bool(row.enabled),
        "connector_type": row.connector_type,
        "connector_config": scrub_connector_config(row.connector_config or {}),
        "last_sync_at": row.last_sync_at.isoformat() if row.last_sync_at else None,
        "last_success_at": row.last_success_at.isoformat() if row.last_success_at else None,
        "last_failure_at": row.last_failure_at.isoformat() if row.last_failure_at else None,
        "last_error": row.last_error,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def list_sources(db: Session, *, enabled_only: bool = False) -> List[models.KnowledgeSource]:
    q = db.query(models.KnowledgeSource).order_by(models.KnowledgeSource.key.asc())
    if enabled_only:
        q = q.filter(models.KnowledgeSource.enabled.is_(True))
    return q.all()


def get_source(db: Session, source_id: str) -> Optional[models.KnowledgeSource]:
    return db.get(models.KnowledgeSource, source_id)


def get_source_by_key(db: Session, key: str) -> Optional[models.KnowledgeSource]:
    return db.query(models.KnowledgeSource).filter_by(key=key).first()


def create_source(db: Session, payload: Dict[str, Any]) -> models.KnowledgeSource:
    key = (payload.get("key") or "").strip()
    if not key:
        raise ValueError("key required")
    if get_source_by_key(db, key):
        raise ValueError(f"source key already exists: {key}")

    row = models.KnowledgeSource(
        id=str(uuid.uuid4()),
        key=key,
        name=(payload.get("name") or key).strip(),
        description=payload.get("description"),
        source_type=payload.get("source_type") or "UNKNOWN",
        authority_type=payload.get("authority_type") or "UNKNOWN",
        base_url=payload.get("base_url"),
        country=payload.get("country") or "SA",
        geography=payload.get("geography"),
        sectors=list(payload.get("sectors") or []),
        languages=list(payload.get("languages") or []),
        trust_score=payload.get("trust_score"),
        quality_score=payload.get("quality_score"),
        refresh_policy=payload.get("refresh_policy"),
        refresh_interval_hours=payload.get("refresh_interval_hours"),
        enabled=bool(payload.get("enabled", False)),
        connector_type=payload.get("connector_type") or "registry_only",
        connector_config=scrub_connector_config(payload.get("connector_config") or {}),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_source(db: Session, source_id: str, payload: Dict[str, Any]) -> models.KnowledgeSource:
    row = get_source(db, source_id)
    if not row:
        raise LookupError("source not found")

    for field in (
        "name",
        "description",
        "source_type",
        "authority_type",
        "base_url",
        "country",
        "geography",
        "trust_score",
        "quality_score",
        "refresh_policy",
        "refresh_interval_hours",
        "enabled",
        "connector_type",
    ):
        if field in payload:
            setattr(row, field, payload[field])

    if "sectors" in payload:
        row.sectors = list(payload["sectors"] or [])
    if "languages" in payload:
        row.languages = list(payload["languages"] or [])
    if "connector_config" in payload:
        row.connector_config = scrub_connector_config(payload.get("connector_config") or {})

    # key is immutable after create
    db.commit()
    db.refresh(row)
    return row


def record_sync_result(
    db: Session,
    source_id: str,
    *,
    success: bool,
    error: Optional[str] = None,
) -> models.KnowledgeSource:
    row = get_source(db, source_id)
    if not row:
        raise LookupError("source not found")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    row.last_sync_at = now
    if success:
        row.last_success_at = now
        row.last_error = None
    else:
        row.last_failure_at = now
        row.last_error = (error or "unknown error")[:2000]
    db.commit()
    db.refresh(row)
    return row


def connector_for_source(row: models.KnowledgeSource):
    """Resolve a SourceConnector for a registry row (fixture only in 7A)."""
    if row.connector_type == "fixture" and row.key == "saudi_open_data":
        return FixtureSaudiOpenDataConnector(enabled=bool(row.enabled))
    return None


def source_status(db: Session, source_id: str) -> Dict[str, Any]:
    row = get_source(db, source_id)
    if not row:
        raise LookupError("source not found")

    connector = connector_for_source(row)
    if connector is None:
        health = ConnectorHealth(
            status=ConnectorStatus.DISABLED if not row.enabled else ConnectorStatus.UNAVAILABLE,
            checked_at=datetime.now(timezone.utc),
            detail="no live connector in Phase 7A (registry_only)",
            metadata={"connector_type": row.connector_type},
        )
    else:
        health = connector.health()

    return {
        "id": row.id,
        "key": row.key,
        "enabled": bool(row.enabled),
        "connector_type": row.connector_type,
        "connector_id": getattr(connector, "connector_id", None),
        "status": health.status.value,
        "checked_at": health.checked_at.isoformat(),
        "detail": health.detail,
        "metadata": health.metadata,
        "last_sync_at": row.last_sync_at.isoformat() if row.last_sync_at else None,
        "last_success_at": row.last_success_at.isoformat() if row.last_success_at else None,
        "last_failure_at": row.last_failure_at.isoformat() if row.last_failure_at else None,
        "last_error": row.last_error,
    }


def ensure_seed_sources(db: Session) -> List[models.KnowledgeSource]:
    """Idempotently insert the Phase 7A Saudi source registry definitions."""
    created: List[models.KnowledgeSource] = []
    for seed in SEED_SOURCES:
        existing = get_source_by_key(db, seed["key"])
        if existing:
            continue
        created.append(create_source(db, seed))
    return created
