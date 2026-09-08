"""Company financial profile: per-period upsert, no invented data, ownership."""
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
        "/projects/", headers=headers, json={"name": "شركة قائمة", "industry": "retail", "investment": 3000000}
    ).json()
    return client.post(
        "/feasibility/",
        headers=headers,
        json={"project_id": project["id"], "title": "توسع الشركة", "industry": "retail", "investment": 3000000},
    ).json()


def test_missing_metrics_stay_null_not_zero():
    headers = _headers("cfp_missing")
    study = _study(headers)
    resp = client.put(
        f"/studies/{study['id']}/financial-periods/FY2025",
        headers=headers,
        json={"revenue": 12500000, "source": "financial_statement"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["revenue"] == 12500000
    assert body["ebitda"] is None
    assert body["existing_debt"] is None


def test_put_partially_updates_existing_period_without_clobbering():
    headers = _headers("cfp_partial")
    study = _study(headers)
    client.put(
        f"/studies/{study['id']}/financial-periods/FY2025",
        headers=headers,
        json={"revenue": 12500000, "ebitda": 2500000, "source": "financial_statement"},
    )
    updated = client.put(
        f"/studies/{study['id']}/financial-periods/FY2025",
        headers=headers,
        json={"existing_debt": 1200000},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["revenue"] == 12500000
    assert body["ebitda"] == 2500000
    assert body["existing_debt"] == 1200000


def test_multiple_periods_are_independent():
    headers = _headers("cfp_periods")
    study = _study(headers)
    client.put(f"/studies/{study['id']}/financial-periods/FY2024", headers=headers, json={"revenue": 10000000})
    client.put(f"/studies/{study['id']}/financial-periods/FY2025", headers=headers, json={"revenue": 12500000})
    listed = client.get(f"/studies/{study['id']}/financial-periods/", headers=headers).json()
    assert [row["period"] for row in listed] == ["FY2024", "FY2025"]
    assert [row["revenue"] for row in listed] == [10000000, 12500000]


def test_invalid_source_rejected():
    headers = _headers("cfp_source")
    study = _study(headers)
    resp = client.put(
        f"/studies/{study['id']}/financial-periods/FY2025",
        headers=headers,
        json={"revenue": 1, "source": "definitely_verified"},
    )
    assert resp.status_code == 422, resp.text


def test_document_id_must_belong_to_same_study():
    headers = _headers("cfp_doc")
    study = _study(headers)
    resp = client.put(
        f"/studies/{study['id']}/financial-periods/FY2025",
        headers=headers,
        json={"revenue": 1, "document_id": 999999},
    )
    assert resp.status_code == 422, resp.text


def test_company_financial_profile_ownership_isolation():
    owner = _headers("cfp_owner")
    other = _headers("cfp_other")
    study = _study(owner)
    client.put(f"/studies/{study['id']}/financial-periods/FY2025", headers=owner, json={"revenue": 1})

    assert client.get(f"/studies/{study['id']}/financial-periods/", headers=other).status_code == 403
    assert client.get(f"/studies/{study['id']}/financial-periods/FY2025", headers=other).status_code == 403
    assert client.put(f"/studies/{study['id']}/financial-periods/FY2025", headers=other, json={"revenue": 999}).status_code == 403
