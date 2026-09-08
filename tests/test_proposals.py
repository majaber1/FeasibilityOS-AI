"""Proposal lifecycle, persistence, and owner-isolation regression tests."""
import os
import sys
import tempfile
import uuid
from pathlib import Path

if not os.environ.get("DATABASE_URL"):
    _tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _tmp.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + _tmp.name
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-characters-long")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app import db as app_db  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
PASSWORD = "Sup3rSecret!"


def setup_module(module):
    app_db.init_db()


def _auth(prefix: str) -> dict[str, str]:
    email = f"{prefix}_{uuid.uuid4().hex[:12]}@example.com"
    registered = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert registered.status_code == 201, registered.text
    login = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_proposal_lifecycle_persists_and_is_owner_scoped():
    owner = _auth("proposal_owner")
    other = _auth("proposal_other")

    created = client.post(
        "/proposals/",
        headers=owner,
        json={
            "title": "Market-entry proposal",
            "proposal_type": "commercial",
            "locale": "en",
            "payload": {"client_name": "Acme", "scope": "Saudi launch"},
        },
    )
    assert created.status_code == 201, created.text
    proposal_id = created.json()["id"]

    listed = client.get("/proposals/", headers=owner)
    assert listed.status_code == 200
    assert any(item["id"] == proposal_id for item in listed.json())

    forbidden_read = client.get(f"/proposals/{proposal_id}", headers=other)
    assert forbidden_read.status_code == 404

    updated = client.patch(
        f"/proposals/{proposal_id}",
        headers=owner,
        json={"title": "Updated proposal", "payload": {"price": "250000"}},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Updated proposal"
    assert updated.json()["payload"] == {
        "client_name": "Acme",
        "scope": "Saudi launch",
        "price": "250000",
    }

    deleted = client.delete(f"/proposals/{proposal_id}", headers=owner)
    assert deleted.status_code == 204, deleted.text
    assert client.get(f"/proposals/{proposal_id}", headers=owner).status_code == 404


def test_proposals_require_authentication():
    assert client.get("/proposals/").status_code == 401
    assert client.post("/proposals/", json={"title": "Anonymous"}).status_code == 401
