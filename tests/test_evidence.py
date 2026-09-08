"""Evidence layer: provenance, authority classification, and ownership."""
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
    study = client.post(
        "/feasibility/",
        headers=headers,
        json={"project_id": project["id"], "title": "دراسة حضانة", "industry": "education", "investment": 500000},
    ).json()
    return study


def test_evidence_authority_level_is_server_computed_from_official_domain():
    headers = _headers("evidence_official")
    study = _study(headers)
    resp = client.post(
        f"/studies/{study['id']}/evidence",
        headers=headers,
        json={
            "source_type": "official_statistic",
            "title": "Riyadh childcare demand",
            "claim": "GASTAT reports X nurseries in Riyadh",
            "source_url": "https://www.stats.gov.sa/en/some-report",
            "value_number": 120,
            "unit": "count",
            "verification_status": "verified",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["authority_level"] == "OFFICIAL_PRIMARY"
    assert body["verification_status"] == "verified"


def test_evidence_client_cannot_self_certify_authority_level():
    headers = _headers("evidence_spoof")
    study = _study(headers)
    resp = client.post(
        f"/studies/{study['id']}/evidence",
        headers=headers,
        json={
            "source_type": "news",
            "title": "Unverified market claim",
            "claim": "Some blog says demand is high",
            "source_url": "https://random-blog.example.com/post",
        },
    )
    assert resp.status_code == 201, resp.text
    # source_type/authority_level are never accepted from the client payload;
    # only fields the schema defines can influence it, and this URL matches
    # no registry entry.
    assert resp.json()["authority_level"] == "COMMERCIAL_SOURCE"


def test_ai_inference_evidence_can_never_be_verified():
    headers = _headers("evidence_ai")
    study = _study(headers)
    resp = client.post(
        f"/studies/{study['id']}/evidence",
        headers=headers,
        json={
            "source_type": "ai_inference",
            "title": "AI market estimate",
            "claim": "Model estimates 8% growth",
            "verification_status": "verified",
        },
    )
    assert resp.status_code == 422, resp.text


def test_verified_status_requires_source_url():
    headers = _headers("evidence_nourl")
    study = _study(headers)
    resp = client.post(
        f"/studies/{study['id']}/evidence",
        headers=headers,
        json={
            "source_type": "official_statistic",
            "title": "Claim without a source",
            "claim": "Numbers without a link",
            "verification_status": "verified",
        },
    )
    assert resp.status_code == 422, resp.text


def test_evidence_ownership_isolation():
    owner = _headers("evidence_owner")
    other = _headers("evidence_other")
    study = _study(owner)
    created = client.post(
        f"/studies/{study['id']}/evidence",
        headers=owner,
        json={"source_type": "user_document", "title": "Lease", "claim": "Rent is 25,000 SAR/month"},
    ).json()

    assert client.get(f"/studies/{study['id']}/evidence", headers=other).status_code == 403
    assert client.get(f"/studies/{study['id']}/evidence/{created['id']}", headers=other).status_code == 403
    assert client.patch(
        f"/studies/{study['id']}/evidence/{created['id']}", headers=other, json={"title": "hijacked"}
    ).status_code == 403
    assert client.delete(f"/studies/{study['id']}/evidence/{created['id']}", headers=other).status_code == 403


def test_evidence_cannot_be_deleted_while_referenced_by_active_assumption():
    headers = _headers("evidence_ref")
    study = _study(headers)
    evidence = client.post(
        f"/studies/{study['id']}/evidence",
        headers=headers,
        json={"source_type": "user_document", "title": "Lease", "claim": "Rent is 25,000 SAR/month", "value_number": 25000, "unit": "SAR"},
    ).json()
    client.post(
        f"/studies/{study['id']}/assumptions/",
        headers=headers,
        json={
            "key": "monthly_rent",
            "label_en": "Monthly rent",
            "label_ar": "الإيجار الشهري",
            "value_number": 25000,
            "unit": "SAR",
            "origin": "EVIDENCE_DERIVED",
            "evidence_id": evidence["id"],
        },
    )
    resp = client.delete(f"/studies/{study['id']}/evidence/{evidence['id']}", headers=headers)
    assert resp.status_code == 409, resp.text


def test_source_registry_endpoint():
    headers = _headers("evidence_registry")
    resp = client.get("/sources/registry", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "OFFICIAL_PRIMARY" in body["authority_levels"]
    keys = {row["key"] for row in body["sources"]}
    assert "gastat" in keys
    assert "monshaat" in keys
