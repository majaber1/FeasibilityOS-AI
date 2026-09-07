"""
Funding Readiness Tests (Phase 17).

Test Matrix:
- strong complete profile (READY)
- strong financials but missing collateral verification (PARTIALLY_READY)
- missing EBITDA (NEEDS_INFORMATION)
- missing annual debt service (NEEDS_INFORMATION)
- unknown project cost (NEEDS_INFORMATION)
- unknown owner contribution (NEEDS_INFORMATION)
- no financial period (NEEDS_INFORMATION)
- funding gap greater than estimated capacity (PARTIALLY_READY)
- weak financial health (NOT_READY)
- high leverage (NOT_READY)
- weak debt service (NOT_READY)
- no collateral (PARTIALLY_READY with warning)
- encumbered collateral (warning / factors)
- verified collateral (positive factor)
- deterministic repeatability
- cross-owner forbidden (403)
- recalculation upon owner contribution change
- recalculation upon collateral verification change
"""
import os
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

if not os.environ.get("DATABASE_URL"):
    handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    handle.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + handle.name

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from app import db as app_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.funding_readiness import (  # noqa: E402
    STATUS_NEEDS_INFO,
    STATUS_NOT_READY,
    STATUS_PARTIALLY_READY,
    STATUS_READY,
    evaluate_funding_readiness,
)

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
        "/projects/", headers=headers, json={"name": "شركة صناعية قائمة", "industry": "manufacturing", "investment": investment}
    ).json()
    study = client.post(
        "/feasibility/",
        headers=headers,
        json={"project_id": project["id"], "title": "توسعة خط الإنتاج", "industry": "manufacturing", "investment": investment},
    ).json()
    return project, study


def _set_period(headers, study_id, period="FY2025", **metrics):
    payload = {
        "revenue": 12500000,
        "ebitda": 2500000,
        "net_profit": 1800000,
        "existing_debt": 1200000,
        "annual_debt_service": 420000,
        "cash": 1100000,
        "current_assets": 3000000,
        "current_liabilities": 1200000,
        "source": "financial_statement",
    }
    payload.update(metrics)
    resp = client.put(f"/studies/{study_id}/financial-periods/{period}", headers=headers, json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _set_assumption(headers, study_id, key, value_number):
    resp = client.post(
        f"/studies/{study_id}/assumptions/",
        headers=headers,
        json={"key": key, "label_en": key, "label_ar": key, "value_number": value_number, "origin": "USER"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _add_collateral(headers, study_id, **fields):
    payload = {
        "collateral_type": "PROPERTY",
        "description": "Commercial Warehouse",
        "reported_value": 4000000,
        "verification_status": "DOCUMENT_SUPPORTED",
        "verified_value": 4000000,
        "encumbrance_status": "UNENCUMBERED",
    }
    payload.update(fields)
    resp = client.post(f"/studies/{study_id}/collateral/", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ==============================================================================
# PURE DOMAIN SERVICE UNIT TESTS
# ==============================================================================

def test_missing_ebitda_needs_information():
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=3000000,
        owner_contribution=750000,
        financial_period={"revenue": 10000000, "annual_debt_service": 200000},  # ebitda missing
    )
    assert result["status"] == STATUS_NEEDS_INFO
    assert any("EBITDA" in item for item in result["missing_information"])


def test_missing_annual_debt_service_needs_information():
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=3000000,
        owner_contribution=750000,
        financial_period={"revenue": 10000000, "ebitda": 2000000},  # debt service missing
    )
    assert result["status"] == STATUS_NEEDS_INFO
    assert any("debt service" in item.lower() for item in result["missing_information"])


def test_no_financial_period_needs_information():
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=3000000,
        owner_contribution=750000,
        financial_period=None,
    )
    assert result["status"] == STATUS_NEEDS_INFO
    assert any("financial statements" in item.lower() for item in result["missing_information"])


def test_unknown_project_cost_needs_information():
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=0,
        capex_assumption=None,
        owner_contribution=500000,
        financial_period={"revenue": 10000000, "ebitda": 2000000, "annual_debt_service": 200000},
    )
    assert result["status"] == STATUS_NEEDS_INFO
    assert any("investment" in item.lower() or "cost" in item.lower() for item in result["missing_information"])


