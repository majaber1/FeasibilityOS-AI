"""Discovery catalog + structured answers + bulk assumption approve."""
import os
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

if not os.environ.get("DATABASE_URL"):
    _TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _TMP.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + _TMP.name

_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _ROOT / "backend"
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_BACKEND))

from fastapi.testclient import TestClient

from app import db as app_db
from app.main import app

client = TestClient(app)
PASSWORD = "TestP@ss123!"


def setup_module(module):
    assert app_db.DB_ENABLED is True
    app_db.init_db()
    from app.api.v2.study_engine import StudyStateRow, StudyVersionRow  # noqa: F401

    app_db.Base.metadata.create_all(bind=app_db.engine)


def _auth(prefix: str) -> dict:
    email = f"disc_{prefix}_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    tok = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {tok}"}


def _project(headers: dict, name: str) -> int:
    r = client.post(
        "/projects/",
        headers=headers,
        json={"name": name, "industry": "technology", "investment": 1000000, "stage": "idea"},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


class TestDiscoveryCatalog:
    def test_four_golden_archetypes_classified(self):
        from ai_engine.agents.discovery_catalog import (
            build_questions_for_archetype,
            classify_archetype_from_text,
        )

        assert classify_archetype_from_text("WhatsApp AI Platform SaaS subscription") == "saas_digital"
        assert (
            classify_archetype_from_text("Residential complex in Riyadh under construction")
            == "real_estate"
        )
        assert classify_archetype_from_text("Enterprise data center Tier III racks MW") == "data_center"
        assert (
            classify_archetype_from_text("Government award letter ترسية جهة حكومية")
            == "government_contract"
        )

        saas_q = build_questions_for_archetype("saas_digital", "en")
        re_q = build_questions_for_archetype("real_estate", "en")
        assert any(q["id"] == "churn" for q in saas_q)
        assert any(q["id"] == "construction_progress" for q in re_q)
        assert any(q["id"] == "unit_count" for q in re_q)
        assert not any(q["id"] == "churn" for q in re_q)

    def test_structured_answers_persist(self):
        headers = _auth("ans")
        pid = _project(headers, "WhatsApp AI Platform")

        with patch("ai_engine.agents.discovery.get_llm") as mock_llm:
            llm = MagicMock()
            llm.invoke.return_value = MagicMock(
                content='```json\n{"archetype":"saas_digital","sector":"AI","stage":"idea","decision_goal":"feasibility","missing_information":[],"recommended_model":"saas_v1","summary":"SaaS idea."}\n```'
            )
            mock_llm.return_value = llm
            created = client.post(
                "/api/v2/studies",
                headers=headers,
                json={
                    "project_id": str(pid),
                    "language": "en",
                    "description": "WhatsApp AI Platform SaaS for SMBs",
                },
            )
        assert created.status_code == 200, created.text
        body = created.json()
        study_id = body["study_id"]
        assert body["phase"] in {"NEEDS_INFORMATION", "UNDERSTANDING"}
        questions = body.get("discovery_questions") or []
        assert len(questions) > 0
        assert all("```" not in (q.get("prompt") or "") for q in questions)

        answers = [{"id": q["id"], "value": (q.get("options") or ["x"])[0] if q.get("options") else 10} for q in questions[:3]]
        # Prefer typed values for currency/number
        for q in questions:
            if q["id"] == "subscription_price":
                answers.append({"id": q["id"], "value": 199})
            if q["id"] == "year1_customers":
                answers.append({"id": q["id"], "value": 500})

        res = client.post(
            f"/api/v2/studies/{study_id}/answer-questions",
            headers=headers,
            json={"answers": answers},
        )
        assert res.status_code == 200, res.text
        saved = res.json()
        assert saved["profile"]["structured_answers"]
        answered = [q for q in saved["discovery_questions"] if q.get("answered")]
        assert len(answered) >= 1


class TestBulkAssumptionApprove:
    def test_bulk_approve_draft_critical_then_pipeline(self):
        headers = _auth("bulk")
        pid = _project(headers, "Bulk Approve Co")
        created = client.post(
            "/api/v2/studies",
            headers=headers,
            json={"project_id": str(pid), "language": "en", "description": ""},
        )
        study_id = created.json()["study_id"]

        from app.api.v2 import study_engine as se

        db = app_db.SessionLocal()
        try:
            row = db.query(se.StudyStateRow).filter_by(study_id=study_id).first()
            row.phase = "ASSUMPTIONS_REVIEW"
            row.profile_json = {
                "archetype": "saas_digital",
                "sector": "AI",
                "stage": "idea",
                "decision_goal": "feasibility",
                "language": "en",
                "structured_answers": {
                    "subscription_price": 199,
                    "year1_customers": 400,
                    "cac": 500,
                    "churn": 3,
                    "development_cost": 800000,
                    "cloud_ai_cost": 20000,
                    "team_cost": 40000,
                },
                "recommended_model": "saas_v1",
            }
            row.profile_confirmed = True
            row.assumptions_json = [
                {
                    "key": "year1_customers",
                    "value": "400",
                    "source": "provisional",
                    "confidence": "medium",
                    "origin": "provisional_estimate",
                    "status": "draft",
                    "critical": True,
                    "low": "300",
                    "base": "400",
                    "high": "600",
                },
                {
                    "key": "subscription_price",
                    "value": "199",
                    "source": "provisional",
                    "confidence": "medium",
                    "origin": "provisional_estimate",
                    "status": "draft",
                    "critical": True,
                },
            ]
            row.assumptions_approved = False
            db.commit()
        finally:
            db.close()

        with patch("ai_engine.agents.financial_analyst.get_llm") as mock_fin, patch(
            "ai_engine.agents.risk.get_llm"
        ) as mock_risk, patch("ai_engine.agents.decision.get_llm") as mock_dec:
            for m in (mock_fin, mock_risk, mock_dec):
                llm = MagicMock()
                llm.invoke.side_effect = Exception("offline")
                m.return_value = llm
            res = client.post(
                f"/api/v2/studies/{study_id}/approve/assumptions",
                headers=headers,
                json={"approved": True},
            )
        assert res.status_code == 200, res.text
        body = res.json()
        statuses = {a["key"]: a["status"] for a in body["assumptions"]}
        assert statuses["year1_customers"] == "approved"
        assert body["phase"] in {
            "READY_FOR_ANALYSIS",
            "ANALYZED",
            "DECISION_READY",
            "FUNDING_READY",
        }
        # Must not remain stuck requiring per-item approve
        assert "still draft" not in (body.get("error") or "").lower()

    def test_rejected_blocks_bulk_approve(self):
        headers = _auth("rej")
        pid = _project(headers, "Reject Block")
        created = client.post(
            "/api/v2/studies",
            headers=headers,
            json={"project_id": str(pid), "language": "en", "description": ""},
        )
        study_id = created.json()["study_id"]
        from app.api.v2 import study_engine as se

        db = app_db.SessionLocal()
        try:
            row = db.query(se.StudyStateRow).filter_by(study_id=study_id).first()
            row.phase = "ASSUMPTIONS_REVIEW"
            row.assumptions_json = [
                {
                    "key": "cac",
                    "value": "1000",
                    "source": "provisional",
                    "confidence": "low",
                    "origin": "provisional_estimate",
                    "status": "rejected",
                    "critical": True,
                }
            ]
            db.commit()
        finally:
            db.close()

        res = client.post(
            f"/api/v2/studies/{study_id}/approve/assumptions",
            headers=headers,
            json={"approved": True},
        )
        assert res.status_code == 400
        assert "rejected" in res.text.lower()


class TestFinancialIncompleteAndFunding:
    def test_model_incomplete_not_fake_npv(self):
        from ai_engine.agents.financial_analyst import run_financial_analysis
        from ai_engine.models.study_state import Assumption, ProjectProfile, StudyState

        state = StudyState(
            study_id="s1",
            project_id="p1",
            user_id="u1",
            language="en",
            phase="READY_FOR_ANALYSIS",
            profile=ProjectProfile(archetype="saas_digital", stage="idea"),
            assumptions=[
                Assumption(
                    key="notes",
                    value="no numbers",
                    source="user",
                    confidence="low",
                    origin="user",
                    status="approved",
                )
            ],
            assumptions_approved=True,
        )
        with patch("ai_engine.agents.financial_analyst.get_llm") as mock_llm:
            llm = MagicMock()
            llm.invoke.side_effect = Exception("offline")
            mock_llm.return_value = llm
            out = run_financial_analysis(state)
        assert out.financial_results["status"] == "MODEL_INCOMPLETE"
        assert out.financial_results["npv"] is None
        assert out.verdict == "NEED_MORE_VALIDATION"

    def test_funding_reuses_matcher(self):
        from ai_engine.agents.funding import run_funding
        from ai_engine.models.study_state import ProjectProfile, StudyState

        state = StudyState(
            study_id="s2",
            project_id="p2",
            user_id="u2",
            language="en",
            phase="FUNDING_READY",
            profile=ProjectProfile(archetype="saas_digital", stage="mvp", sector="AI"),
            verdict="GO_WITH_CONDITIONS",
            financial_results={"analysis_complete": True, "npv": 1000, "status": "OK"},
        )
        out = run_funding(state)
        funding = out.workflow_meta["funding"]
        assert funding["score_explained"] is True
        assert funding["matches"]
        assert "score_percent" in funding
