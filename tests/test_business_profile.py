"""Business profile: upsert semantics, reuse across flows, ownership."""
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
    return client.post(
        "/feasibility/",
        headers=headers,
        json={"project_id": project["id"], "title": "دراسة حضانة", "industry": "education", "investment": 500000},
    ).json()


def test_get_before_any_upsert_returns_empty_profile():
    headers = _headers("profile_missing")
    study = _study(headers)
    resp = client.get(f"/studies/{study['id']}/business-profile/", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["study_id"] == study["id"]
    assert body["business_activity"] is None
    assert body["is_existing_business"] is False


def test_put_creates_then_partially_updates_without_clobbering_other_fields():
    headers = _headers("profile_upsert")
    study = _study(headers)

    created = client.put(
        f"/studies/{study['id']}/business-profile/",
        headers=headers,
        json={"business_activity": "Childcare nursery", "city": "Riyadh", "capacity_value": 30, "capacity_unit": "children"},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["business_activity"] == "Childcare nursery"
    assert body["city"] == "Riyadh"

    updated = client.put(
        f"/studies/{study['id']}/business-profile/",
        headers=headers,
        json={"customer_segment": "working parents"},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    # Fields not sent in the second PUT must survive (partial update, not a full replace).
    assert body["business_activity"] == "Childcare nursery"
    assert body["city"] == "Riyadh"
    assert body["customer_segment"] == "working parents"

    fetched = client.get(f"/studies/{study['id']}/business-profile/", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["capacity_value"] == 30


def test_rejects_unknown_fields():
    headers = _headers("profile_strict")
    study = _study(headers)
    resp = client.put(
        f"/studies/{study['id']}/business-profile/",
        headers=headers,
        json={"owner_id": 999, "business_activity": "x"},
    )
    assert resp.status_code == 422


def test_business_profile_ownership_isolation():
    owner = _headers("profile_owner")
    other = _headers("profile_other")
    study = _study(owner)
    client.put(f"/studies/{study['id']}/business-profile/", headers=owner, json={"city": "Riyadh"})

    assert client.get(f"/studies/{study['id']}/business-profile/", headers=other).status_code == 403
    assert client.put(f"/studies/{study['id']}/business-profile/", headers=other, json={"city": "hijacked"}).status_code == 403
