"""Knowledge Intelligence API — upload, list, retrieve (tenant-isolated)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import UserOut, get_current_user
from app.db import DB_ENABLED, get_db
from app.services import knowledge_service as ks

router = APIRouter(prefix="/api/v2/knowledge", tags=["v2-knowledge"])

MAX_BYTES = 12 * 1024 * 1024
ALLOWED_SUFFIXES = {".pdf", ".docx", ".xlsx", ".xls", ".txt"}
ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/plain",
    "application/octet-stream",
}


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=4000)
    study_id: Optional[str] = None
    assumption_keys: Optional[List[str]] = None
    top_k: int = Field(default=6, ge=1, le=20)
    query_profile: Optional[Dict[str, Any]] = None


def _require_db() -> None:
    if not DB_ENABLED:
        raise HTTPException(503, "Database unavailable")


@router.post("/documents")
async def upload_knowledge_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    document_type: Optional[str] = Form(default=None),
    project_type: Optional[str] = Form(default=None),
    sector: Optional[str] = Form(default=None),
    year: Optional[int] = Form(default=None),
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_db()
    filename = (file.filename or "document.bin").split("/")[-1].split("\\")[-1]
    suffix = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(415, "Supported files: PDF, DOCX, XLSX, TXT")
    content_type = file.content_type or "application/octet-stream"
    data = await file.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise HTTPException(413, "File must be between 1 byte and 12 MB")

    overrides: Dict[str, Any] = {}
    if document_type:
        overrides["document_type"] = document_type
    if project_type:
        overrides["project_type"] = project_type
    if sector:
        overrides["sector"] = sector
    if year:
        overrides["year"] = year

    try:
        doc = ks.ingest_upload(
            db,
            owner_id=user.id,
            data=data,
            filename=filename,
            content_type=content_type,
            title=title,
            overrides=overrides or None,
        )
    except Exception as exc:
        raise HTTPException(422, f"Could not ingest document: {exc}") from exc

    return {"document": ks.document_public_dict(doc)}


@router.get("/documents")
def list_knowledge_documents(
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_db()
    docs = ks.list_documents(db, owner_id=user.id)
    return {"documents": [ks.document_public_dict(d) for d in docs]}


@router.get("/documents/{document_id}")
def get_knowledge_document(
    document_id: str,
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_db()
    doc = ks.get_document(db, owner_id=user.id, document_id=document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    payload = ks.document_public_dict(doc)
    payload["chunks"] = [
        {
            "id": c.id,
            "content": c.content[:500],
            "importance": c.importance,
            "metadata": c.chunk_metadata or {},
        }
        for c in (doc.chunks or [])
    ]
    return {"document": payload}


@router.post("/retrieve")
def retrieve_knowledge(
    req: RetrieveRequest,
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_db()
    pack = ks.retrieve_evidence(
        db,
        owner_id=user.id,
        query=req.query,
        study_id=req.study_id,
        assumption_keys=req.assumption_keys,
        top_k=req.top_k,
        query_profile=req.query_profile,
    )
    return {"evidence_pack": pack}


@router.get("/dashboard")
def knowledge_dashboard(
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_db()
    return {"dashboard": ks.dashboard_stats(db, owner_id=user.id)}


@router.get("/memories")
def list_study_memories(
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_db()
    from app import models
    rows = (
        db.query(models.StudyMemory)
        .filter(models.StudyMemory.owner_id == user.id)
        .order_by(models.StudyMemory.updated_at.desc())
        .all()
    )
    return {
        "memories": [
            {
                "id": r.id,
                "source_study_id": r.source_study_id,
                "archetype": r.archetype,
                "project_type": r.project_type,
                "sector": r.sector,
                "decision": r.decision,
                "lessons_learned": r.lessons_learned,
                "summary_text": r.summary_text,
                "conditions": r.conditions,
                "influence_summary": r.influence_summary,
            }
            for r in rows
        ]
    }
