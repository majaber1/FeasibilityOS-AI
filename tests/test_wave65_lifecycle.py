"""Wave 6.5 — ten realistic project lifecycles plus UX safety regressions.

Every dataset value is a USER_ASSUMPTION. Missing market facts stay UNKNOWN /
NOT_AVAILABLE / INSUFFICIENT_DATA. Validation GO still requires real evidence.
"""
from __future__ import annotations

import os
import tempfile
import uuid

import pytest

if not os.environ.get("DATABASE_URL"):
    _TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _TMP.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + _TMP.name
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-characters-long")

from fastapi.testclient import TestClient

from app import db as app_db
from app.main import app

client = TestClient(app)
PASSWORD = "Sup3rSecretPassword123!"

PROJECTS = [
    {"name": "Saudi Scrap AI Marketplace", "industry": "technology", "investment": 850000, "stage": "idea", "activity": "AI marketplace + recycling brokerage"},
    {"name": "Smart Clinic SaaS", "industry": "healthcare", "investment": 420000, "stage": "mvp", "activity": "B2B clinic SaaS subscriptions"},
    {"name": "Plastic Recycling Factory", "industry": "industrial", "investment": 12500000, "stage": "idea", "activity": "High-CAPEX recycling plant"},
    {"name": "Food Waste Marketplace", "industry": "food", "investment": 310000, "stage": "idea", "activity": "Restaurant surplus marketplace"},
    {"name": "Smart Maintenance Platform", "industry": "technology", "investment": 540000, "stage": "mvp", "activity": "Technician booking marketplace"},
    {"name": "Online Training Platform", "industry": "education", "investment": 280000, "stage": "idea", "activity": "EdTech courses and subscriptions"},
    {"name": "Specialized E-commerce Store", "industry": "retail", "investment": 190000, "stage": "idea", "activity": "Inventory-led specialty retail"},
    {"name": "Smart Agriculture Project", "industry": "industrial", "investment": 2100000, "stage": "idea", "activity": "AgriTech equipment and seasonal cycles"},
    {"name": "AI Document Automation SaaS", "industry": "technology", "investment": 670000, "stage": "mvp", "activity": "Enterprise document processing"},
    {"name": "Logistics Optimization Platform", "industry": "technology", "investment": 930000, "stage": "idea", "activity": "Fleet route-optimization SaaS"},
]


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    assert app_db.DB_ENABLED is True
    app_db.init_db()


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def _register(prefix: str):
    email = f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": PASSWORD, "full_name": "Wave 65 Founder"})
    assert r.status_code == 201, r.text
    tok = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return tok