def test_unknown_owner_contribution_needs_information():
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=3000000,
        owner_contribution=None,  # missing
        financial_period={"revenue": 10000000, "ebitda": 2000000, "annual_debt_service": 200000},
    )
    assert result["status"] == STATUS_NEEDS_INFO
    assert any("owner" in item.lower() for item in result["missing_information"])


def test_negative_ebitda_is_not_ready():
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=3000000,
        owner_contribution=750000,
        financial_period={"revenue": 5000000, "ebitda": -200000, "annual_debt_service": 100000},
    )
    assert result["status"] == STATUS_NOT_READY
    assert any("EBITDA" in b or "Operating cash" in b for b in result["blocking_factors"])


def test_weak_debt_service_dscr_below_1_is_not_ready():
    # EBITDA 200k, debt service 300k => DSCR = 0.67 < 1.0
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=3000000,
        owner_contribution=750000,
        financial_period={"revenue": 5000000, "ebitda": 200000, "annual_debt_service": 300000},
    )
    assert result["status"] == STATUS_NOT_READY
    assert any("DSCR" in b or "coverage" in b for b in result["blocking_factors"])


def test_high_leverage_above_5_is_not_ready():
    # Existing debt 6M, EBITDA 1M => Debt/EBITDA = 6.0x > 5.0x
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=3000000,
        owner_contribution=750000,
        financial_period={"revenue": 5000000, "ebitda": 1000000, "existing_debt": 6000000, "annual_debt_service": 200000},
    )
    assert result["status"] == STATUS_NOT_READY
    assert any("leverage" in b.lower() for b in result["blocking_factors"])


def test_strong_complete_profile_is_ready():
    # Revenue 12.5M, EBITDA 2.5M, existing debt 1.2M, debt service 420k, project 3M, owner 750k (gap = 2.25M), base capacity ~7.11M
    # Collateral verified 4M
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=3000000,
        owner_contribution=750000,
        financial_period={
            "revenue": 12500000,
            "ebitda": 2500000,
            "net_profit": 1800000,
            "existing_debt": 1200000,
            "annual_debt_service": 420000,
        },
        collateral_records=[
            {"reported_value": 4000000, "verified_value": 4000000, "verification_status": "DOCUMENT_SUPPORTED", "encumbrance_status": "UNENCUMBERED", "encumbrance_amount": None}
        ],
    )
    assert result["status"] == STATUS_READY
    assert len(result["blocking_factors"]) == 0
    assert len(result["missing_information"]) == 0
    assert len(result["warnings"]) == 0
    assert any("DSCR" in p for p in result["positive_factors"])
    assert any("covers" in p for p in result["positive_factors"])


def test_verified_collateral_positive_factor():
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=3000000,
        owner_contribution=750000,
        financial_period={
            "revenue": 12500000,
            "ebitda": 2500000,
            "net_profit": 1800000,
            "existing_debt": 1200000,
            "annual_debt_service": 420000,
        },
        collateral_records=[
            {"reported_value": 4000000, "verified_value": 4000000, "verification_status": "VERIFIED", "encumbrance_status": "UNENCUMBERED", "encumbrance_amount": None}
        ],
    )
    assert any("explicitly verified collateral value" in p for p in result["positive_factors"])


def test_weak_financial_health_is_not_ready():
    # Negative EBITDA and operating at loss
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=3000000,
        owner_contribution=750000,
        financial_period={
            "revenue": 3000000,
            "ebitda": -150000,
            "net_profit": -500000,
            "existing_debt": 2000000,
            "annual_debt_service": 300000,
        },
        collateral_records=[],
    )
    assert result["status"] == STATUS_NOT_READY
    assert len(result["blocking_factors"]) > 0


