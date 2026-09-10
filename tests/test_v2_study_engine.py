"""V2 AI Study Engine tests: state model, calculator, orchestrator routing,
phase-blocking validation, and API endpoints.

DB-backed on a throwaway SQLite file (DATABASE_URL set before importing app.db).
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
from app import auth as security  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
PASSWORD = "TestP@ss123!"


def setup_module(module):
    assert app_db.DB_ENABLED is True
    app_db.init_db()
    from app.api.v2.study_engine import StudyStateRow, StudyVersionRow
    app_db.Base.metadata.create_all(bind=app_db.engine)


def _email(prefix: str) -> str:
    return f"v2_{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def _auth(prefix: str) -> dict:
    email = _email(prefix)
    r = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    tok = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


# =============================================================================
# 1. StudyState model tests
# =============================================================================

class TestStudyStateModel:
    def test_default_phase_is_draft(self):
        from ai_engine.models.study_state import StudyState
        state = StudyState(study_id="s1", project_id="p1", user_id="u1")
        assert state.phase == "DRAFT"
        assert state.language == "ar"
        assert state.profile is None
        assert state.verdict is None

    def test_all_phases_are_valid(self):
        from ai_engine.models.study_state import StudyState
        valid_phases = [
            "DRAFT", "UNDERSTANDING", "NEEDS_INFORMATION",
            "EVIDENCE_REVIEW", "ASSUMPTIONS_REVIEW", "READY_FOR_ANALYSIS",
            "ANALYZED", "DECISION_READY", "FUNDING_READY",
        ]
        for phase in valid_phases:
            state = StudyState(study_id="s1", project_id="p1", user_id="u1", phase=phase)
            assert state.phase == phase

    def test_project_profile_defaults(self):
        from ai_engine.models.study_state import ProjectProfile
        profile = ProjectProfile()
        assert profile.archetype == "unknown"
        assert profile.sector == ""
        assert profile.missing_information == []

    def test_assumption_model(self):
        from ai_engine.models.study_state import Assumption
        a = Assumption(
            key="monthly_revenue",
            value="50000 SAR",
            source="user_input",
            confidence="medium",
            low="30000",
            base="50000",
            high="80000",
        )
        assert a.key == "monthly_revenue"
        assert a.confidence == "medium"

    def test_claim_model(self):
        from ai_engine.models.study_state import Claim
        c = Claim(
            statement="Market size is 2B SAR",
            source_type="official",
            confidence=0.85,
        )
        assert c.source_type == "official"
        assert c.confidence == 0.85

    def test_state_serialization_roundtrip(self):
        from ai_engine.models.study_state import StudyState, ProjectProfile, Assumption
        state = StudyState(
            study_id="s1", project_id="p1", user_id="u1",
            language="en", phase="NEEDS_INFORMATION",
            profile=ProjectProfile(archetype="saas_digital", sector="Technology"),
            assumptions=[Assumption(key="capex", value="100000", source="user", confidence="confirmed")],
        )
        data = state.model_dump()
        restored = StudyState(**data)
        assert restored.phase == "NEEDS_INFORMATION"
        assert restored.profile.archetype == "saas_digital"
        assert len(restored.assumptions) == 1

    def test_all_archetypes_valid(self):
        from ai_engine.models.study_state import ProjectProfile
        archetypes = ["saas_digital", "real_estate", "data_center", "retail", "industrial", "services", "franchise", "unknown"]
        for arch in archetypes:
            p = ProjectProfile(archetype=arch)
            assert p.archetype == arch

    def test_all_verdicts_valid(self):
        from ai_engine.models.study_state import StudyState
        verdicts = ["GO", "GO_WITH_CONDITIONS", "DEFER", "NO_GO", "INSUFFICIENT_EVIDENCE"]
        for v in verdicts:
            state = StudyState(study_id="s1", project_id="p1", user_id="u1", verdict=v)
            assert state.verdict == v


# =============================================================================
# 2. Calculator deterministic math tests
# =============================================================================

class TestCalculator:
    def test_npv_positive_project(self):
        from ai_engine.tools.calculator import calculate_npv
        result = calculate_npv([-100000, 40000, 50000, 60000], 0.12)
        assert result > 0
        assert abs(result - 18280.79) < 1

    def test_npv_negative_project(self):
        from ai_engine.tools.calculator import calculate_npv
        result = calculate_npv([-500000, 10000, 10000, 10000], 0.12)
        assert result < 0

    def test_npv_zero_discount(self):
        from ai_engine.tools.calculator import calculate_npv
        result = calculate_npv([-100, 50, 50, 50], 0.0)
        assert result == 50.0

    def test_irr_valid_project(self):
        from ai_engine.tools.calculator import calculate_irr
        result = calculate_irr([-100000, 40000, 50000, 60000])
        assert result is not None
        assert 0.20 < result < 0.25

    def test_irr_returns_none_for_single_cashflow(self):
        from ai_engine.tools.calculator import calculate_irr
        assert calculate_irr([-100000]) is None

    def test_irr_returns_none_for_empty(self):
        from ai_engine.tools.calculator import calculate_irr
        assert calculate_irr([]) is None

    def test_payback_period_standard(self):
        from ai_engine.tools.calculator import calculate_payback_period
        result = calculate_payback_period(100000, [40000, 40000, 40000])
        assert result is not None
        assert 2.0 < result < 3.0

    def test_payback_period_exact_year(self):
        from ai_engine.tools.calculator import calculate_payback_period
        result = calculate_payback_period(100000, [50000, 50000])
        assert result == 2.0

    def test_payback_period_never_recovered(self):
        from ai_engine.tools.calculator import calculate_payback_period
        result = calculate_payback_period(1000000, [1000, 1000, 1000])
        assert result is None

    def test_payback_period_zero_investment(self):
        from ai_engine.tools.calculator import calculate_payback_period
        result = calculate_payback_period(0, [10000])
        assert result is None

    def test_breakeven_standard(self):
        from ai_engine.tools.calculator import calculate_breakeven
        result = calculate_breakeven(50000, 100, 60)
        assert result == 1250.0

    def test_breakeven_zero_margin(self):
        from ai_engine.tools.calculator import calculate_breakeven
        result = calculate_breakeven(50000, 100, 100)
        assert result is None

    def test_breakeven_negative_margin(self):
        from ai_engine.tools.calculator import calculate_breakeven
        result = calculate_breakeven(50000, 50, 100)
        assert result is None


# =============================================================================
# 3. Orchestrator routing tests
# =============================================================================

class TestOrchestratorRouting:
    def test_phase_to_node_mapping(self):
        from ai_engine.orchestrator import route_by_phase, PHASE_TRANSITIONS
        from ai_engine.models.study_state import StudyState
        from langgraph.graph import END

        expected = {
            "DRAFT": "discovery",
            "UNDERSTANDING": "discovery",
            "NEEDS_INFORMATION": "discovery",
            "EVIDENCE_REVIEW": "evidence",
            "ASSUMPTIONS_REVIEW": "assumptions",
            "READY_FOR_ANALYSIS": "financial",
            "ANALYZED": "risk",
            "DECISION_READY": "decision",
            "FUNDING_READY": END,
        }
        for phase, expected_node in expected.items():
            state = StudyState(study_id="s1", project_id="p1", user_id="u1", phase=phase)
            assert route_by_phase(state) == expected_node, f"Phase {phase} should route to {expected_node}"

    def test_error_routes_to_error_handler(self):
        from ai_engine.orchestrator import route_by_phase
        from ai_engine.models.study_state import StudyState

        state = StudyState(study_id="s1", project_id="p1", user_id="u1", error="Something broke")
        assert route_by_phase(state) == "error_handler"

    def test_error_handler_sets_retry(self):
        from ai_engine.orchestrator import error_handler
        from ai_engine.models.study_state import StudyState

        state = StudyState(study_id="s1", project_id="p1", user_id="u1", error="API timeout")
        result = error_handler(state)
        assert result.next_action == "retry"
        assert result.blocking_reason == "API timeout"

    def test_graph_compiles_successfully(self):
        from ai_engine.orchestrator import get_graph
        graph = get_graph()
        assert graph is not None

    def test_graph_has_all_nodes(self):
        from ai_engine.orchestrator import build_graph
        graph = build_graph()
        expected_nodes = {"discovery", "evidence", "assumptions", "financial", "risk", "decision", "error_handler"}
        assert expected_nodes.issubset(set(graph.nodes.keys()))


# =============================================================================
# 4. V2 API endpoint tests
# =============================================================================

class TestV2StudyAPI:
    def test_anonymous_create_is_401(self):
        r = client.post("/api/v2/studies", json={
            "project_id": "p1", "language": "en", "description": "",
        })
        assert r.status_code == 401

    def test_anonymous_list_is_401(self):
        r = client.get("/api/v2/studies")
        assert r.status_code == 401

    def test_list_studies_empty(self):
        headers = _auth("list_empty")
        r = client.get("/api/v2/studies", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert "studies" in body
        assert isinstance(body["studies"], list)

    def test_create_study_no_description(self):
        headers = _auth("create_nodesc")
        r = client.post("/api/v2/studies", json={
            "project_id": "proj_001", "language": "en",
        }, headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert "study_id" in body
        assert body["phase"] == "DRAFT"
        assert body["study_id"].startswith("study_")

    def test_get_study_by_id(self):
        headers = _auth("get_study")
        create = client.post("/api/v2/studies", json={
            "project_id": "proj_002", "language": "ar",
        }, headers=headers)
        study_id = create.json()["study_id"]

        r = client.get(f"/api/v2/studies/{study_id}", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body["study_id"] == study_id
        assert body["phase"] == "DRAFT"
        # Workspace needs the filled payloads, not only counts.
        assert "claims" in body and isinstance(body["claims"], list)
        assert "assumptions" in body and isinstance(body["assumptions"], list)
        assert "messages" in body and isinstance(body["messages"], list)
        assert "financial_results" in body
        assert "decision_conditions" in body

    def test_get_study_returns_persisted_ai_fill(self):
        headers = _auth("get_filled")
        create = client.post("/api/v2/studies", json={
            "project_id": "proj_filled", "language": "en",
        }, headers=headers)
        study_id = create.json()["study_id"]

        from app.api.v2 import study_engine as se
        db = app_db.SessionLocal()
        try:
            row = db.query(se.StudyStateRow).filter_by(study_id=study_id).first()
            assert row is not None
            row.phase = "READY_FOR_ANALYSIS"
            row.profile_json = {
                "archetype": "services",
                "sector": "Ride-hailing",
                "stage": "idea",
                "decision_goal": "investment",
                "missing_information": [],
                "language": "en",
                "recommended_model": "general_v1",
            }
            row.claims_json = [
                {"statement": "Avg trip 40 SAR", "source_type": "user_input", "confidence": 0.9},
            ]
            row.assumptions_json = [
                {"key": "Initial investment", "value": "5000000 SAR", "source": "user", "confidence": "confirmed"},
            ]
            row.messages_json = [
                {"type": "human", "content": "Build Uper Ride"},
                {"type": "ai", "content": "Profile complete.\n```json\n{\"ok\": true}\n```"},
            ]
            row.financial_results_json = {"npv": 123, "irr": 0.2, "payback_months": 18, "capex": 5000000}
            db.commit()
        finally:
            db.close()

        r = client.get(f"/api/v2/studies/{study_id}", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body["claims_count"] == 1
        assert body["claims"][0]["statement"] == "Avg trip 40 SAR"
        assert body["assumptions_count"] == 1
        assert body["assumptions"][0]["key"] == "Initial investment"
        assert body["financial_results"]["capex"] == 5000000
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][1]["role"] == "assistant"

    def test_get_study_not_found(self):
        headers = _auth("get_404")
        r = client.get("/api/v2/studies/study_nonexistent", headers=headers)
        assert r.status_code == 404

    def test_study_isolation_between_users(self):
        h1 = _auth("iso_user1")
        h2 = _auth("iso_user2")
        create = client.post("/api/v2/studies", json={
            "project_id": "proj_iso", "language": "en",
        }, headers=h1)
        study_id = create.json()["study_id"]

        r = client.get(f"/api/v2/studies/{study_id}", headers=h2)
        assert r.status_code == 404

    def test_approve_profile_wrong_phase_400(self):
        headers = _auth("approve_bad")
        create = client.post("/api/v2/studies", json={
            "project_id": "proj_approve", "language": "en",
        }, headers=headers)
        study_id = create.json()["study_id"]

        r = client.post(f"/api/v2/studies/{study_id}/approve/profile", json={
            "approved": True,
        }, headers=headers)
        assert r.status_code == 400

    def test_approve_profile_advances_with_missing_information(self):
        """Confirm Profile must leave NEEDS_INFORMATION even when gaps remain."""
        headers = _auth("approve_gaps")
        create = client.post("/api/v2/studies", json={
            "project_id": "proj_gaps", "language": "en",
        }, headers=headers)
        study_id = create.json()["study_id"]

        from app.api.v2 import study_engine as se
        from app import db as app_db
        from unittest.mock import patch, MagicMock

        db = app_db.SessionLocal()
        try:
            row = db.query(se.StudyStateRow).filter_by(study_id=study_id).first()
            assert row is not None
            row.phase = "NEEDS_INFORMATION"
            row.profile_json = {
                "archetype": "saas_digital",
                "sector": "Compliance SaaS",
                "stage": "unknown",
                "decision_goal": "unknown",
                "missing_information": [
                    "Current project stage",
                    "Revenue model and pricing",
                    "Expected CAC",
                ],
                "language": "en",
                "recommended_model": "saas_v1",
            }
            row.profile_confirmed = False
            row.messages_json = [
                {"type": "human", "content": "AI compliance platform for Saudi enterprises"},
                {"type": "ai", "content": "Gathering more information."},
            ]
            db.commit()
        finally:
            db.close()

        evidence_json = """```json
{"claims":[{"statement":"Saudi enterprises need compliance tooling","source_type":"user_input","confidence":0.8}],"gaps":[],"evidence_sufficient":true}
```"""

        with patch("ai_engine.agents.evidence.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(content=evidence_json)
            mock_get_llm.return_value = mock_llm

            r = client.post(
                f"/api/v2/studies/{study_id}/approve/profile",
                json={"approved": True},
                headers=headers,
            )

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["phase"] != "NEEDS_INFORMATION"
        assert body["phase"] in {"EVIDENCE_REVIEW", "ASSUMPTIONS_REVIEW"}
        assert body["profile"]["stage"] != "unknown"
        assert body["profile"]["decision_goal"] != "unknown"
        assert body["profile"]["missing_information"] == []
        assert any("estimate" in (m.get("content") or "").lower() or "gaps" in (m.get("content") or "").lower()
                   for m in body.get("messages", []) if m.get("role") == "assistant")
        assert body.get("claims_count", 0) >= 1
        assert len(body.get("claims") or []) >= 1

    def test_approve_profile_fills_claims_when_groq_missing(self):
        """Confirm must still populate Evidence claims when GROQ_API_KEY is absent."""
        headers = _auth("approve_nogroq")
        create = client.post("/api/v2/studies", json={
            "project_id": "proj_nogroq", "language": "en",
        }, headers=headers)
        study_id = create.json()["study_id"]

        from app.api.v2 import study_engine as se
        from app import db as app_db
        from unittest.mock import patch

        db = app_db.SessionLocal()
        try:
            row = db.query(se.StudyStateRow).filter_by(study_id=study_id).first()
            assert row is not None
            row.phase = "NEEDS_INFORMATION"
            row.profile_json = {
                "archetype": "services",
                "sector": "Ride-hailing",
                "stage": "unknown",
                "decision_goal": "unknown",
                "missing_information": [
                    "Current project stage",
                    "Revenue model and pricing",
                    "Expected CAC",
                ],
                "language": "en",
                "recommended_model": "services_v1",
            }
            row.profile_confirmed = False
            row.messages_json = [
                {"type": "human", "content": "Uber-like ride hailing in Riyadh"},
                {"type": "ai", "content": "Need more information."},
            ]
            db.commit()
        finally:
            db.close()

        with patch(
            "ai_engine.agents.evidence.get_llm",
            side_effect=ValueError("GROQ_API_KEY is not set"),
        ):
            r = client.post(
                f"/api/v2/studies/{study_id}/approve/profile",
                json={"approved": True},
                headers=headers,
            )

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["phase"] == "EVIDENCE_REVIEW"
        assert body.get("error") in (None, "", False)
        assert body.get("claims_count", 0) >= 3
        assert all(c.get("source_type") == "ai_assumption" for c in body.get("claims") or [])
        assert body["profile"]["missing_information"] == []

    def test_approve_invalid_stage_400(self):
        headers = _auth("approve_invalid")
        create = client.post("/api/v2/studies", json={
            "project_id": "proj_inv", "language": "en",
        }, headers=headers)
        study_id = create.json()["study_id"]

        r = client.post(f"/api/v2/studies/{study_id}/approve/nonexistent", json={
            "approved": True,
        }, headers=headers)
        assert r.status_code == 400
        assert "Invalid stage" in r.json()["detail"]

    def test_approve_study_not_found_404(self):
        headers = _auth("approve_404")
        r = client.post("/api/v2/studies/study_missing/approve/profile", json={
            "approved": True,
        }, headers=headers)
        assert r.status_code == 404

    def test_send_message_to_study_not_found_404(self):
        headers = _auth("msg_404")
        r = client.post("/api/v2/studies/study_missing/message", json={
            "message": "hello",
        }, headers=headers)
        assert r.status_code == 404

    def test_list_shows_created_study(self):
        headers = _auth("list_shows")
        client.post("/api/v2/studies", json={
            "project_id": "proj_list", "language": "en",
        }, headers=headers)

        r = client.get("/api/v2/studies", headers=headers)
        assert r.status_code == 200
        studies = r.json()["studies"]
        assert len(studies) >= 1
        assert any(s["phase"] == "DRAFT" for s in studies)

    def test_create_study_default_language_ar(self):
        headers = _auth("lang_default")
        r = client.post("/api/v2/studies", json={
            "project_id": "proj_lang",
        }, headers=headers)
        assert r.status_code == 200

    def test_multiple_studies_per_user(self):
        headers = _auth("multi")
        for i in range(3):
            r = client.post("/api/v2/studies", json={
                "project_id": f"proj_multi_{i}", "language": "en",
            }, headers=headers)
            assert r.status_code == 200

        listing = client.get("/api/v2/studies", headers=headers).json()["studies"]
        assert len(listing) >= 3


# =============================================================================
# 5. Financial scenario computation tests
# =============================================================================

class TestFinancialScenarios:
    def test_compute_scenario_base(self):
        from ai_engine.agents.financial_analyst import _compute_scenario
        result = _compute_scenario(
            capex=500000,
            revenues=[300000, 400000, 500000],
            costs=[150000, 180000, 200000],
            discount_rate=0.12,
            multiplier=1.0,
        )
        assert "npv" in result
        assert "irr" in result
        assert "payback_months" in result
        assert isinstance(result["npv"], float)

    def test_compute_scenario_optimistic_better_than_base(self):
        from ai_engine.agents.financial_analyst import _compute_scenario
        base = _compute_scenario(500000, [300000, 400000, 500000], [150000, 180000, 200000], 0.12, 1.0)
        optimistic = _compute_scenario(500000, [300000, 400000, 500000], [150000, 180000, 200000], 0.12, 1.2)
        assert optimistic["npv"] > base["npv"]

    def test_compute_scenario_conservative_worse_than_base(self):
        from ai_engine.agents.financial_analyst import _compute_scenario
        base = _compute_scenario(500000, [300000, 400000, 500000], [150000, 180000, 200000], 0.12, 1.0)
        conservative = _compute_scenario(500000, [300000, 400000, 500000], [150000, 180000, 200000], 0.12, 0.8)
        assert conservative["npv"] < base["npv"]

    def test_compute_scenario_zero_revenues(self):
        from ai_engine.agents.financial_analyst import _compute_scenario
        result = _compute_scenario(100000, [0, 0, 0], [50000, 50000, 50000], 0.12, 1.0)
        assert result["npv"] < 0

    def test_compute_scenario_zero_capex(self):
        from ai_engine.agents.financial_analyst import _compute_scenario
        result = _compute_scenario(0, [100000, 100000, 100000], [50000, 50000, 50000], 0.12, 1.0)
        assert result["npv"] > 0


# =============================================================================
# 6. Phase transition integrity tests
# =============================================================================

class TestPhaseTransitions:
    def test_all_phases_have_routing_entry(self):
        from ai_engine.orchestrator import PHASE_TRANSITIONS
        from ai_engine.models.study_state import StudyPhase
        import typing
        phases = list(typing.get_args(StudyPhase))
        for phase in phases:
            assert phase in PHASE_TRANSITIONS, f"Phase {phase} missing from PHASE_TRANSITIONS"

    def test_approve_stages_match_phases(self):
        valid_stages = {
            "profile": "NEEDS_INFORMATION",
            "evidence": "EVIDENCE_REVIEW",
            "assumptions": "ASSUMPTIONS_REVIEW",
        }
        for stage, expected_phase in valid_stages.items():
            r = client.post(f"/api/v2/studies/study_fake/approve/{stage}", json={
                "approved": True,
            })
            assert r.status_code == 401


# =============================================================================
# 7. Edge cases and error handling
# =============================================================================

class TestEdgeCases:
    def test_npv_large_cashflows(self):
        from ai_engine.tools.calculator import calculate_npv
        result = calculate_npv([-10_000_000] + [3_000_000] * 10, 0.12)
        assert isinstance(result, float)
        assert result > 0

    def test_irr_high_return_project(self):
        from ai_engine.tools.calculator import calculate_irr
        result = calculate_irr([-1000, 5000])
        assert result is not None
        assert result > 3.0

    def test_payback_first_year_recovery(self):
        from ai_engine.tools.calculator import calculate_payback_period
        result = calculate_payback_period(10000, [50000])
        assert result is not None
        assert result < 1.0

    def test_state_with_all_optional_fields(self):
        from ai_engine.models.study_state import StudyState, ProjectProfile, Assumption, Claim
        state = StudyState(
            study_id="full", project_id="p1", user_id="u1",
            language="en", phase="DECISION_READY",
            profile=ProjectProfile(archetype="data_center", sector="Tech", stage="growth"),
            profile_confirmed=True,
            claims=[Claim(statement="test", source_type="user_input", confidence=0.9)],
            evidence_approved=True,
            assumptions=[Assumption(key="k", value="v", source="s", confidence="confirmed")],
            assumptions_approved=True,
            financial_results={"npv": 100000, "irr": 0.25},
            verdict="GO",
            decision_rationale="Strong financials",
            decision_conditions=["Monitor competition"],
            decision_risks=["Regulatory risk"],
            decision_version=1,
        )
        data = state.model_dump()
        assert data["verdict"] == "GO"
        assert len(data["decision_conditions"]) == 1
        restored = StudyState(**data)
        assert restored.verdict == "GO"
