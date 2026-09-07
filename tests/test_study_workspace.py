"""Persistent study idempotency, ownership, and optimistic concurrency."""
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


def _project(headers):
    response = client.post(
        "/projects/",
        headers=headers,
        json={"name": "حضانة أطفال", "industry": "education", "investment": 500000},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _study(headers, project_id):
    return client.post(
        "/feasibility/",
        headers=headers,
        json={"project_id": project_id, "title": "دراسة حضانة", "industry": "education", "investment": 500000},
    )


def test_create_is_idempotent_for_project():
    headers = _headers("study_idempotent")
    project = _project(headers)
    first = _study(headers, project["id"])
    second = _study(headers, project["id"])
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]
    listing = client.get(f"/feasibility/?project_id={project['id']}", headers=headers)
    assert len(listing.json()) == 1


def test_study_rejects_other_owner():
    owner = _headers("study_owner")
    other = _headers("study_other")
    study = _study(owner, _project(owner)["id"]).json()
    assert client.get(f"/feasibility/{study['id']}", headers=other).status_code == 403
    assert client.patch(f"/feasibility/{study['id']}/step", headers=other, json={"step": 1, "data": {}}).status_code == 403


def test_autosave_revision_conflict_preserves_newer_data():
    headers = _headers("study_revision")
    study = _study(headers, _project(headers)["id"]).json()
    assert study["revision"] == 1
    saved = client.patch(
        f"/feasibility/{study['id']}/step",
        headers=headers,
        json={"step": 1, "data": {"notes": "newer"}, "expected_revision": 1},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 2
    stale = client.patch(
        f"/feasibility/{study['id']}/step",
        headers=headers,
        json={"step": 1, "data": {"notes": "stale"}, "expected_revision": 1},
    )
    assert stale.status_code == 409, stale.text
    current = client.get(f"/feasibility/{study['id']}", headers=headers).json()
    assert current["payload"]["step_1"]["notes"] == "newer"
    assert current["revision"] == 2
