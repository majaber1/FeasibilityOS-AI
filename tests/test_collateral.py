"""Collateral: types, verification/encumbrance validation, summary, ownership."""
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
from app.services.collateral import summarize_collateral, validate_consistency  # noqa: E402

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


def _create(headers, study_id, **overrides):
    payload = {"collateral_type": "PROPERTY", "description": "Riyadh warehouse", "reported_value": 4000000}
    payload.update(overrides)
    return client.post(f"/studies/{study_id}/collateral/", headers=headers, json=payload)


# --- Pure function unit tests -------------------------------------------------

def test_negative_reported_value_rejected():
    with pytest.raises(ValueError):
        validate_consistency({
            "collateral_type": "CASH", "reported_value": -100, "verified_value": None,
            "verification_status": "USER_REPORTED", "encumbrance_status": "UNKNOWN", "encumbrance_amount": None,
        })


def test_zero_reported_value_is_legitimate():
    validate_consistency({
        "collateral_type": "CASH", "reported_value": 0, "verified_value": None,
        "verification_status": "USER_REPORTED", "encumbrance_status": "UNKNOWN", "encumbrance_amount": None,
    })  # must not raise


def test_verified_value_requires_appropriate_status():
    with pytest.raises(ValueError):
        validate_consistency({
            "collateral_type": "PROPERTY", "reported_value": 4000000, "verified_value": 3800000,
            "verification_status": "USER_REPORTED", "encumbrance_status": "UNKNOWN", "encumbrance_amount": None,
        })


def test_encumbrance_amount_required_when_encumbered():
    with pytest.raises(ValueError):
        validate_consistency({
            "collateral_type": "PROPERTY", "reported_value": 4000000, "verified_value": None,
            "verification_status": "USER_REPORTED", "encumbrance_status": "PARTIALLY_ENCUMBERED", "encumbrance_amount": None,
        })


def test_encumbrance_amount_forbidden_when_not_encumbered():
    with pytest.raises(ValueError):
        validate_consistency({
            "collateral_type": "PROPERTY", "reported_value": 4000000, "verified_value": None,
            "verification_status": "USER_REPORTED", "encumbrance_status": "UNENCUMBERED", "encumbrance_amount": 100000,
        })


def test_encumbrance_amount_cannot_exceed_value():
    with pytest.raises(ValueError):
        validate_consistency({
            "collateral_type": "PROPERTY", "reported_value": 4000000, "verified_value": None,
            "verification_status": "USER_REPORTED", "encumbrance_status": "FULLY_ENCUMBERED", "encumbrance_amount": 5000000,
        })


def test_summary_matches_golden_fixture_before_verification():
    records = [
        {"reported_value": 4000000, "verified_value": None, "verification_status": "USER_REPORTED", "encumbrance_status": "UNKNOWN", "encumbrance_amount": None},
        {"reported_value": 2000000, "verified_value": None, "verification_status": "USER_REPORTED", "encumbrance_status": "UNKNOWN", "encumbrance_amount": None},
    ]
    summary = summarize_collateral(records)
    assert summary["total_reported_value"] == 6000000
    assert summary["total_verified_value"] == 0  # nothing VERIFIED yet -- never inferred from reported_value
    assert summary["total_encumbered_value"] == 0
    assert summary["total_unencumbered_reported_value"] == 6000000


def test_summary_worked_example_from_spec():
    records = [
        {"reported_value": 4000000, "verified_value": 4000000, "verification_status": "VERIFIED", "encumbrance_status": "PARTIALLY_ENCUMBERED", "encumbrance_amount": 1000000},
        {"reported_value": 2000000, "verified_value": None, "verification_status": "USER_REPORTED", "encumbrance_status": "UNKNOWN", "encumbrance_amount": None},
    ]
    summary = summarize_collateral(records)
    assert summary["total_reported_value"] == 6000000
    assert summary["total_verified_value"] == 4000000
    assert summary["total_encumbered_value"] == 1000000
    assert summary["total_unencumbered_reported_value"] == 5000000


def test_summary_is_deterministic_repeatable():
    records = [{"reported_value": 1000, "verified_value": None, "verification_status": "UNVERIFIED", "encumbrance_status": "UNKNOWN", "encumbrance_amount": None}]
    assert summarize_collateral(records) == summarize_collateral(records)


# --- API-level tests -----------------------------------------------------------

def test_create_property_equipment_cash():
    headers = _headers("collateral_types")
    study = _study(headers)
    assert _create(headers, study["id"], collateral_type="PROPERTY", description="Warehouse", reported_value=4000000).status_code == 201
    assert _create(headers, study["id"], collateral_type="EQUIPMENT", description="Machinery", reported_value=2000000).status_code == 201
    assert _create(headers, study["id"], collateral_type="CASH", description="Term deposit", reported_value=500000).status_code == 201


