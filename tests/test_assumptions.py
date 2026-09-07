"""Study assumptions: provenance, versioning, and ownership."""
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


def _study(headers):
    project = client.post(
        "/projects/", headers=headers, json={"name": "حضانة أطفال", "industry": "education", "investment": 500000}
    ).json()
    study = client.post(
        "/feasibility/",
        headers=headers,
        json={"project_id": project["id"], "title": "دراسة حضانة", "industry": "education", "investment": 500000},
    ).json()
    return study


def _create(headers, study_id, **overrides):
    payload = {
        "key": "monthly_rent",
        "label_en": "Monthly rent",
        "label_ar": "الإيجار الشهري",
        "value_number": 25000,
        "unit": "SAR",
        "origin": "USER",
    }
    payload.update(overrides)
    return client.post(f"/studies/{study_id}/assumptions/", headers=headers, json=payload)


def test_ai_suggested_origin_is_explicit_and_never_defaults_to_user():
    headers = _headers("assume_ai")
    study = _study(headers)
    resp = _create(headers, study["id"], origin="AI_SUGGESTED", reason="Suggested from comparable nurseries")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["origin"] == "AI_SUGGESTED"


def test_evidence_derived_requires_valid_evidence_in_same_study():
    headers = _headers("assume_evidence")
    study = _study(headers)
    resp = _create(headers, study["id"], origin="EVIDENCE_DERIVED")
    assert resp.status_code == 422, resp.text  # missing evidence_id

    resp2 = _create(headers, study["id"], origin="EVIDENCE_DERIVED", evidence_id=999999)
    assert resp2.status_code == 422, resp2.text  # nonexistent evidence


def test_new_value_for_same_key_creates_a_new_version_and_retires_old():
    headers = _headers("assume_version")
    study = _study(headers)
    first = _create(headers, study["id"], value_number=25000).json()
    assert first["version"] == 1
    assert first["is_active"] is True

    second = _create(headers, study["id"], value_number=27000).json()
    assert second["version"] == 2
    assert second["is_active"] is True

    active = client.get(f"/studies/{study['id']}/assumptions/", headers=headers).json()
    assert len(active) == 1
    assert active[0]["value_number"] == 27000

    history = client.get(f"/studies/{study['id']}/assumptions/?include_inactive=true", headers=headers).json()
    versions = sorted(row["version"] for row in history if row["key"] == "monthly_rent")
    assert versions == [1, 2]


def test_retire_assumption_soft_deletes():
    headers = _headers("assume_retire")
    study = _study(headers)
    created = _create(headers, study["id"]).json()
    resp = client.delete(f"/studies/{study['id']}/assumptions/{created['id']}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is False
    active = client.get(f"/studies/{study['id']}/assumptions/", headers=headers).json()
    assert active == []


def test_assumption_ownership_isolation():
    owner = _headers("assume_owner")
    other = _headers("assume_other")
    study = _study(owner)
    created = _create(owner, study["id"]).json()

    assert client.get(f"/studies/{study['id']}/assumptions/", headers=other).status_code == 403
    assert _create(other, study["id"]).status_code == 403
    assert client.delete(f"/studies/{study['id']}/assumptions/{created['id']}", headers=other).status_code == 403
