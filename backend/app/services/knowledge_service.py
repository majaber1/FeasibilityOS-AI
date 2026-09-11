"""Knowledge Intelligence persistence + retrieval service (tenant-scoped)."""
from __future__ import annotations

import uuid
from collections import Counter
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app import models
from ai_engine.knowledge.ingest import ingest_bytes
from ai_engine.knowledge.retrieve import build_evidence_pack, retrieve_for_query
from ai_engine.knowledge.memory import build_memory_payload, upsert_study_memory
from ai_engine.knowledge.influence import (
    enrich_assumption_influence,
    influence_records_for_evidence,
)


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
        "quality_score": getattr(doc, "quality_score", None),
        "quality_breakdown": getattr(doc, "quality_breakdown", None),
        "reference_count": int(getattr(doc, "reference_count", 0) or 0),
        "geography": getattr(doc, "geography", None),
        "business_model": getattr(doc, "business_model", None),
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
        quality_score=ingested.get("quality_score"),
        quality_breakdown=ingested.get("quality_breakdown"),
        reference_count=int(ingested.get("reference_count") or 0),
        geography=ingested.get("geography") or ingested.get("country") or "SA",
        business_model=ingested.get("business_model"),
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
    query_profile: Optional[Dict[str, Any]] = None,
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
        query=query,
        hits=hits,
        assumption_keys=assumption_keys,
        document_by_id=doc_by_id,
        query_profile=query_profile,
    )

    referenced: Counter[str] = Counter()
    for cite in pack.get("citations") or []:
        if not (cite.get("document_id") or cite.get("study_memory_id")):
            continue
        doc_id = cite.get("document_id")
        if doc_id:
            referenced[str(doc_id)] += 1
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
                related_project=cite.get("source_title") or cite.get("title"),
                assumption_key=None,
                reason="Retrieved as similar-project evidence",
            )
        )
    for doc_id, n in referenced.items():
        doc = doc_by_id.get(doc_id)
        if doc is not None:
            doc.reference_count = int(getattr(doc, "reference_count", 0) or 0) + n
            db.add(doc)
    db.commit()
    return pack


def record_assumption_influence(
    db: Session,
    *,
    owner_id: int,
    study_id: Optional[str],
    assumptions: List[Any],
) -> int:
    """Persist knowledge influence rows for assumptions (post-generation glue)."""
    rows = influence_records_for_evidence(assumptions, study_id=study_id)
    for row in rows:
        db.add(
            models.KnowledgeEvidence(
                id=str(uuid.uuid4()),
                owner_id=owner_id,
                study_id=study_id,
                claim=row.get("claim") or "",
                source_document_id=row.get("source_document_id"),
                source_chunk_id=row.get("source_chunk_id"),
                source_study_memory_id=row.get("source_study_memory_id"),
                confidence=float(row.get("confidence") or 0.5),
                related_project=row.get("related_project"),
                assumption_key=row.get("assumption_key"),
                reason=row.get("reason"),
            )
        )
        doc_id = row.get("source_document_id")
        if doc_id:
            doc = (
                db.query(models.KnowledgeDocument)
                .filter(
                    models.KnowledgeDocument.id == doc_id,
                    models.KnowledgeDocument.owner_id == owner_id,
                )
                .first()
            )
            if doc is not None:
                doc.reference_count = int(getattr(doc, "reference_count", 0) or 0) + 1
                db.add(doc)
    if rows:
        db.commit()
    return len(rows)


def enrich_state_assumptions(state: Any) -> Any:
    """Enrich assumption knowledge_refs with influence metadata (no engine change)."""
    assumptions = getattr(state, "assumptions", None) or []
    kc = getattr(state, "knowledge_context", None) or {}
    enriched = enrich_assumption_influence(assumptions, kc)
    state.assumptions = enriched
    return state


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


def dashboard_stats(db: Session, *, owner_id: int) -> Dict[str, Any]:
    """Knowledge dashboard aggregates for the current tenant."""
    docs = list_documents(db, owner_id=owner_id)
    memories = (
        db.query(models.StudyMemory)
        .filter(models.StudyMemory.owner_id == owner_id)
        .order_by(models.StudyMemory.updated_at.desc())
        .all()
    )
    coverage: Counter[str] = Counter()
    for d in docs:
        key = (d.sector or d.project_type or "other").replace("_", " ").title()
        coverage[key] += 1
    for m in memories:
        key = (m.sector or m.project_type or m.archetype or "other").replace("_", " ").title()
        coverage[key] += 1

    quality_rows = [
        {
            "id": d.id,
            "title": d.title,
            "quality_score": d.quality_score,
            "reasons": (d.quality_breakdown or {}).get("reasons")
            if isinstance(d.quality_breakdown, dict)
            else [],
            "project_type": d.project_type,
            "sector": d.sector,
            "year": d.year,
        }
        for d in docs
        if d.quality_score is not None
    ]
    quality_rows.sort(key=lambda r: float(r.get("quality_score") or 0), reverse=True)

    most_referenced = sorted(
        [
            {
                "id": d.id,
                "title": d.title,
                "reference_count": int(d.reference_count or 0),
                "quality_score": d.quality_score,
                "project_type": d.project_type,
            }
            for d in docs
        ],
        key=lambda r: r["reference_count"],
        reverse=True,
    )[:10]

    avg_quality = None
    if quality_rows:
        avg_quality = round(
            sum(float(r["quality_score"]) for r in quality_rows) / len(quality_rows), 1
        )

    return {
        "documents_count": len(docs),
        "memories_count": len(memories),
        "coverage": [{"sector": k, "count": v} for k, v in coverage.most_common()],
        "average_quality_score": avg_quality,
        "quality_scores": quality_rows[:20],
        "most_referenced": most_referenced,
        "recent_memories": [
            {
                "id": m.id,
                "source_study_id": m.source_study_id,
                "archetype": m.archetype,
                "project_type": m.project_type,
                "sector": m.sector,
                "decision": m.decision,
                "summary_text": m.summary_text,
            }
            for m in memories[:10]
        ],
    }
