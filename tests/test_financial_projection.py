"""Compute-from-assumptions: deterministic, reproducible, no invented inputs."""
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
from app.services.financial_projection import missing_required_keys, project_cash_flows  # noqa: E402

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


def _set_assumption(headers, study_id, key, value, unit="SAR"):
    return client.post(
        f"/studies/{study_id}/assumptions/",
        headers=headers,
        json={"key": key, "label_en": key, "label_ar": key, "value_number": value, "unit": unit, "origin": "USER"},
    )


def test_project_cash_flows_pure_function_growth_and_flat_opex():
    investment, flows, discount_rate = project_cash_flows(
        {"capex": 500000, "revenue_year1": 100000, "opex_annual": 20000, "growth_rate": 0.10, "horizon_years": 3}
    )
    assert investment == 500000
    assert discount_rate == 0.10  # default, not supplied
    assert flows == [100000 - 20000, 100000 * 1.10 - 20000, 100000 * 1.10**2 - 20000]


def test_missing_required_keys_detected():
    assert missing_required_keys({}) == ["capex", "revenue_year1"]
    assert missing_required_keys({"capex": 1}) == ["revenue_year1"]
    assert missing_required_keys({"capex": 1, "revenue_year1": 2}) == []


def test_compute_from_assumptions_requires_capex_and_revenue():
    headers = _headers("proj_missing")
    study = _study(headers)
    resp = client.post(f"/feasibility/{study['id']}/compute-from-assumptions", headers=headers)
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert set(detail["missing"]) == {"capex", "revenue_year1"}


def test_compute_from_assumptions_uses_recorded_values_and_is_reproducible():
    headers = _headers("proj_ok")
    study = _study(headers)
    _set_assumption(headers, study["id"], "capex", 500000)
    _set_assumption(headers, study["id"], "revenue_year1", 300000)
    _set_assumption(headers, study["id"], "opex_annual", 150000)
    _set_assumption(headers, study["id"], "growth_rate", 0.05, unit="%")

    first = client.post(f"/feasibility/{study['id']}/compute-from-assumptions", headers=headers)
    assert first.status_code == 200, first.text
    first_result = first.json()["result"]

    second = client.post(f"/feasibility/{study['id']}/compute-from-assumptions", headers=headers)
    assert second.status_code == 200, second.text
    second_result = second.json()["result"]

    # Same assumptions -> same deterministic result every time.
    assert first_result["npv"] == second_result["npv"]
    assert first_result["roi_percent"] == second_result["roi_percent"]
    assert first_result["verdict"] == second_result["verdict"]


def test_updating_an_assumption_changes_the_next_computed_result():
    headers = _headers("proj_update")
    study = _study(headers)
    _set_assumption(headers, study["id"], "capex", 500000)
    _set_assumption(headers, study["id"], "revenue_year1", 100000)
    before = client.post(f"/feasibility/{study['id']}/compute-from-assumptions", headers=headers).json()["result"]

    _set_assumption(headers, study["id"], "revenue_year1", 900000)  # retires v1, creates v2
    after = client.post(f"/feasibility/{study['id']}/compute-from-assumptions", headers=headers).json()["result"]

    assert before["npv"] != after["npv"]


def test_compute_from_assumptions_ownership_isolation():
    owner = _headers("proj_owner")
    other = _headers("proj_other")
    study = _study(owner)
    _set_assumption(owner, study["id"], "capex", 100000)
    _set_assumption(owner, study["id"], "revenue_year1", 50000)
    assert client.post(f"/feasibility/{study['id']}/compute-from-assumptions", headers=other).status_code == 403
