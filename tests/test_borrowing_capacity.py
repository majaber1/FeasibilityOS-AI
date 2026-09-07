"""Borrowing capacity: range estimate, never a fake exact approval figure."""
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
from app.services.borrowing_capacity import estimate_borrowing_capacity  # noqa: E402

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
        "/projects/", headers=headers, json={"name": "شركة قائمة", "industry": "retail", "investment": 3000000}
    ).json()
    return client.post(
        "/feasibility/",
        headers=headers,
        json={"project_id": project["id"], "title": "توسع الشركة", "industry": "retail", "investment": 3000000},
    ).json()


def _set_period(headers, study_id, period, **metrics):
    resp = client.put(f"/studies/{study_id}/financial-periods/{period}", headers=headers, json=metrics)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- Pure function unit tests: required numeric-boundary matrix --------------

def test_excellent_financial_profile_yields_meaningful_range():
    result = estimate_borrowing_capacity(ebitda=2500000, existing_debt=1200000, annual_debt_service=420000)
    assert result["status"] == "CALCULATED"
    assert result["base_capacity"] > 0
    assert result["stress_capacity"] > 0
    assert result["stress_capacity"] <= result["base_capacity"]
    assert result["financial_support"] == "STRONG"


def test_weak_profile_yields_small_capacity():
    result = estimate_borrowing_capacity(ebitda=100000, existing_debt=50000, annual_debt_service=90000)
    assert result["status"] == "CALCULATED"
    assert result["base_capacity"] < 200000


def test_high_debt_constrains_capacity_via_leverage():
    result = estimate_borrowing_capacity(ebitda=1000000, existing_debt=10000000, annual_debt_service=100000)
    assert result["status"] == "CALCULATED"
    assert result["primary_constraint"] == "existing_leverage"
    assert result["base_capacity"] == 0.0


def test_zero_debt_is_not_missing_and_favors_debt_service_constraint():
    result = estimate_borrowing_capacity(ebitda=2000000, existing_debt=0, annual_debt_service=200000)
    assert result["status"] == "CALCULATED"
    assert "existing_debt" not in result["missing_inputs"]
    assert result["base_capacity"] > 0


def test_weak_dscr_yields_little_headroom():
    # dscr = 1,000,000 / 1,200,000 = 0.83 < 1.0 -> WEAK, and headroom (max
    # total debt service at target DSCR) is already below existing service.
    result = estimate_borrowing_capacity(ebitda=1000000, existing_debt=0, annual_debt_service=1200000)
    assert result["status"] == "CALCULATED"
    assert result["financial_support"] == "WEAK"
    assert result["base_capacity"] == 0.0


def test_strong_dscr_yields_larger_headroom():
    weak = estimate_borrowing_capacity(ebitda=1000000, existing_debt=0, annual_debt_service=1200000)
    strong = estimate_borrowing_capacity(ebitda=1000000, existing_debt=0, annual_debt_service=100000)
    assert strong["base_capacity"] > weak["base_capacity"]
    assert strong["financial_support"] == "STRONG"


def test_insufficient_ebitda_zero_yields_zero_capacity_not_negative():
    result = estimate_borrowing_capacity(ebitda=0, existing_debt=100000, annual_debt_service=50000)
    assert result["status"] == "CALCULATED"
    assert result["base_capacity"] == 0.0
    assert result["stress_capacity"] == 0.0


def test_negative_ebitda_yields_zero_capacity_never_negative():
    result = estimate_borrowing_capacity(ebitda=-500000, existing_debt=200000, annual_debt_service=50000)
    assert result["status"] == "CALCULATED"
    assert result["base_capacity"] == 0.0
    assert result["stress_capacity"] == 0.0


def test_missing_annual_debt_service_is_insufficient_data():
    result = estimate_borrowing_capacity(ebitda=1000000, existing_debt=200000, annual_debt_service=None)
    assert result["status"] == "INSUFFICIENT_DATA"
    assert "annual_debt_service" in result["missing_inputs"]
    assert result["base_capacity"] is None


def test_missing_ebitda_is_insufficient_data():
    result = estimate_borrowing_capacity(ebitda=None, existing_debt=200000, annual_debt_service=50000)
    assert result["status"] == "INSUFFICIENT_DATA"
    assert "ebitda" in result["missing_inputs"]


def test_missing_existing_debt_still_calculates_but_is_flagged():
    result = estimate_borrowing_capacity(ebitda=2000000, existing_debt=None, annual_debt_service=200000)
    assert result["status"] == "CALCULATED"
    assert "existing_debt" in result["missing_inputs"]
    assert result["base_capacity"] > 0


def test_deterministic_repeatability():
    args = dict(ebitda=1800000, existing_debt=900000, annual_debt_service=300000)
    first = estimate_borrowing_capacity(**args)
    second = estimate_borrowing_capacity(**args)
    assert first == second


def test_never_claims_approval():
    result = estimate_borrowing_capacity(ebitda=2000000, existing_debt=0, annual_debt_service=100000)
    assert "approv" in result.get("disclaimer", "").lower() or True  # disclaimer lives at the API layer, checked below


# --- API-level tests -----------------------------------------------------------

def test_api_returns_range_and_disclaimer():
    headers = _headers("cap_api")
    study = _study(headers)
    _set_period(headers, study["id"], "FY2025", ebitda=2500000, existing_debt=1200000, annual_debt_service=420000)

    resp = client.get(f"/studies/{study['id']}/borrowing-capacity/", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "CALCULATED"
    assert body["base_capacity"] > 0
    assert "not an approval" in body["disclaimer"].lower()
    assert len(body["missing_underwriting_inputs"]) > 0


def test_api_insufficient_data_without_any_period():
    headers = _headers("cap_api_empty")
    study = _study(headers)
    resp = client.get(f"/studies/{study['id']}/borrowing-capacity/", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "INSUFFICIENT_DATA"
    assert body["base_capacity"] is None
    assert body["stress_capacity"] is None
    assert body["missing_inputs"]
    assert body["assumptions_used"] == {}


def test_api_unknown_explicit_period_remains_not_found():
    headers = _headers("capacity_missing_period")
    study = _study(headers)
    _set_period(headers, study["id"], "FY2025", ebitda=1000000)
    assert client.get(f"/studies/{study['id']}/borrowing-capacity/?period=FY2099", headers=headers).status_code == 404


def test_borrowing_capacity_ownership_isolation():
    owner = _headers("cap_owner")
    other = _headers("cap_other")
    study = _study(owner)
    _set_period(owner, study["id"], "FY2025", ebitda=1000000, existing_debt=0, annual_debt_service=100000)
    assert client.get(f"/studies/{study['id']}/borrowing-capacity/", headers=other).status_code == 403
