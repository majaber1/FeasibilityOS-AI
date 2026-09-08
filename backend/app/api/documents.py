from __future__ import annotations

from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import UserOut, get_current_user
from app.db import DB_ENABLED, get_db
from app.models import AuditLog, Document, FeasibilityStudy, Project
from app.services.object_storage import delete_object, get_object, put_object

router = APIRouter(prefix="/documents", tags=["documents"])
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {
    "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "image/jpeg", "image/png",
}
DOCUMENT_TYPES = {
    "financial_statement", "bank_statement", "cr_document", "asset_schedule",
    "debt_schedule", "guarantee", "project_proposal", "other",
}


class DocumentOut(BaseModel):
    id: int
    project_id: int | None
    study_id: int | None
    document_type: str | None
    name: str
    content_type: str | None
    size_bytes: int | None
    created_at: object
    model_config = {"from_attributes": True}


def _owned_project(db: Session, project_id: int, user: UserOut) -> Project:
    project = db.get(Project, project_id)
    if not project or (user.role_key != "admin" and project.owner_id != user.id):
        raise HTTPException(404, "Project not found")
    return project


@router.get("/", response_model=list[DocumentOut])
def list_documents(project_id: int, user: UserOut = Depends(get_current_user), db: Session = Depends(get_db)):
    if not DB_ENABLED:
        raise HTTPException(503, "Database unavailable")
    _owned_project(db, project_id, user)
    return db.query(Document).filter(Document.project_id == project_id, Document.owner_id == user.id).order_by(Document.id.desc()).all()


@router.post("/", response_model=DocumentOut, status_code=201)
async def upload_document(
    project_id: int = Form(...),
    file: UploadFile = File(...),
    study_id: Optional[int] = Form(default=None),
    document_type: Optional[str] = Form(default=None),
    user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not DB_ENABLED:
        raise HTTPException(503, "Database unavailable")
    _owned_project(db, project_id, user)
    if study_id is not None:
        study = db.get(FeasibilityStudy, study_id)
        if study is None or study.project_id != project_id:
            raise HTTPException(422, "study_id must belong to project_id")
    if document_type is not None and document_type not in DOCUMENT_TYPES:
        raise HTTPException(422, f"document_type must be one of {sorted(DOCUMENT_TYPES)}")
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Supported files: PDF, DOCX, XLSX, JPG, PNG")
    data = await file.read(MAX_FILE_SIZE + 1)
    if not data or len(data) > MAX_FILE_SIZE:
        raise HTTPException(413, "File must be between 1 byte and 10 MB")
    safe_name = Path(file.filename or "document").name.replace("/", "_").replace("\\", "_")
    key = f"funding/{user.id}/{project_id}/{uuid4().hex}-{safe_name}"
    put_object(key, data, content_type)
    row = Document(
        owner_id=user.id, project_id=project_id, study_id=study_id, document_type=document_type,
        name=safe_name, content_type=content_type, size_bytes=len(data), storage_ref=key,
    )
    db.add(row)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action="document.upload", entity="document", entity_id=row.id, meta={"project_id": project_id, "size": len(data)}))
    db.commit(); db.refresh(row)
    return row


@router.get("/{document_id}/download")
def download_document(document_id: int, user: UserOut = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Document, document_id)
    if not row or (user.role_key != "admin" and row.owner_id != user.id):
        raise HTTPException(404, "Document not found")
    data, content_type = get_object(row.storage_ref or "")
    return Response(data, media_type=content_type, headers={"Content-Disposition": f'attachment; filename="{row.name}"'})


@router.delete("/{document_id}", status_code=204)
def remove_document(document_id: int, user: UserOut = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Document, document_id)
    if not row or (user.role_key != "admin" and row.owner_id != user.id):
        raise HTTPException(404, "Document not found")
    if row.storage_ref:
        delete_object(row.storage_ref)
    db.delete(row); db.commit()
