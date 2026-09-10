"""End-to-end workspace tests: full user journey from registration through
study creation, messaging, phase progression, approval gates, and
multi-user isolation.

DB-backed on a throwaway SQLite file. Does NOT call Groq (no AI engine
invocation) — tests cover the API contract, persistence, and state
transitions via direct DB manipulation where needed.
"""
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
PASSWORD = "E2eTest@Pass1!"


def setup_module(module):
    assert app_db.DB_ENABLED is True
    app_db.init_db()
    from app.api.v2.study_engine import StudyStateRow, StudyVersionRow
    app_db.Base.metadata.create_all(bind=app_db.engine)


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _register_and_login(prefix: str = "e2e") -> tuple[dict, str]:
    """Register a new user, login, return (auth_headers, email)."""
    email = f"{prefix}_{_uid()}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    tok = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}, email


# =============================================================================
# 1. Registration → Login → Token flow
# =============================================================================

class TestAuthFlow:
    def test_register_returns_201(self):
        email = f"reg_{_uid()}@example.com"
        r = client.post("/auth/register", json={"email": email, "password": PASSWORD})
        assert r.status_code == 201

    def test_login_returns_token(self):
        headers, email = _register_and_login("login")
        assert "Bearer" in headers["Authorization"]

    def test_duplicate_register_fails(self):
        email = f"dup_{_uid()}@example.com"
        client.post("/auth/register", json={"email": email, "password": PASSWORD})
        r = client.post("/auth/register", json={"email": email, "password": PASSWORD})
        assert r.status_code in (400, 409)

    def test_wrong_password_fails(self):
        email = f"wrong_{_uid()}@example.com"
        client.post("/auth/register", json={"email": email, "password": PASSWORD})
        r = client.post("/auth/login", json={"email": email, "password": "WrongP@ss1!"})
        assert r.status_code == 401

    def test_unregistered_email_fails(self):
        r = client.post("/auth/login", json={"email": f"ghost_{_uid()}@example.com", "password": PASSWORD})
        assert r.status_code == 401


# =============================================================================
# 2. Study creation (workspace entry point)
# =============================================================================

class TestStudyCreation:
    def test_create_study_no_description(self):
        headers, _ = _register_and_login("create")
        r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
            "language": "ar",
        }, headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["study_id"].startswith("study_")
        assert data["phase"] == "DRAFT"

    def test_create_study_with_language_en(self):
        headers, _ = _register_and_login("lang")
        r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
            "language": "en",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["phase"] == "DRAFT"

    def test_create_study_returns_study_id(self):
        headers, _ = _register_and_login("sid")
        r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
        }, headers=headers)
        data = r.json()
        assert "study_id" in data
        assert len(data["study_id"]) > 6

    def test_create_study_unauthenticated_401(self):
        r = client.post("/api/v2/studies", json={
            "project_id": "proj_x",
        })
        assert r.status_code == 401


# =============================================================================
# 3. Study retrieval and listing
# =============================================================================

class TestStudyRetrieval:
    def test_get_study_by_id(self):
        headers, _ = _register_and_login("get")
        create_r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
        }, headers=headers)
        sid = create_r.json()["study_id"]

        r = client.get(f"/api/v2/studies/{sid}", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["study_id"] == sid
        assert data["phase"] == "DRAFT"

    def test_get_study_not_found_404(self):
        headers, _ = _register_and_login("notfound")
        r = client.get("/api/v2/studies/study_nonexistent", headers=headers)
        assert r.status_code == 404

    def test_list_studies_empty(self):
        headers, _ = _register_and_login("empty")
        r = client.get("/api/v2/studies", headers=headers)
        assert r.status_code == 200
        assert r.json()["studies"] == []

    def test_list_studies_shows_created(self):
        headers, _ = _register_and_login("list")
        pid = f"proj_{_uid()}"
        client.post("/api/v2/studies", json={"project_id": pid}, headers=headers)
        client.post("/api/v2/studies", json={"project_id": pid}, headers=headers)

        r = client.get("/api/v2/studies", headers=headers)
        studies = r.json()["studies"]
        assert len(studies) == 2

    def test_list_studies_has_correct_fields(self):
        headers, _ = _register_and_login("fields")
        client.post("/api/v2/studies", json={"project_id": f"proj_{_uid()}"}, headers=headers)

        r = client.get("/api/v2/studies", headers=headers)
        study = r.json()["studies"][0]
        assert "study_id" in study
        assert "phase" in study
        assert "created_at" in study
        assert "updated_at" in study


# =============================================================================
# 4. Workspace messaging
# =============================================================================

class TestWorkspaceMessaging:
    def test_message_to_nonexistent_study_404(self):
        headers, _ = _register_and_login("msg404")
        r = client.post("/api/v2/studies/study_fake/message", json={
            "message": "hello",
        }, headers=headers)
        assert r.status_code == 404

    def test_message_unauthenticated_401(self):
        r = client.post("/api/v2/studies/study_fake/message", json={
            "message": "hello",
        })
        assert r.status_code == 401

    def test_message_requires_body(self):
        headers, _ = _register_and_login("nobody")
        create_r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
        }, headers=headers)
        sid = create_r.json()["study_id"]

        r = client.post(f"/api/v2/studies/{sid}/message", headers=headers)
        assert r.status_code == 422