def test_strong_financials_with_unverified_collateral_is_partially_ready():
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=3000000,
        owner_contribution=750000,
        financial_period={
            "revenue": 12500000,
            "ebitda": 2500000,
            "net_profit": 1800000,
            "existing_debt": 1200000,
            "annual_debt_service": 420000,
        },
        collateral_records=[
            {"reported_value": 4000000, "verified_value": None, "verification_status": "USER_REPORTED", "encumbrance_status": "UNKNOWN", "encumbrance_amount": None}
        ],
    )
    assert result["status"] == STATUS_PARTIALLY_READY
    assert any("unverified" in w or "user-reported" in w for w in result["warnings"])


def test_funding_gap_exceeds_capacity_is_partially_ready():
    # Gap = 10M - 500k = 9.5M, but capacity with EBITDA 1M, debt service 250k is ~2.4M
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=10000000,
        owner_contribution=500000,
        financial_period={
            "revenue": 8000000,
            "ebitda": 1000000,
            "annual_debt_service": 250000,
            "existing_debt": 500000,
        },
        collateral_records=[
            {"reported_value": 5000000, "verified_value": 5000000, "verification_status": "VERIFIED", "encumbrance_status": "UNENCUMBERED", "encumbrance_amount": None}
        ],
    )
    assert result["status"] == STATUS_PARTIALLY_READY
    assert any("does not fully cover" in w for w in result["warnings"])


def test_no_collateral_is_partially_ready_with_warning():
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=3000000,
        owner_contribution=750000,
        financial_period={
            "revenue": 12500000,
            "ebitda": 2500000,
            "existing_debt": 1200000,
            "annual_debt_service": 420000,
        },
        collateral_records=[],
    )
    assert result["status"] == STATUS_PARTIALLY_READY
    assert any("No collateral" in w for w in result["warnings"])


def test_encumbered_collateral_warning():
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=3000000,
        owner_contribution=750000,
        financial_period={
            "revenue": 12500000,
            "ebitda": 2500000,
            "existing_debt": 1200000,
            "annual_debt_service": 420000,
        },
        collateral_records=[
            {"reported_value": 4000000, "verified_value": 4000000, "verification_status": "VERIFIED", "encumbrance_status": "UNKNOWN", "encumbrance_amount": None}
        ],
    )
    assert result["status"] == STATUS_PARTIALLY_READY
    assert any("Encumbrance status is unknown" in w for w in result["warnings"])


def test_deterministic_repeatability():
    params = {
        "study_id": 42,
        "project_investment": 3000000,
        "owner_contribution": 750000,
        "financial_period": {"revenue": 12500000, "ebitda": 2500000, "existing_debt": 1200000, "annual_debt_service": 420000},
        "collateral_records": [{"reported_value": 4000000, "verified_value": 4000000, "verification_status": "VERIFIED", "encumbrance_status": "UNENCUMBERED", "encumbrance_amount": None}],
    }
    r1 = evaluate_funding_readiness(**params)
    r2 = evaluate_funding_readiness(**params)
    assert r1 == r2


def test_internal_thresholds_not_represented_as_verified_lender_rules():
    from app.services.funding_readiness import INTERNAL_SCREENING_ASSUMPTIONS
    assert "min_dscr_ready" in INTERNAL_SCREENING_ASSUMPTIONS
    assert "min_owner_equity_pct" in INTERNAL_SCREENING_ASSUMPTIONS

    # Trigger warnings for low equity and tight DSCR
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=3000000,
        owner_contribution=100000,  # 3.3% < 15%
        financial_period={
            "revenue": 10000000,
            "ebitda": 1000000,
            "existing_debt": 1000000,
            "annual_debt_service": 900000,  # DSCR = 1.11 < 1.25
        },
    )
    assert "internal_screening_assumptions" in result
    all_text = " ".join(result["warnings"] + result["positive_factors"] + [result["summary_en"]])
    # Must NOT present internal thresholds as verified Saudi lender rules or institutional mandates
    assert "Saudi lenders typically require" not in all_text
    assert "institutional leverage thresholds" not in all_text
    assert "official" not in all_text.lower()
    # Must clearly reference internal screening
    assert "internal screening" in all_text.lower()


