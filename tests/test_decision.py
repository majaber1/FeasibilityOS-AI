"""Explainable decision engine: deterministic, traceable, not an AI score."""
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
from app.services.decision_engine import evaluate_decision  # noqa: E402

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


def _add_evidence(headers, study_id, title="Lease quote"):
    resp = client.post(
        f"/studies/{study_id}/evidence",
        headers=headers,
        json={"source_type": "user_document", "title": title, "claim": "some claim"},
    )
    assert resp.status_code == 201, resp.text


def _run_scenario(headers, study_id, scenario_type, overrides=None):
    resp = client.post(
        f"/studies/{study_id}/scenarios/",
        headers=headers,
        json={"scenario_type": scenario_type, "assumption_overrides": overrides or {}},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- Pure function unit tests -------------------------------------------------

def test_no_base_scenario_is_insufficient_evidence():
    outcome = evaluate_decision(evidence_count=5, base_scenario=None, conservative_scenario=None)
    assert outcome["decision"] == "INSUFFICIENT_EVIDENCE"


def test_no_evidence_is_insufficient_evidence_even_with_good_financials():
    base = {"id": 1, "financial_result_snapshot": {"verdict": "feasible", "npv": 500000}, "source_assumption_values": {}}
    outcome = evaluate_decision(evidence_count=0, base_scenario=base, conservative_scenario=None)
    assert outcome["decision"] == "INSUFFICIENT_EVIDENCE"


def test_negative_base_npv_is_no_go():
    base = {"id": 1, "financial_result_snapshot": {"verdict": "not_feasible", "npv": -200000}, "source_assumption_values": {}}
    outcome = evaluate_decision(evidence_count=3, base_scenario=base, conservative_scenario=None)
    assert outcome["decision"] == "NO_GO"


def test_feasible_base_with_negative_conservative_is_conditional_go():
    base = {"id": 1, "financial_result_snapshot": {"verdict": "feasible", "npv": 500000}, "source_assumption_values": {}}
    conservative = {"id": 2, "financial_result_snapshot": {"verdict": "not_feasible", "npv": -50000}, "source_assumption_values": {}}
    outcome = evaluate_decision(evidence_count=3, base_scenario=base, conservative_scenario=conservative)
    assert outcome["decision"] == "CONDITIONAL_GO"
    assert outcome["conditions"]


def test_feasible_base_and_positive_conservative_is_go():
    base = {"id": 1, "financial_result_snapshot": {"verdict": "feasible", "npv": 500000}, "source_assumption_values": {"capex": {"value": 500000}}}
    conservative = {"id": 2, "financial_result_snapshot": {"verdict": "feasible", "npv": 50000}, "source_assumption_values": {}}
    outcome = evaluate_decision(evidence_count=3, base_scenario=base, conservative_scenario=conservative)
    assert outcome["decision"] == "GO"
    assert outcome["key_drivers"] == ["capex=500000"]


def test_borderline_base_is_conditional_go():
    base = {"id": 1, "financial_result_snapshot": {"verdict": "borderline", "npv": 100}, "source_assumption_values": {}}
    outcome = evaluate_decision(evidence_count=3, base_scenario=base, conservative_scenario=None)
    assert outcome["decision"] == "CONDITIONAL_GO"


def test_deterministic_same_input_same_output():
    base = {"id": 1, "financial_result_snapshot": {"verdict": "feasible", "npv": 300000}, "source_assumption_values": {}}
    first = evaluate_decision(evidence_count=2, base_scenario=base, conservative_scenario=None)
    second = evaluate_decision(evidence_count=2, base_scenario=base, conservative_scenario=None)
    assert first == second


# --- API-level tests -----------------------------------------------------------

def test_api_go_decision_traces_to_evidence_and_scenarios():
    headers = _headers("decision_go")
    study = _study(headers)
    _set_assumption(headers, study["id"], "capex", 500000)
    _set_assumption(headers, study["id"], "revenue_year1", 900000)
    _set_assumption(headers, study["id"], "opex_annual", 100000)
    _add_evidence(headers, study["id"], "Market demand study")
    _add_evidence(headers, study["id"], "Rent quote")
    base = _run_scenario(headers, study["id"], "BASE")
    conservative = _run_scenario(headers, study["id"], "CONSERVATIVE", {"revenue_year1": 700000})

    resp = client.post(f"/studies/{study['id']}/decision/", headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["decision"] in ("GO", "CONDITIONAL_GO")
    assert body["scenario_references"]["BASE"] == base["id"]
    assert body["scenario_references"]["CONSERVATIVE"] == conservative["id"]
    assert len(body["evidence_references"]) == 2


def test_api_insufficient_evidence_without_any_scenario():
    headers = _headers("decision_none")
    study = _study(headers)
    resp = client.post(f"/studies/{study['id']}/decision/", headers=headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["decision"] == "INSUFFICIENT_EVIDENCE"


def test_decision_history_preserves_prior_decisions():
    headers = _headers("decision_history")
    study = _study(headers)
    first = client.post(f"/studies/{study['id']}/decision/", headers=headers).json()
    _set_assumption(headers, study["id"], "capex", 500000)
    _set_assumption(headers, study["id"], "revenue_year1", 800000)
    _add_evidence(headers, study["id"])
    _run_scenario(headers, study["id"], "BASE")
    second = client.post(f"/studies/{study['id']}/decision/", headers=headers).json()

    history = client.get(f"/studies/{study['id']}/decision/history", headers=headers).json()
    ids = {row["id"] for row in history}
    assert first["id"] in ids and second["id"] in ids
    assert first["decision"] != second["decision"]

    latest = client.get(f"/studies/{study['id']}/decision/", headers=headers).json()
    assert latest["id"] == second["id"]


def test_decision_ownership_isolation():
    owner = _headers("decision_owner")
    other = _headers("decision_other")
    study = _study(owner)
    client.post(f"/studies/{study['id']}/decision/", headers=owner)

    assert client.post(f"/studies/{study['id']}/decision/", headers=other).status_code == 403
    assert client.get(f"/studies/{study['id']}/decision/", headers=other).status_code == 403