# =============================================================================
# 5. Phase-blocking / approval gates
# =============================================================================

class TestApprovalGates:
    def test_approve_profile_wrong_phase_400(self):
        headers, _ = _register_and_login("gate1")
        create_r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
        }, headers=headers)
        sid = create_r.json()["study_id"]

        r = client.post(f"/api/v2/studies/{sid}/information-gate", json={
            "choice": "research",
        }, headers=headers)
        assert r.status_code == 400
        assert "phase" in r.json()["detail"].lower() or "DRAFT" in r.json()["detail"]

    def test_approve_evidence_wrong_phase_400(self):
        headers, _ = _register_and_login("gate2")
        create_r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
        }, headers=headers)
        sid = create_r.json()["study_id"]

        r = client.post(f"/api/v2/studies/{sid}/approve/evidence", json={
            "approved": True,
        }, headers=headers)
        assert r.status_code == 400

    def test_approve_assumptions_wrong_phase_400(self):
        headers, _ = _register_and_login("gate3")
        create_r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
        }, headers=headers)
        sid = create_r.json()["study_id"]

        r = client.post(f"/api/v2/studies/{sid}/approve/assumptions", json={
            "approved": True,
        }, headers=headers)
        assert r.status_code == 400

    def test_approve_invalid_stage_400(self):
        headers, _ = _register_and_login("gate4")
        create_r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
        }, headers=headers)
        sid = create_r.json()["study_id"]

        r = client.post(f"/api/v2/studies/{sid}/approve/invalid_stage", json={
            "approved": True,
        }, headers=headers)
        assert r.status_code == 400
        assert "invalid" in r.json()["detail"].lower()

    def test_approve_study_not_found_404(self):
        headers, _ = _register_and_login("gate5")
        r = client.post("/api/v2/studies/study_nonexistent/information-gate", json={
            "choice": "research",
        }, headers=headers)
        assert r.status_code == 404

    def test_approve_unauthenticated_401(self):
        r = client.post("/api/v2/studies/study_x/information-gate", json={
            "choice": "research",
        })
        assert r.status_code == 401


# =============================================================================
# 6. Multi-user isolation
# =============================================================================

class TestUserIsolation:
    def test_user_cannot_see_other_users_study(self):
        headers_a, _ = _register_and_login("isoA")
        headers_b, _ = _register_and_login("isoB")

        create_r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
        }, headers=headers_a)
        sid = create_r.json()["study_id"]

        r = client.get(f"/api/v2/studies/{sid}", headers=headers_b)
        assert r.status_code == 404

    def test_user_cannot_list_other_users_studies(self):
        headers_a, _ = _register_and_login("listA")
        headers_b, _ = _register_and_login("listB")

        client.post("/api/v2/studies", json={"project_id": f"proj_{_uid()}"}, headers=headers_a)
        client.post("/api/v2/studies", json={"project_id": f"proj_{_uid()}"}, headers=headers_a)

        r = client.get("/api/v2/studies", headers=headers_b)
        assert r.json()["studies"] == []

    def test_user_cannot_message_other_users_study(self):
        headers_a, _ = _register_and_login("msgA")
        headers_b, _ = _register_and_login("msgB")

        create_r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
        }, headers=headers_a)
        sid = create_r.json()["study_id"]

        r = client.post(f"/api/v2/studies/{sid}/message", json={
            "message": "hijack attempt",
        }, headers=headers_b)
        assert r.status_code == 404

    def test_user_cannot_approve_other_users_study(self):
        headers_a, _ = _register_and_login("aprA")
        headers_b, _ = _register_and_login("aprB")

        create_r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
        }, headers=headers_a)
        sid = create_r.json()["study_id"]

        r = client.post(f"/api/v2/studies/{sid}/information-gate", json={
            "choice": "research",
        }, headers=headers_b)
        assert r.status_code == 404