def test_document_supported_without_verified_value_does_not_inflate_verified_collateral_value():
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=3000000,
        owner_contribution=750000,
        financial_period={
            "revenue": 12500000,
            "ebitda": 2500000,
            "existing_debt": 1200000,
            "annual_debt_service": 420000,
        },
        collateral_records=[
            {
                "reported_value": 5000000,
                "verified_value": None,  # no verified value!
                "verification_status": "DOCUMENT_SUPPORTED",
                "encumbrance_status": "UNENCUMBERED",
                "encumbrance_amount": None,
            }
        ],
    )
    # Must NOT be READY because valuation is not independently verified
    assert result["status"] == STATUS_PARTIALLY_READY
    # Warning must state document supported, value not independently verified
    assert any("document supported, value not independently verified" in w for w in result["warnings"])
    # Verified value must NOT be inflated by reported_value
    assert result["collateral_snapshot"]["total_verified_value"] == 0
    # No claim of 5M verified value in positive factors
    assert not any("5,000,000" in p for p in result["positive_factors"])
    assert not any("verified collateral value" in p for p in result["positive_factors"])


def test_user_reported_collateral_does_not_become_verified():
    result = evaluate_funding_readiness(
        study_id=1,
        project_investment=3000000,
        owner_contribution=750000,
        financial_period={
            "revenue": 12500000,
            "ebitda": 2500000,
            "existing_debt": 1200000,
            "annual_debt_service": 420000,
        },
        collateral_records=[
            {
                "reported_value": 8000000,
                "verified_value": None,
                "verification_status": "USER_REPORTED",
                "encumbrance_status": "UNENCUMBERED",
                "encumbrance_amount": None,
            }
        ],
    )
    assert result["status"] == STATUS_PARTIALLY_READY
    assert any("user-reported or unverified without documentation" in w for w in result["warnings"])
    assert result["collateral_snapshot"]["total_verified_value"] == 0
    assert not any("verified collateral value" in p for p in result["positive_factors"])


def test_funding_readiness_remains_deterministic():
    kwargs = {
        "study_id": 99,
        "project_investment": 4500000,
        "owner_contribution": 1000000,
        "financial_period": {
            "revenue": 15000000,
            "ebitda": 3000000,
            "existing_debt": 1500000,
            "annual_debt_service": 500000,
        },
        "collateral_records": [
            {"reported_value": 3000000, "verified_value": 3000000, "verification_status": "VERIFIED", "encumbrance_status": "UNENCUMBERED", "encumbrance_amount": None},
            {"reported_value": 2000000, "verified_value": None, "verification_status": "DOCUMENT_SUPPORTED", "encumbrance_status": "UNENCUMBERED", "encumbrance_amount": None},
        ],
    }
    r1 = evaluate_funding_readiness(**kwargs)
    r2 = evaluate_funding_readiness(**kwargs)
    r3 = evaluate_funding_readiness(**kwargs)
    assert r1 == r2 == r3


# ==============================================================================
# API-LEVEL INTEGRATION TESTS
# ==============================================================================