def _assumption(headers, study_id: int, key: str, value: float, label_en: str, label_ar: str):
    r = client.post(
        f"/studies/{study_id}/assumptions/",
        headers=headers,
        json={
            "key": key,
            "label_en": label_en,
            "label_ar": label_ar,
            "value_number": value,
            "unit": "SAR",
            "origin": "USER",
            "reason": "USER_ASSUMPTION entered by founder for planning; not a market fact",
            "confidence": "medium",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["origin"] == "USER"
    return body


def _support_critical_hypotheses(headers, study_id: int):
    val = client.get(f"/api/v1/validation/study/{study_id}", headers=headers)
    assert val.status_code == 200, val.text
    ws = val.json()
    for hypo in ws["hypotheses"]:
        if hypo.get("importance") != "CRITICAL":
            continue
        ev = client.post(
            f"/api/v1/validation/workspaces/{ws['id']}/evidence",
            headers=headers,
            json={
                "evidence_type": "CUSTOMER_INTERVIEW",
                "title": f"Founder-recorded interview for hypothesis {hypo['id']}",
                "hypothesis_id": hypo["id"],
                "evidence_strength": "STRONG",
                "evidence_direction": "SUPPORTING",
                "is_simulated": False,
                "structured_payload": {"role": "prospective buyer", "quote": "User-recorded interview note, not a market census."},
            },
        )
        assert ev.status_code == 201, ev.text
    return ws["id"]


def _run_lifecycle(headers, spec: dict):
    created = client.post(
        "/projects/",
        headers=headers,
        json={"name": spec["name"], "industry": spec["industry"], "investment": spec["investment"], "stage": spec["stage"]},
    )
    assert created.status_code == 201, created.text
    project = created.json()
    pid = project["id"]

    renamed = client.patch(
        f"/projects/{pid}",
        headers=headers,
        json={"name": spec["name"] + " — v2", "investment": spec["investment"] + 1000, "stage": spec["stage"]},
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"].endswith("— v2")

    first = client.post(
        "/feasibility/",
        headers=headers,
        json={"project_id": pid, "title": spec["name"], "industry": spec["industry"], "investment": spec["investment"]},
    )
    assert first.status_code == 201, first.text
    study = first.json()
    sid = study["id"]

    second = client.post(
        "/feasibility/",
        headers=headers,
        json={"project_id": pid, "title": spec["name"] + " duplicate", "industry": spec["industry"], "investment": spec["investment"]},
    )
    assert second.status_code == 201, second.text
    assert second.json()["id"] == sid
    listing = client.get(f"/feasibility/?project_id={pid}", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    profile = client.put(
        f"/studies/{sid}/business-profile/",
        headers=headers,
        json={"business_activity": spec["activity"], "city": "Riyadh", "region": "Riyadh", "customer_segment": "USER_ASSUMPTION target segment"},
    )
    assert profile.status_code in (200, 201), profile.text

    missing = client.post(f"/feasibility/{sid}/compute-from-assumptions", headers=headers)
    assert missing.status_code == 422, missing.text
    assert "capex" in missing.text or "missing" in missing.text.lower()

    _assumption(headers, sid, "capex", spec["investment"], "CAPEX", "النفقات الرأسمالية")
    _assumption(headers, sid, "revenue_year1", max(spec["investment"] * 0.35, 50000), "Year-1 revenue", "إيراد السنة الأولى")

    computed = client.post(f"/feasibility/{sid}/compute-from-assumptions", headers=headers)
    assert computed.status_code == 200, computed.text
    result = computed.json()["result"]
    assert result is not None
    assert "npv" in result and "roi_percent" in result
    assert result.get("verdict") in {"feasible", "borderline", "not_feasible"}

    health = client.get(f"/studies/{sid}/financial-health/", headers=headers)
    assert health.status_code == 200, health.text
    assert health.json()["data_status"] == "NO_PERIODS_RECORDED"

    capacity = client.get(f"/studies/{sid}/borrowing-capacity/", headers=headers)
    assert capacity.status_code == 200, capacity.text
    assert capacity.json()["status"] == "INSUFFICIENT_DATA"

    blocked_launch = client.get(f"/api/v1/launch/study/{sid}", headers=headers)
    assert blocked_launch.status_code == 422

    ws_id = _support_critical_hypotheses(headers, sid)
    go = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/decision",
        headers=headers,
        json={"decision": "GO", "decision_reason": "Field interviews support the critical hypotheses; remaining TAM figures stay UNKNOWN."},
    )
    assert go.status_code == 201, go.text
    history = client.get(f"/api/v1/validation/study/{sid}", headers=headers).json()
    assert history.get("latest_decision", {}).get("id") == go.json()["id"]

    launch = client.get(f"/api/v1/launch/study/{sid}", headers=headers)
    assert launch.status_code == 200, launch.text
    launch_id = launch.json()["id"]
    task = client.post(
        f"/api/v1/launch/workspaces/{launch_id}/tasks",
        headers=headers,
        json={"title": "Open CR and municipal file", "is_critical": True},
    )
    assert task.status_code == 201, task.text
    status = client.patch(
        f"/api/v1/launch/workspaces/{launch_id}/status",
        headers=headers,
        json={"status": "IN_PROGRESS"},
    )
    assert status.status_code == 200, status.text
    relaunch = client.get(f"/api/v1/launch/study/{sid}", headers=headers)
    assert any(t["title"] == "Open CR and municipal file" for t in relaunch.json()["tasks"])
    assert relaunch.json()["status"] == "IN_PROGRESS"

    growth = client.get(f"/api/v1/growth/study/{sid}", headers=headers)
    assert growth.status_code == 200, growth.text
    health_state = growth.json()["business_health"]["health_state"]
    assert health_state == "INSUFFICIENT_DATA"
    scale = client.post(
        f"/api/v1/growth/workspaces/{growth.json()['workspace']['id']}/decisions",
        headers=headers,
        json={"decision": "SCALE", "decision_reason": "Should be rejected without complete actuals."},
    )
    assert scale.status_code in (400, 422)
    hold = client.post(
        f"/api/v1/growth/workspaces/{growth.json()['workspace']['id']}/decisions",
        headers=headers,
        json={"decision": "HOLD", "decision_reason": "Hold until actual operating periods are recorded. Missing data is not failure."},
    )
    assert hold.status_code == 201, hold.text
    growth_again = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()
    assert any(d["decision"] == "HOLD" for d in growth_again["decisions"])

    persisted = client.get(f"/feasibility/{sid}", headers=headers)
    assert persisted.status_code == 200
    assert persisted.json()["result"] is not None
    assert client.get(f"/projects/{pid}", headers=headers).json()["name"].endswith("— v2")
    return pid, sid


def test_wave65_ten_projects_full_lifecycle():
    tok = _register("wave65")
    headers = _auth(tok)
    ids = []
    for spec in PROJECTS:
        ids.append(_run_lifecycle(headers, spec))
    assert len(ids) == 10
    projects = client.get("/projects/", headers=headers)
    assert projects.status_code == 200
    names = {row["name"] for row in projects.json()}
    for spec in PROJECTS:
        assert any(spec["name"] in name for name in names)


def test_wave65_new_study_does_not_duplicate_existing_study():
    tok = _register("nodup")
    headers = _auth(tok)
    project = client.post("/projects/", headers=headers, json=PROJECTS[0]).json()
    a = client.post("/feasibility/", headers=headers, json={"project_id": project["id"], "title": "A", "industry": "technology", "investment": 100000})
    b = client.post("/feasibility/", headers=headers, json={"project_id": project["id"], "title": "B", "industry": "technology", "investment": 100000})
    assert a.json()["id"] == b.json()["id"]
    listed = client.get(f"/feasibility/?project_id={project['id']}", headers=headers).json()
    assert len(listed) == 1


def test_wave65_go_without_evidence_is_blocked():
    tok = _register("noev")
    headers = _auth(tok)
    project = client.post("/projects/", headers=headers, json=PROJECTS[1]).json()
    study = client.post("/feasibility/", headers=headers, json={"project_id": project["id"], "title": PROJECTS[1]["name"], "industry": "healthcare", "investment": 420000}).json()
    ws = client.get(f"/api/v1/validation/study/{study['id']}", headers=headers).json()
    r = client.post(
        f"/api/v1/validation/workspaces/{ws['id']}/decision",
        headers=headers,
        json={"decision": "GO", "decision_reason": "No field evidence recorded"},
    )
    assert r.status_code in (400, 422)
