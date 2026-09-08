"""Quick Idea Check: deterministic classification, persistence, ownership."""
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
from app.services.quick_idea_check import classify_industry, classify_status  # noqa: E402

client = TestClient(app)


def setup_module(module):
    app_db.init_db()


def _headers(prefix: str):
    email = f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    password = "Sup3rSecret!"
    assert client.post("/auth/register", json={"email": email, "password": password}).status_code == 201
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_classify_industry_matches_arabic_and_english_keywords():
    assert classify_industry("أنا أفكر بمشروع حضانة أطفال في الرياض") == "education"
    assert classify_industry("I want to open a nursery in Jeddah") == "education"
    assert classify_industry("مطعم صغير في جدة") == "food"
    assert classify_industry("قطعة أرض فارغة") is None


def test_classify_status_is_deterministic_not_a_fake_score():
    assert classify_status(["city"], evidence_count=0, assumption_count=0) == "INSUFFICIENT_DATA"
    assert classify_status([], evidence_count=0, assumption_count=0) == "HIGH_UNCERTAINTY"
    assert classify_status([], evidence_count=1, assumption_count=0) == "NEEDS_VALIDATION"
    assert classify_status([], evidence_count=1, assumption_count=1) == "PROMISING"


def test_golden_journey_nursery_idea_creates_project_and_study():
    headers = _headers("quick_check_nursery")
    resp = client.post(
        "/quick-idea-check/",
        headers=headers,
        json={
            "idea_text": "أنا أفكر بمشروع حضانة أطفال في الرياض",
            "estimated_capital": 500000,
            "city": "Riyadh",
            "customer_segment": "working parents",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["industry_guess"] == "education"
    assert body["regulatory_complexity_hint"] == "higher"
    assert body["missing_fields"] == []
    # brand new study: no evidence yet -> HIGH_UNCERTAINTY, never a fake percent score.
    assert body["status"] == "HIGH_UNCERTAINTY"
    assert body["evidence_coverage"] == 0

    project = client.get(f"/projects/{body['project_id']}", headers=headers)
    assert project.status_code == 200
    assert project.json()["investment"] == 500000

    study = client.get(f"/feasibility/{body['study_id']}", headers=headers)
    assert study.status_code == 200
    assert study.json()["payload"]["quick_idea_check"]["idea_text"] == "أنا أفكر بمشروع حضانة أطفال في الرياض"


def test_missing_fields_forces_insufficient_data_regardless_of_evidence():
    headers = _headers("quick_check_missing")
    resp = client.post(
        "/quick-idea-check/",
        headers=headers,
        json={"idea_text": "مشروع تقني جديد", "estimated_capital": 100000},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "INSUFFICIENT_DATA"
    assert "city" in body["missing_fields"]
    assert "customer_segment" in body["missing_fields"]


def test_reposting_same_project_id_does_not_duplicate_study():
    headers = _headers("quick_check_idempotent")
    first = client.post(
        "/quick-idea-check/",
        headers=headers,
        json={"idea_text": "متجر إلكتروني", "estimated_capital": 200000, "city": "Jeddah", "customer_segment": "retail shoppers"},
    ).json()
    second = client.post(
        "/quick-idea-check/",
        headers=headers,
        json={
            "idea_text": "متجر إلكتروني محدث",
            "estimated_capital": 250000,
            "city": "Jeddah",
            "customer_segment": "retail shoppers",
            "project_id": first["project_id"],
        },
    )
    assert second.status_code == 201, second.text
    assert second.json()["study_id"] == first["study_id"]
    listing = client.get(f"/feasibility/?project_id={first['project_id']}", headers=headers)
    assert len(listing.json()) == 1


def test_check_evolves_as_evidence_and_assumptions_are_added():
    headers = _headers("quick_check_evolve")
    created = client.post(
        "/quick-idea-check/",
        headers=headers,
        json={"idea_text": "عيادة أسنان في الدمام", "estimated_capital": 300000, "city": "Dammam", "customer_segment": "families"},
    ).json()
    assert created["status"] == "HIGH_UNCERTAINTY"

    study_id = created["study_id"]
    evidence = client.post(
        f"/studies/{study_id}/evidence",
        headers=headers,
        json={"source_type": "user_document", "title": "Lease", "claim": "Rent quote received"},
    ).json()
    after_evidence = client.get(f"/quick-idea-check/{study_id}", headers=headers)
    assert after_evidence.status_code == 200
    assert after_evidence.json()["status"] == "NEEDS_VALIDATION"
    assert after_evidence.json()["evidence_coverage"] == 1

    client.post(
        f"/studies/{study_id}/assumptions/",
        headers=headers,
        json={
            "key": "monthly_rent", "label_en": "Monthly rent", "label_ar": "الإيجار الشهري",
            "value_number": 10000, "unit": "SAR", "origin": "EVIDENCE_DERIVED", "evidence_id": evidence["id"],
        },
    )
    after_assumption = client.get(f"/quick-idea-check/{study_id}", headers=headers)
    assert after_assumption.json()["status"] == "PROMISING"


def test_quick_idea_check_ownership_isolation():
    owner = _headers("quick_check_owner")
    other = _headers("quick_check_other")
    created = client.post(
        "/quick-idea-check/",
        headers=owner,
        json={"idea_text": "فندق صغير", "estimated_capital": 400000, "city": "Abha", "customer_segment": "tourists"},
    ).json()
    assert client.get(f"/quick-idea-check/{created['study_id']}", headers=other).status_code == 403
    assert client.post(
        "/quick-idea-check/", headers=other,
        json={"idea_text": "hijack", "estimated_capital": 1000, "project_id": created["project_id"]},
    ).status_code == 403
