"""Scenario engine: explicit assumption overrides, not blanket %, reproducible."""
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


def _set_assumption(headers, study_id, key, value):
    resp = client.post(
        f"/studies/{study_id}/assumptions/",
        headers=headers,
        json={"key": key, "label_en": key, "label_ar": key, "value_number": value, "origin": "USER"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_scenario_rejects_unknown_override_keys():
    headers = _headers("scen_unknown")
    study = _study(headers)
    resp = client.post(
        f"/studies/{study['id']}/scenarios/",
        headers=headers,
        json={"scenario_type": "BASE", "assumption_overrides": {"occupancy_rate": 0.65}},
    )
    assert resp.status_code == 422, resp.text


def test_scenario_requires_required_assumptions_present_or_overridden():
    headers = _headers("scen_missing")
    study = _study(headers)
    resp = client.post(f"/studies/{study['id']}/scenarios/", headers=headers, json={"scenario_type": "BASE"})
    assert resp.status_code == 422, resp.text
    assert set(resp.json()["detail"]["missing"]) == {"capex", "revenue_year1"}


def test_base_conservative_optimistic_use_explicit_overrides_not_blanket_percent():
    headers = _headers("scen_explicit")
    study = _study(headers)
    _set_assumption(headers, study["id"], "capex", 500000)
    _set_assumption(headers, study["id"], "revenue_year1", 300000)
    _set_assumption(headers, study["id"], "opex_annual", 150000)

    base = client.post(f"/studies/{study['id']}/scenarios/", headers=headers, json={"scenario_type": "BASE"}).json()

    conservative = client.post(
        f"/studies/{study['id']}/scenarios/",
        headers=headers,
        json={"scenario_type": "CONSERVATIVE", "assumption_overrides": {"revenue_year1": 210000, "opex_annual": 165000}},
    ).json()

    optimistic = client.post(
        f"/studies/{study['id']}/scenarios/",
        headers=headers,
        json={"scenario_type": "OPTIMISTIC", "assumption_overrides": {"revenue_year1": 390000}},
    ).json()

    # Overrides are explicit named assumptions, not a derived blanket %.
    assert conservative["assumption_overrides"] == {"revenue_year1": 210000, "opex_annual": 165000}
    assert optimistic["assumption_overrides"] == {"revenue_year1": 390000}

    # The three scenarios produce genuinely different, explainable results.
    assert conservative["financial_result_snapshot"]["npv"] < base["financial_result_snapshot"]["npv"]
    assert optimistic["financial_result_snapshot"]["npv"] > base["financial_result_snapshot"]["npv"]

    # capex came from a base assumption in every case; provenance is traceable.
    assert conservative["source_assumption_values"]["capex"]["origin"] == "assumption"
    assert conservative["source_assumption_values"]["revenue_year1"]["origin"] == "override"


def test_scenario_never_mutates_the_studys_base_assumptions():
    headers = _headers("scen_no_mutate")
    study = _study(headers)
    _set_assumption(headers, study["id"], "capex", 500000)
    _set_assumption(headers, study["id"], "revenue_year1", 300000)

    client.post(
        f"/studies/{study['id']}/scenarios/",
        headers=headers,
        json={"scenario_type": "CONSERVATIVE", "assumption_overrides": {"revenue_year1": 100000}},
    )

    active = client.get(f"/studies/{study['id']}/assumptions/", headers=headers).json()
    revenue_assumption = next(a for a in active if a["key"] == "revenue_year1")
    assert revenue_assumption["value_number"] == 300000  # untouched by the scenario override


def test_scenario_computation_is_deterministic_and_reproducible():
    headers = _headers("scen_repro")
    study = _study(headers)
    _set_assumption(headers, study["id"], "capex", 500000)
    _set_assumption(headers, study["id"], "revenue_year1", 300000)

    first = client.post(
        f"/studies/{study['id']}/scenarios/",
        headers=headers,
        json={"scenario_type": "BASE"},
    ).json()
    second = client.post(
        f"/studies/{study['id']}/scenarios/",
        headers=headers,
        json={"scenario_type": "BASE"},
    ).json()

    assert first["financial_result_snapshot"]["npv"] == second["financial_result_snapshot"]["npv"]
    assert first["calculation_version"] == second["calculation_version"]


def test_compare_returns_latest_run_per_scenario_type():
    headers = _headers("scen_compare")
    study = _study(headers)
    _set_assumption(headers, study["id"], "capex", 500000)
    _set_assumption(headers, study["id"], "revenue_year1", 300000)

    client.post(f"/studies/{study['id']}/scenarios/", headers=headers, json={"scenario_type": "BASE"})
    client.post(
        f"/studies/{study['id']}/scenarios/", headers=headers,
        json={"scenario_type": "CONSERVATIVE", "assumption_overrides": {"revenue_year1": 200000}},
    )

    compared = client.get(f"/studies/{study['id']}/scenarios/compare", headers=headers).json()
    assert compared["BASE"] is not None
    assert compared["CONSERVATIVE"] is not None
    assert compared["OPTIMISTIC"] is None


def test_scenario_ownership_isolation():
    owner = _headers("scen_owner")
    other = _headers("scen_other")
    study = _study(owner)
    _set_assumption(owner, study["id"], "capex", 500000)
    _set_assumption(owner, study["id"], "revenue_year1", 300000)

    assert client.post(f"/studies/{study['id']}/scenarios/", headers=other, json={"scenario_type": "BASE"}).status_code == 403
    assert client.get(f"/studies/{study['id']}/scenarios/", headers=other).status_code == 403
