"""Document intake foundation: study linkage + traced extracted facts.

Object storage (Cloudflare R2) isn't configured in this test environment,
so these tests exercise the study-linkage and extracted-fact provenance API
directly against Document rows inserted through the ORM (bypassing the
upload endpoint's storage call) -- the same approach the rest of the app
uses to keep DB-backed tests independent of external services.
"""
import os
import sys
import tempfile
import uuid
from pathlib import Path

if not os.environ.get("DATABASE_URL"):
    handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    handle.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + handle.name

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from app import db as app_db  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def setup_module(module):
    app_db.init_db()


def _headers(prefix: str):
    email = f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    password = "Sup3rSecret!"
    assert client.post("/auth/register", json={"email": email, "password": password}).status_code == 201
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _study_and_owner_id(headers):
    project = client.post(
        "/projects/", headers=headers, json={"name": "شركة قائمة", "industry": "retail", "investment": 3000000}
    ).json()
    study = client.post(
        "/feasibility/",
        headers=headers,
        json={"project_id": project["id"], "title": "توسع الشركة", "industry": "retail", "investment": 3000000},
    ).json()
    me = client.get("/auth/me", headers=headers).json()
    return study, project, me["id"]


def _insert_document(owner_id: int, project_id: int, study_id: int, document_type: str = "financial_statement"):
    from app import models

    db = app_db.SessionLocal()
    try:
        row = models.Document(
            owner_id=owner_id, project_id=project_id, study_id=study_id, document_type=document_type,
            name="statements.pdf", content_type="application/pdf", size_bytes=1024, storage_ref="test/fake-key",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


def test_extracted_fact_requires_document_linked_to_same_study():
    headers = _headers("facts_wrong_doc")
    study, project, owner_id = _study_and_owner_id(headers)
    other_study = client.post(
        "/feasibility/",
        headers=headers,
        json={"industry": "retail", "investment": 100000, "title": "different study"},
    ).json()
    doc_id = _insert_document(owner_id, project["id"], other_study["id"])

    resp = client.post(
        f"/studies/{study['id']}/extracted-facts/",
        headers=headers,
        json={"document_id": doc_id, "field_name": "revenue", "value_number": 12500000, "unit": "SAR", "period": "FY2025"},
    )
    assert resp.status_code == 422, resp.text


def test_extracted_fact_created_with_full_provenance():
    headers = _headers("facts_ok")
    study, project, owner_id = _study_and_owner_id(headers)
    doc_id = _insert_document(owner_id, project["id"], study["id"])

    resp = client.post(
        f"/studies/{study['id']}/extracted-facts/",
        headers=headers,
        json={
            "document_id": doc_id, "field_name": "ebitda", "value_number": 2500000, "unit": "SAR",
            "period": "FY2025", "source_location": "page 4, income statement",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["extraction_status"] == "user_entered"
    assert body["confidence"] == "high"
    assert body["review_status"] == "confirmed"
    assert body["source_location"] == "page 4, income statement"

    listed = client.get(f"/studies/{study['id']}/extracted-facts/", headers=headers).json()
    assert len(listed) == 1


def test_extracted_facts_ownership_isolation():
    owner = _headers("facts_owner")
    other = _headers("facts_other")
    study, project, owner_id = _study_and_owner_id(owner)
    doc_id = _insert_document(owner_id, project["id"], study["id"])

    assert client.get(f"/studies/{study['id']}/extracted-facts/", headers=other).status_code == 403
    assert client.post(
        f"/studies/{study['id']}/extracted-facts/", headers=other,
        json={"document_id": doc_id, "field_name": "revenue", "value_number": 1},
    ).status_code == 403


def test_document_study_link_rejects_mismatched_project():
    headers = _headers("doc_link_mismatch")
    study, project, _owner_id = _study_and_owner_id(headers)
    other_project = client.post(
        "/projects/", headers=headers, json={"name": "مشروع آخر", "industry": "retail", "investment": 100000}
    ).json()

    resp = client.post(
        "/documents/",
        headers=headers,
        data={"project_id": other_project["id"], "study_id": study["id"]},
        files={"file": ("statement.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert resp.status_code == 422, resp.text
