"""Knowledge Intelligence persistence + retrieval service (tenant-scoped)."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app import models
from ai_engine.knowledge.ingest import ingest_bytes
from ai_engine.knowledge.retrieve import build_evidence_pack, retrieve_for_query
from ai_engine.knowledge.memory import build_memory_payload, upsert_study_memory


def _org_id(db: Session, owner_id: int) -> Optional[int]:
    user = db.get(models.User, owner_id)
    return getattr(user, "organization_id", None) if user else None


def document_public_dict(doc: models.KnowledgeDocument) -> Dict[str, Any]:
    """Serialize a knowledge document. Never includes embeddings."""
    return {
        "id": doc.id,
        "title": doc.title,
        "source": doc.source,
        "sector": doc.sector,
        "country": doc.country,
        "year": doc.year,
        "document_type": doc.document_type,
        "project_type": doc.project_type,
        "capex": doc.capex,
        "opex": doc.opex,
        "revenue_model": doc.revenue_model,
        "assumptions": doc.assumptions or {},
        "outcome": doc.outcome,
        "confidence": doc.confidence,
        "visibility": doc.visibility,
        "extraction_status": doc.extraction_status,
        "original_filename": doc.original_filename,
        "content_type": doc.content_type,
        "created_at": doc.created_at.isoformat() if getattr(doc, "created_at", None) else None,
        "chunk_count": len(doc.chunks or []),
    }


def save_ingested_document(
    db: Session,
    *,
    owner_id: int,
    ingested: Dict[str, Any],
    storage_ref: Optional[str] = None,
) -> models.KnowledgeDocument:
    doc = models.KnowledgeDocument(
        id=ingested["id"],
        owner_id=owner_id,
        organization_id=_org_id(db, owner_id),
        title=ingested.get("title") or "Untitled",
        source=ingested.get("source") or "upload",
        sector=ingested.get("sector"),
        country=ingested.get("country") or "SA",
        year=ingested.get("year"),
        document_type=ingested.get("document_type") or "feasibility_study",
        project_type=ingested.get("project_type"),
        capex=ingested.get("capex"),
        opex=ingested.get("opex"),
        revenue_model=ingested.get("revenue_model"),
        assumptions=ingested.get("assumptions") or {},
        outcome=ingested.get("outcome"),
        confidence=float(ingested.get("confidence") or 0.5),
        visibility="private",
        extraction_status=ingested.get("extraction_status") or "ready",
        storage_ref=storage_ref,
        content_type=ingested.get("content_type"),
        original_filename=ingested.get("original_filename"),
        raw_text_excerpt=ingested.get("raw_text_excerpt"),
    )
    db.add(doc)
    for ch in ingested.get("chunks") or []:
        db.add(
            models.KnowledgeChunk(
                id=ch["id"],
                document_id=doc.id,
                owner_id=owner_id,
                content=ch["content"],
                embedding=ch.get("embedding") or [],
                chunk_metadata=ch.get("metadata") or {},
                importance=float(ch.get("importance") or 0.5),
            )
        )
    db.commit()
    db.refresh(doc)
    return doc


def ingest_upload(
    db: Session,
    *,
    owner_id: int,
    data: bytes,
    filename: str,
    content_type: Optional[str] = None,
    title: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
    storage_ref: Optional[str] = None,
) -> models.KnowledgeDocument:
    ingested = ingest_bytes(
        data,
        filename=filename,
        content_type=content_type,
        title=title,
        source="upload",
        overrides=overrides,
    )
    return save_ingested_document(
        db, owner_id=owner_id, ingested=ingested, storage_ref=storage_ref
    )


def list_documents(db: Session, *, owner_id: int) -> List[models.KnowledgeDocument]:
    return (
        db.query(models.KnowledgeDocument)
        .filter(models.KnowledgeDocument.owner_id == owner_id)
        .order_by(models.KnowledgeDocument.created_at.desc())
        .all()
    )


def get_document(
    db: Session, *, owner_id: int, document_id: str
) -> Optional[models.KnowledgeDocument]:
    return (
        db.query(models.KnowledgeDocument)
        .filter(
            models.KnowledgeDocument.id == document_id,
            models.KnowledgeDocument.owner_id == owner_id,
        )
        .first()
    )


def retrieve_evidence(
    db: Session,
    *,
    owner_id: int,
    query: str,
    study_id: Optional[str] = None,
    assumption_keys: Optional[List[str]] = None,
    top_k: int = 6,
) -> Dict[str, Any]:
    """Retrieve tenant-scoped evidence. Always filters by owner_id."""
    chunks = (
        db.query(models.KnowledgeChunk)
        .filter(models.KnowledgeChunk.owner_id == owner_id)
        .all()
    )
    docs = (
        db.query(models.KnowledgeDocument)
        .filter(models.KnowledgeDocument.owner_id == owner_id)
        .all()
    )
    doc_by_id = {d.id: d for d in docs}
    memories = (
        db.query(models.StudyMemory)
        .filter(models.StudyMemory.owner_id == owner_id)
        .all()
    )

    hits = retrieve_for_query(
        query=query,
        chunk_rows=chunks,
        document_by_id=doc_by_id,
        memory_rows=memories,
        top_k=top_k,
    )
    pack = build_evidence_pack(
        query=query, hits=hits, assumption_keys=assumption_keys
    )

    for cite in pack.get("citations") or []:
        if not (cite.get("document_id") or cite.get("study_memory_id")):
            continue
        db.add(
            models.KnowledgeEvidence(
                id=str(uuid.uuid4()),
                owner_id=owner_id,
                study_id=study_id,
                claim=cite.get("claim") or "",
                source_document_id=cite.get("document_id"),
                source_chunk_id=cite.get("chunk_id"),
                source_study_memory_id=cite.get("study_memory_id"),
                confidence=float(cite.get("confidence") or 0.5),
                related_project=None,
            )
        )
    db.commit()
    return pack


def remember_completed_study(
    db: Session, *, owner_id: int, state: Any
) -> Optional[models.StudyMemory]:
    payload = build_memory_payload(
        state, owner_id=owner_id, organization_id=_org_id(db, owner_id)
    )
    if not payload.get("source_study_id"):
        return None
    row = upsert_study_memory(db, models, payload)
    db.commit()
    return row