def test_negative_value_rejected_via_api():
    headers = _headers("collateral_neg")
    study = _study(headers)
    resp = _create(headers, study["id"], reported_value=-1)
    assert resp.status_code == 422


def test_zero_value_accepted_via_api():
    headers = _headers("collateral_zero")
    study = _study(headers)
    resp = _create(headers, study["id"], reported_value=0)
    assert resp.status_code == 201, resp.text


def test_verified_vs_unverified_via_api():
    headers = _headers("collateral_verify")
    study = _study(headers)
    verified = _create(
        headers, study["id"], reported_value=4000000, verified_value=3900000, verification_status="VERIFIED",
    )
    assert verified.status_code == 201, verified.text
    unverified = _create(headers, study["id"], reported_value=2000000, verification_status="UNVERIFIED")
    assert unverified.status_code == 201, unverified.text


def test_encumbered_partially_encumbered_unknown_via_api():
    headers = _headers("collateral_encumbrance")
    study = _study(headers)
    full = _create(headers, study["id"], encumbrance_status="FULLY_ENCUMBERED", encumbrance_amount=4000000)
    assert full.status_code == 201, full.text
    partial = _create(headers, study["id"], encumbrance_status="PARTIALLY_ENCUMBERED", encumbrance_amount=1000000)
    assert partial.status_code == 201, partial.text
    unknown = _create(headers, study["id"], encumbrance_status="UNKNOWN")
    assert unknown.status_code == 201, unknown.text


def test_summary_totals_via_api_match_golden_fixture():
    headers = _headers("collateral_summary_api")
    study = _study(headers)
    _create(headers, study["id"], collateral_type="PROPERTY", description="Warehouse", reported_value=4000000)
    _create(headers, study["id"], collateral_type="EQUIPMENT", description="Machinery", reported_value=2000000)

    summary = client.get(f"/studies/{study['id']}/collateral/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["record_count"] == 2
    assert body["total_reported_value"] == 6000000
    assert body["total_verified_value"] == 0


def test_edit_record():
    headers = _headers("collateral_edit")
    study = _study(headers)
    created = _create(headers, study["id"], reported_value=2000000).json()
    updated = client.patch(
        f"/studies/{study['id']}/collateral/{created['id']}", headers=headers,
        json={"reported_value": 2200000, "description": "Updated machinery valuation"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["reported_value"] == 2200000
    assert updated.json()["description"] == "Updated machinery valuation"


def test_edit_record_still_enforces_consistency_against_merged_state():
    headers = _headers("collateral_edit_invalid")
    study = _study(headers)
    created = _create(headers, study["id"], reported_value=2000000).json()
    # Setting only encumbrance_status without an amount must fail even though
    # the create request never touched encumbrance_amount.
    resp = client.patch(
        f"/studies/{study['id']}/collateral/{created['id']}", headers=headers,
        json={"encumbrance_status": "FULLY_ENCUMBERED"},
    )
    assert resp.status_code == 422, resp.text


def test_delete_record():
    headers = _headers("collateral_delete")
    study = _study(headers)
    created = _create(headers, study["id"]).json()
    resp = client.delete(f"/studies/{study['id']}/collateral/{created['id']}", headers=headers)
    assert resp.status_code == 204
    assert client.get(f"/studies/{study['id']}/collateral/{created['id']}", headers=headers).status_code == 404


def test_persistence_through_reload():
    headers = _headers("collateral_persist")
    study = _study(headers)
    created = _create(headers, study["id"], reported_value=4000000).json()
    reloaded = client.get(f"/studies/{study['id']}/collateral/{created['id']}", headers=headers)
    assert reloaded.status_code == 200
    assert reloaded.json()["reported_value"] == 4000000
    listed = client.get(f"/studies/{study['id']}/collateral/", headers=headers).json()
    assert any(row["id"] == created["id"] for row in listed)


def test_collateral_ownership_isolation():
    owner = _headers("collateral_owner")
    other = _headers("collateral_other")
    study = _study(owner)
    created = _create(owner, study["id"]).json()

    assert client.get(f"/studies/{study['id']}/collateral/", headers=other).status_code == 403
    assert client.get(f"/studies/{study['id']}/collateral/{created['id']}", headers=other).status_code == 403
    assert client.get(f"/studies/{study['id']}/collateral/summary", headers=other).status_code == 403
    assert _create(other, study["id"]).status_code == 403
    assert client.patch(
        f"/studies/{study['id']}/collateral/{created['id']}", headers=other, json={"reported_value": 1}
    ).status_code == 403
    assert client.delete(f"/studies/{study['id']}/collateral/{created['id']}", headers=other).status_code == 403
