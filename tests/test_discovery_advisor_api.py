"""API-level Discovery Advisor: AI estimate + persistence (no browser)."""
from __future__ import annotations

import os
import sys
import tempfile
import uuid
from pathlib import Path

if not os.environ.get("DATABASE_URL"):
    _TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _TMP.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + _TMP.name

_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _ROOT / "backend"
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_BACKEND))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import db as app_db  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
PASSWORD = "DiscoveryAdvisor1!"


def setup_module(module):
    assert app_db.DB_ENABLED is True
    app_db.init_db()
    from app.api.v2.study_engine import StudyStateRow, StudyVersionRow  # noqa: F401

    app_db.Base.metadata.create_all(bind=app_db.engine)


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _register_and_login(prefix: str = "discovery") -> dict:
    email = f"{prefix}_{_uid()}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    tok = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {tok}"}


def test_ai_estimate_persists_and_advances():
    headers = _register_and_login("da_api")
    proj = client.post(
        "/projects/",
        json={
            "name": "SaaS Discovery Advisor",
            "industry": "technology",
            "investment": 1000000,
            "stage": "idea",
        },
        headers=headers,
    )
    assert proj.status_code < 400, proj.text
    project_id = str(proj.json()["id"])

    study = client.post(
        "/api/v2/studies",
        json={
            "project_id": project_id,
            "language": "en",
            "description": "B2B SaaS CRM subscription ARR CAC churn for Saudi SMBs",
        },
        headers=headers,
    )
    assert study.status_code < 400, study.text
    study_id = study.json().get("study_id") or study.json().get("id")

    arch = client.post(
        f"/api/v2/studies/{study_id}/archetype",
        json={"archetype": "saas_digital", "approved": True},
        headers=headers,
    )
    assert arch.status_code < 400, arch.text
    data = arch.json()
    assert data.get("phase") == "NEEDS_INFORMATION"
    qs = data.get("discovery_questions") or []
    assert qs, "expected discovery interview questions"
    assert all("category" in q and "explanation" in q and "allow_ai_estimate" in q for q in qs)
    assert all(q.get("answer_type") for q in qs)

    estimate_ids = [q["id"] for q in qs if q.get("required", True)]
    submit = client.post(
        f"/api/v2/studies/{study_id}/structured-answers",
        json={"answers": {}, "ai_estimates": estimate_ids, "mark_answered": True},
        headers=headers,
    )
    assert submit.status_code < 400, submit.text
    submitted = submit.json()
    assert submitted.get("phase") != "NEEDS_INFORMATION"
    dq = submitted.get("discovery_questions") or []
    assert any(q.get("ai_estimated") for q in dq), "expected ai_estimated flags"

    again = client.get(f"/api/v2/studies/{study_id}", headers=headers)
    assert again.status_code < 400, again.text
    reloaded = again.json()
    dq2 = reloaded.get("discovery_questions") or []
    assert any(q.get("ai_estimated") for q in dq2)
    assert reloaded.get("phase") != "NEEDS_INFORMATION"
