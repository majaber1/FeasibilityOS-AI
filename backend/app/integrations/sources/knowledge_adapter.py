"""Adapt SourceDocument → existing Knowledge Layer (no second ingest pipeline)."""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app import models

from ai_engine.knowledge.chunking import chunk_text
from ai_engine.knowledge.embeddings import embed_text
from ai_engine.knowledge.quality import score_document_quality
from app.services import knowledge_service as ks

from .schemas import SourceDocument
from .validation import provenance_is_complete, validate_source_document, verification_status_for


class ProvenanceError(ValueError):
    """Raised when a source document lacks provenance required for ingest."""


def source_document_to_ingest_payload(doc: SourceDocument) -> Dict[str, Any]:
    ok, errors = validate_source_document(doc)
    if not ok:
        raise ProvenanceError("invalid SourceDocument: " + "; ".join(errors))
    if not provenance_is_complete(doc.provenance):
        raise ProvenanceError("incomplete provenance — refuse Knowledge Layer ingest")

    text = doc.content
    chunks_raw = chunk_text(text)
    chunks = []
    for ch in chunks_raw:
        content = ch["content"]
        chunks.append(
            {
                "id": str(uuid.uuid4()),
                "content": content,
                "embedding": embed_text(content),
                "metadata": {
                    "index": ch["index"],
                    "source_id": doc.source_id,
                    "connector_id": doc.provenance.connector_id,
                    "registry_key": doc.provenance.registry_key,
                    "original_url": doc.provenance.original_url,
                    "retrieval_method": doc.provenance.retrieval_method,
                    "authority_type": doc.authority_type.value,
                    "verification_status": verification_status_for(doc),
                },
                "importance": 0.6,
            }
        )

    meta = {
        "source_id": doc.source_id,
        "source_name": doc.source_name,
        "source_type": doc.source_type.value,
        "authority_type": doc.authority_type.value,
        "url": doc.url,
        "canonical_url": doc.canonical_url,
        "published_at": doc.published_at.isoformat() if doc.published_at else None,
        "retrieved_at": doc.retrieved_at.isoformat(),
        "effective_date": doc.effective_date.isoformat() if doc.effective_date else None,
        "expires_at": doc.expires_at.isoformat() if doc.expires_at else None,
        "country": doc.country,
        "geography": doc.geography,
        "sector": doc.sector,
        "language": doc.language,
        "document_type": doc.document_type,
        "content_hash": doc.content_hash,
        "verification_status": verification_status_for(doc),
        "verification_eligibility": doc.verification_eligibility.value,
        "provenance": doc.provenance.model_dump(mode="json"),
        "connector_metadata": doc.metadata,
    }

    quality = score_document_quality(
        text=text,
        metadata={"sector": doc.sector, "country": doc.country or "SA"},
        source=f"connector:{doc.provenance.connector_id}",
        country=doc.country or "SA",
    )

    return {
        "id": str(uuid.uuid4()),
        "title": doc.title or doc.source_name,
        "source": f"connector:{doc.provenance.connector_id}",
        "sector": doc.sector,
        "country": doc.country or "SA",
        "year": doc.published_at.year if doc.published_at else None,
        "document_type": doc.document_type or "external_source",
        "project_type": None,
        "capex": None,
        "opex": None,
        "revenue_model": None,
        "assumptions": {"external_source": meta},
        "outcome": None,
        "confidence": float(doc.confidence if doc.confidence is not None else 0.5),
        "extraction_status": "ready",
        "raw_text_excerpt": text[:4000],
        "chunks": chunks,
        "original_filename": None,
        "content_type": doc.content_type or "text/plain",
        "quality_score": quality.get("quality_score"),
        "quality_breakdown": {
            "factors": quality.get("factors"),
            "reasons": quality.get("reasons"),
            "quality_confidence": quality.get("quality_confidence"),
        },
        "reference_count": 0,
        "geography": doc.geography or doc.country or "SA",
        "business_model": None,
    }


def find_existing_by_content_hash(
    db: Session,
    *,
    owner_id: int,
    content_hash: Optional[str],
):
    """Return an existing KnowledgeDocument for this owner+content_hash if present."""
    if not content_hash:
        return None
    rows = (
        db.query(models.KnowledgeDocument)
        .filter(models.KnowledgeDocument.owner_id == owner_id)
        .all()
    )
    for row in rows:
        assumptions = row.assumptions or {}
        ext = assumptions.get("external_source") or {}
        if isinstance(ext, dict) and ext.get("content_hash") == content_hash:
            return row
    return None


def ingest_source_document(
    db: Session,
    *,
    owner_id: int,
    document: SourceDocument,
    storage_ref: Optional[str] = None,
):
    """Persist via existing knowledge_service.save_ingested_document only.

    Duplicate content_hash for the same owner is idempotent (returns existing row).
    """
    existing = find_existing_by_content_hash(
        db, owner_id=owner_id, content_hash=document.content_hash
    )
    if existing is not None:
        setattr(existing, "_idempotent_reuse", True)
        return existing
    payload = source_document_to_ingest_payload(document)
    return ks.save_ingested_document(
        db,
        owner_id=owner_id,
        ingested=payload,
        storage_ref=storage_ref,
    )
