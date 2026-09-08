"""Independent-tool APIs: financial analyses, linking previews, notifications, analytics."""
import os
import sys
import tempfile
import uuid
from pathlib import Path

if not os.environ.get("DATABASE_URL"):
    handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    handle.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + handle.name
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-characters-long")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app import db as app_db  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
PASSWORD = "Sup3rSecret!"


def setup_module(module):
    app_db.init_db()


def _auth(prefix: str):
    email = f"{prefix}_{uuid.uuid4().hex[:12]}@example.com"
    assert client.post("/auth/register", json={"email": email, "password": PASSWORD}).status_code == 201
    token = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _study(headers):
    project = client.post(
        "/projects/",
        headers=headers,
        json={"name": "AI Logistics Startup", "industry": "logistics", "investment": 900000},
    ).json()
    study = client.post(
        "/feasibility/",
        headers=headers,
        json={
            "project_id": project["id"],
            "title": "AI Logistics feasibility",
            "industry": "logistics",
            "investment": 900000,
        },
    ).json()
    computed = client.post(
        f"/feasibility/{study['id']}/compute",
        headers=headers,
        json={"annual_cash_flows": [220000, 260000, 310000, 360000, 410000], "discount_rate": 0.1},
    )
    assert computed.status_code == 200, computed.text
    return project, computed.json()


def test_financial_analysis_persists_independently_and_is_owner_scoped():
    owner = _auth("fin_owner")
    other = _auth("fin_other")
    created = client.post(
        "/financial/analyses",
        headers=owner,
        json={
            "title": "Standalone warehouse model",
            "investment": 500000,
            "annual_cash_flows": [120000, 140000, 160000, 180000, 200000],
            "discount_rate": 0.1,
        },
    )
    assert created.status_code == 201, created.text
    analysis_id = created.json()["id"]
    assert created.json()["result"]["verdict"] in {"feasible", "borderline", "not_feasible"}
    listed = client.get("/financial/analyses", headers=owner)
    assert any(item["id"] == analysis_id for item in listed.json())
    assert client.get(f"/financial/analyses/{analysis_id}", headers=other).status_code == 404


def test_financial_import_preview_from_study_is_explicit():
    headers = _auth("fin_import")
    project, study = _study(headers)
    preview = client.get(f"/financial/from-study/{study['id']}", headers=headers)
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["source_record"] == f"feasibility_study:{study['id']}"
    assert "investment" in body["imported_fields"]
    assert body["project_id"] == project["id"]
    assert body["annual_cash_flows"]


def test_proposal_import_preview_does_not_create_a_proposal():
    headers = _auth("prop_import")
    _project, study = _study(headers)
    preview = client.get(f"/proposals/from-study/{study['id']}", headers=headers)
    assert preview.status_code == 200, preview.text
    assert preview.json()["study_title"]
    listed = client.get("/proposals/", headers=headers)
    assert listed.json() == []


def test_notifications_and_analytics_are_private():
    owner = _auth("notify_owner")
    other = _auth("notify_other")
    created = client.post(
        "/financial/analyses",
        headers=owner,
        json={"title": "Notify me", "investment": 100000, "annual_cash_flows": [30000, 40000, 50000]},
    )
    assert created.status_code == 201, created.text
    notes = client.get("/notifications/", headers=owner)
    assert notes.status_code == 200
    assert notes.json()
    note_id = notes.json()[0]["id"]
    assert client.post(f"/notifications/{note_id}/read", headers=other).status_code == 404
    tracked = client.post(
        "/analytics/events",
        headers=owner,
        json={"event_type": "tool_opened", "service_key": "financial_analysis"},
    )
    assert tracked.status_code == 202
    assert tracked.json()["accepted"] is True
    rejected = client.post(
        "/analytics/events",
        headers=owner,
        json={"event_type": "raw_business_description", "service_key": "feasibility"},
    )
    assert rejected.json()["accepted"] is False


def test_investor_package_requires_a_selected_source():
    headers = _auth("package")
    empty = client.post("/reports/investor-package", headers=headers, json={"locale": "en"})
    assert empty.status_code == 400
    project, study = _study(headers)
    package = client.post(
        "/reports/investor-package",
        headers=headers,
        json={"study_id": study["id"], "project_id": project["id"], "locale": "ar"},
    )
    assert package.status_code == 200, package.text
    assert package.headers["content-type"].startswith("application/pdf")


def test_entitlements_demo_provider_enables_tools_without_fake_checkout():
    headers = _auth("entitle")
    listed = client.get("/entitlements/", headers=headers)
    assert listed.status_code == 200
    keys = {row["service_key"] for row in listed.json()}
    assert "feasibility" in keys
    assert "proposal" in keys
    assert all(row["upgrade_required"] is False for row in listed.json())