# =============================================================================
# 7. Study persistence & state roundtrip
# =============================================================================

class TestPersistence:
    def test_study_survives_re_fetch(self):
        headers, _ = _register_and_login("persist")
        create_r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
        }, headers=headers)
        sid = create_r.json()["study_id"]

        r1 = client.get(f"/api/v2/studies/{sid}", headers=headers)
        r2 = client.get(f"/api/v2/studies/{sid}", headers=headers)
        assert r1.json()["study_id"] == r2.json()["study_id"]
        assert r1.json()["phase"] == r2.json()["phase"]

    def test_multiple_studies_same_project(self):
        headers, _ = _register_and_login("multi")
        pid = f"proj_{_uid()}"

        ids = set()
        for _ in range(3):
            r = client.post("/api/v2/studies", json={"project_id": pid}, headers=headers)
            ids.add(r.json()["study_id"])
        assert len(ids) == 3

    def test_study_has_timestamps(self):
        headers, _ = _register_and_login("ts")
        create_r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
        }, headers=headers)
        sid = create_r.json()["study_id"]

        r = client.get(f"/api/v2/studies/{sid}", headers=headers)
        data = r.json()
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None


# =============================================================================
# 8. Backend health and V2 route registration
# =============================================================================

class TestBackendIntegration:
    def test_health_endpoint(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "running"

    def test_v2_routes_registered(self):
        routes = [getattr(r, "path", str(r)) for r in app.routes]
        assert any("/api/v2/studies" in p for p in routes)

    def test_v2_studies_get_requires_auth(self):
        r = client.get("/api/v2/studies")
        assert r.status_code == 401

    def test_v2_studies_post_requires_auth(self):
        r = client.post("/api/v2/studies", json={"project_id": "x"})
        assert r.status_code == 401


# =============================================================================
# 9. Direct phase manipulation (simulate AI progression)
# =============================================================================

class TestPhaseProgression:
    """Simulate phase progression by directly updating DB rows,
    verifying the API reflects state changes correctly."""

    def _create_study(self, headers) -> str:
        r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
        }, headers=headers)
        return r.json()["study_id"]

    def _set_phase(self, study_id: str, phase: str, **extra):
        db = app_db.SessionLocal()
        try:
            from app.api.v2.study_engine import StudyStateRow
            row = db.query(StudyStateRow).filter_by(study_id=study_id).first()
            assert row is not None
            row.phase = phase
            for k, v in extra.items():
                if hasattr(row, k):
                    setattr(row, k, v)
            db.commit()
        finally:
            db.close()

    def test_phase_shows_in_get(self):
        headers, _ = _register_and_login("phase1")
        sid = self._create_study(headers)
        self._set_phase(sid, "UNDERSTANDING")

        r = client.get(f"/api/v2/studies/{sid}", headers=headers)
        assert r.json()["phase"] == "UNDERSTANDING"

    def test_phase_shows_in_list(self):
        headers, _ = _register_and_login("phase2")
        sid = self._create_study(headers)
        self._set_phase(sid, "ANALYZED")

        r = client.get("/api/v2/studies", headers=headers)
        studies = r.json()["studies"]
        assert any(s["study_id"] == sid and s["phase"] == "ANALYZED" for s in studies)

    def test_approve_profile_in_needs_info_phase(self):
        headers, _ = _register_and_login("phase3")
        sid = self._create_study(headers)
        self._set_phase(sid, "NEEDS_INFORMATION", profile_confirmed=False)

        r = client.post(f"/api/v2/studies/{sid}/information-gate", json={
            "choice": "research",
        }, headers=headers)
        assert r.status_code == 200

    def test_approve_evidence_in_evidence_review(self):
        headers, _ = _register_and_login("phase4")
        sid = self._create_study(headers)
        self._set_phase(sid, "EVIDENCE_REVIEW", claims_json=[
            {"statement": "test claim", "source_type": "user_input", "confidence": 0.8}
        ])

        r = client.post(f"/api/v2/studies/{sid}/approve/evidence", json={
            "approved": True,
        }, headers=headers)
        assert r.status_code == 200

    def test_approve_assumptions_in_assumptions_review(self):
        headers, _ = _register_and_login("phase5")
        sid = self._create_study(headers)
        self._set_phase(sid, "ASSUMPTIONS_REVIEW", assumptions_json=[
            {"key": "revenue", "value": "1000000", "source": "user", "confidence": "medium"}
        ])

        r = client.post(f"/api/v2/studies/{sid}/approve/assumptions", json={
            "approved": True,
        }, headers=headers)
        assert r.status_code == 200

    def test_approve_evidence_empty_claims_400(self):
        headers, _ = _register_and_login("phase6")
        sid = self._create_study(headers)
        self._set_phase(sid, "EVIDENCE_REVIEW", claims_json=[])

        r = client.post(f"/api/v2/studies/{sid}/approve/evidence", json={
            "approved": True,
        }, headers=headers)
        assert r.status_code == 400
        assert "evidence" in r.json()["detail"].lower() or "No" in r.json()["detail"]

    def test_approve_assumptions_empty_400(self):
        headers, _ = _register_and_login("phase7")
        sid = self._create_study(headers)
        self._set_phase(sid, "ASSUMPTIONS_REVIEW", assumptions_json=[])

        r = client.post(f"/api/v2/studies/{sid}/approve/assumptions", json={
            "approved": True,
        }, headers=headers)
        assert r.status_code == 400

    def test_verdict_shows_in_get(self):
        headers, _ = _register_and_login("phase8")
        sid = self._create_study(headers)
        self._set_phase(sid, "DECISION_READY", verdict="GO",
                        decision_rationale="Strong fundamentals")

        r = client.get(f"/api/v2/studies/{sid}", headers=headers)
        data = r.json()
        assert data["verdict"] == "GO"
        assert data["decision_rationale"] == "Strong fundamentals"

    def test_verdict_shows_in_list(self):
        headers, _ = _register_and_login("phase9")
        sid = self._create_study(headers)
        self._set_phase(sid, "FUNDING_READY", verdict="GO_WITH_CONDITIONS")

        r = client.get("/api/v2/studies", headers=headers)
        studies = r.json()["studies"]
        match = [s for s in studies if s["study_id"] == sid]
        assert len(match) == 1
        assert match[0]["verdict"] == "GO_WITH_CONDITIONS"