def test_api_readiness_golden_flow():
    headers = _headers("readiness_golden")
    proj, study = _study(headers, investment=3000000)
    study_id = study["id"]

    # 1. Initially without data -> NEEDS_INFORMATION
    r_init = client.get(f"/studies/{study_id}/funding-readiness/", headers=headers)
    assert r_init.status_code == 200, r_init.text
    body_init = r_init.json()
    assert body_init["status"] == STATUS_NEEDS_INFO
    assert len(body_init["missing_information"]) > 0

    # 2. Add owner contribution (750k)
    _set_assumption(headers, study_id, "owner_contribution", 750000)

    # 3. Add financial period (Golden fixture: Rev 12.5M, EBITDA 2.5M, Debt 1.2M, Service 420k)
    _set_period(headers, study_id, "FY2025")

    # 4. Now has financial data but no collateral -> PARTIALLY_READY (no collateral warning)
    r_mid = client.get(f"/studies/{study_id}/funding-readiness/", headers=headers)
    assert r_mid.status_code == 200
    assert r_mid.json()["status"] == STATUS_PARTIALLY_READY

    # 5. Add user-reported collateral -> PARTIALLY_READY (unverified collateral warning)
    col = _add_collateral(headers, study_id, reported_value=4000000, verified_value=None, verification_status="USER_REPORTED", encumbrance_status="UNKNOWN")
    r_col_unverified = client.get(f"/studies/{study_id}/funding-readiness/", headers=headers)
    assert r_col_unverified.json()["status"] == STATUS_PARTIALLY_READY
    assert any("user-reported" in w.lower() or "unverified" in w.lower() for w in r_col_unverified.json()["warnings"])

    # 6. Verify collateral and clear encumbrance -> READY!
    client.patch(
        f"/studies/{study_id}/collateral/{col['id']}",
        headers=headers,
        json={"verification_status": "VERIFIED", "verified_value": 4000000, "encumbrance_status": "UNENCUMBERED"},
    )
    r_ready = client.get(f"/studies/{study_id}/funding-readiness/", headers=headers)
    assert r_ready.status_code == 200
    body_ready = r_ready.json()
    assert body_ready["status"] == STATUS_READY
    assert len(body_ready["blocking_factors"]) == 0
    assert len(body_ready["warnings"]) == 0
    assert len(body_ready["positive_factors"]) > 0


def test_api_readiness_ownership_isolation():
    owner = _headers("readiness_owner")
    other = _headers("readiness_other")
    proj, study = _study(owner)
    study_id = study["id"]

    # Owner can access
    assert client.get(f"/studies/{study_id}/funding-readiness/", headers=owner).status_code == 200

    # Other user is forbidden
    assert client.get(f"/studies/{study_id}/funding-readiness/", headers=other).status_code == 403


def test_api_recalculates_on_owner_contribution_change():
    headers = _headers("readiness_recalc_owner")
    proj, study = _study(headers, investment=3000000)
    study_id = study["id"]
    _set_period(headers, study_id, "FY2025")
    _add_collateral(headers, study_id, verification_status="VERIFIED", verified_value=4000000, encumbrance_status="UNENCUMBERED")

    # Before owner contribution: NEEDS_INFORMATION
    r1 = client.get(f"/studies/{study_id}/funding-readiness/", headers=headers).json()
    assert r1["status"] == STATUS_NEEDS_INFO

    # Add owner contribution: becomes READY
    _set_assumption(headers, study_id, "owner_contribution", 750000)
    r2 = client.get(f"/studies/{study_id}/funding-readiness/", headers=headers).json()
    assert r2["status"] == STATUS_READY


def test_api_recalculates_on_collateral_verification_change():
    headers = _headers("readiness_recalc_col")
    proj, study = _study(headers, investment=3000000)
    study_id = study["id"]
    _set_assumption(headers, study_id, "owner_contribution", 750000)
    _set_period(headers, study_id, "FY2025")

    # Unverified collateral: PARTIALLY_READY
    col = _add_collateral(headers, study_id, reported_value=4000000, verified_value=None, verification_status="USER_REPORTED", encumbrance_status="UNENCUMBERED")
    r1 = client.get(f"/studies/{study_id}/funding-readiness/", headers=headers).json()
    assert r1["status"] == STATUS_PARTIALLY_READY

    # Update to VERIFIED: READY
    client.patch(
        f"/studies/{study_id}/collateral/{col['id']}",
        headers=headers,
        json={"verification_status": "VERIFIED", "verified_value": 4000000},
    )
    r2 = client.get(f"/studies/{study_id}/funding-readiness/", headers=headers).json()
    assert r2["status"] == STATUS_READY
