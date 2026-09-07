"""Funding gap: reuses existing data, never silently zeroes missing inputs."""
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
from app.services.funding_gap import compute_funding_gap  # noqa: E402

client = TestClient(app)


def setup_module(module):
    app_db.init_db()


def _headers(prefix: str):
    email = f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    password = "Sup3rSecret!"
    assert client.post("/auth/register", json={"email": email, "password": password}).status_code == 201
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _study(headers, investment=3000000):
    project = client.post(
        "/projects/", headers=headers, json={"name": "شركة قائمة", "industry": "retail", "investment": investment}
    ).json()
    return client.post(
        "/feasibility/",
        headers=headers,
        json={"project_id": project["id"], "title": "توسع الشركة", "industry": "retail", "investment": investment},
    ).json()


def _set_assumption(headers, study_id, key, value):
    resp = client.post(
        f"/studies/{study_id}/assumptions/",
        headers=headers,
        json={"key": key, "label_en": key, "label_ar": key, "value_number": value, "origin": "USER"},
    )
    assert resp.status_code == 201, resp.text


# --- Pure function unit tests -------------------------------------------------

def test_matches_the_worked_example_from_the_spec():
    result = compute_funding_gap(
        capex_assumption=3000000, project_investment=0, owner_contribution=750000, existing_facilities=0
    )
    assert result["total_project_requirement"] == 3000000
    assert result["funding_gap"] == 2250000
    assert result["missing_inputs"] == []


def test_falls_back_to_project_investment_when_no_capex_assumption():
    result = compute_funding_gap(
        capex_assumption=None, project_investment=500000, owner_contribution=None, existing_facilities=None
    )
    assert result["total_project_requirement"] == 500000
    assert result["requirement_source"] == "project_investment"


def test_missing_owner_contribution_is_flagged_not_silently_zero():
    result = compute_funding_gap(
        capex_assumption=1000000, project_investment=0, owner_contribution=None, existing_facilities=0
    )
    assert result["owner_available_capital_status"] == "MISSING_DATA"
    assert "owner_contribution" in result["missing_inputs"]
    assert result["funding_gap"] == 1000000  # still computed, treating unset as 0


# --- API-level tests -----------------------------------------------------------

def test_api_reuses_project_investment_and_recorded_assumptions():
    headers = _headers("gap_api")
    study = _study(headers, investment=3000000)
    _set_assumption(headers, study["id"], "owner_contribution", 750000)

    resp = client.get(f"/studies/{study['id']}/funding-gap/", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_project_requirement"] == 3000000
    assert body["requirement_source"] == "project_investment"
    assert body["owner_available_capital"] == 750000
    assert body["funding_gap"] == 2250000
    assert "existing_available_facilities" in body["missing_inputs"]


def test_api_prefers_capex_assumption_over_project_investment():
    headers = _headers("gap_capex")
    study = _study(headers, investment=3000000)
    _set_assumption(headers, study["id"], "capex", 2500000)

    resp = client.get(f"/studies/{study['id']}/funding-gap/", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_project_requirement"] == 2500000
    assert body["requirement_source"] == "capex_assumption"


def test_funding_gap_ownership_isolation():
    owner = _headers("gap_owner")
    other = _headers("gap_other")
    study = _study(owner)
    assert client.get(f"/studies/{study['id']}/funding-gap/", headers=other).status_code == 403