# =============================================================================
# 10. Rejection / feedback flow
# =============================================================================

class TestRejectionFlow:
    def _create_and_set_phase(self, headers, phase, **extra):
        r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
        }, headers=headers)
        sid = r.json()["study_id"]
        db = app_db.SessionLocal()
        try:
            from app.api.v2.study_engine import StudyStateRow
            row = db.query(StudyStateRow).filter_by(study_id=sid).first()
            row.phase = phase
            for k, v in extra.items():
                if hasattr(row, k):
                    setattr(row, k, v)
            db.commit()
        finally:
            db.close()
        return sid

    def test_reject_profile_keeps_phase(self):
        headers, _ = _register_and_login("rej1")
        sid = self._create_and_set_phase(headers, "NEEDS_INFORMATION")

        r = client.post(f"/api/v2/studies/{sid}/information-gate", json={
            "choice": "manual",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["phase"] == "NEEDS_INFORMATION"
        assert r.json()["gate_choice"] == "manual"

    def test_reject_evidence_keeps_phase(self):
        headers, _ = _register_and_login("rej2")
        sid = self._create_and_set_phase(headers, "EVIDENCE_REVIEW", claims_json=[
            {"statement": "claim", "source_type": "user_input", "confidence": 0.5}
        ])

        r = client.post(f"/api/v2/studies/{sid}/approve/evidence", json={
            "approved": False,
            "feedback": "Sources are weak",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["phase"] == "EVIDENCE_REVIEW"

    def test_reject_assumptions_keeps_phase(self):
        headers, _ = _register_and_login("rej3")
        sid = self._create_and_set_phase(headers, "ASSUMPTIONS_REVIEW", assumptions_json=[
            {"key": "cost", "value": "500000", "source": "estimate", "confidence": "low"}
        ])

        r = client.post(f"/api/v2/studies/{sid}/approve/assumptions", json={
            "approved": False,
            "feedback": "Revenue assumptions too optimistic",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["phase"] == "ASSUMPTIONS_REVIEW"
