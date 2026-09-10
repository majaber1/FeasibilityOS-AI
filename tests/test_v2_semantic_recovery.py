"""Phase A semantic recovery: Evidence vs Assumptions invariant tests."""
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

import pytest
from fastapi.testclient import TestClient

from app import db as app_db
from app.main import app

client = TestClient(app)
PASSWORD = "TestP@ss123!"


def setup_module(module):
    assert app_db.DB_ENABLED is True
    app_db.init_db()
    from app.api.v2.study_engine import StudyStateRow, StudyVersionRow

    app_db.Base.metadata.create_all(bind=app_db.engine)


def _auth(prefix: str) -> dict:
    email = f"sem_{prefix}_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    tok = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {tok}"}


def _seed_needs_information(study_id: str, *, gaps: list[str] | None = None):
    from app.api.v2 import study_engine as se

    db = app_db.SessionLocal()
    try:
        row = db.query(se.StudyStateRow).filter_by(study_id=study_id).first()
        assert row is not None
        row.phase = "NEEDS_INFORMATION"
        row.profile_json = {
            "archetype": "saas_digital",
            "sector": "RegTech",
            "stage": "idea",
            "decision_goal": "feasibility",
            "missing_information": gaps
            or [
                "Pricing strategy",
                "Target customer segments",
                "CAC assumptions",
            ],
            "language": "en",
            "recommended_model": "saas_v1",
        }
        row.profile_confirmed = False
        row.claims_json = []
        row.assumptions_json = []
        row.messages_json = [
            {"type": "human", "content": "Multazim compliance platform"},
            {"type": "ai", "content": "Need more information."},
        ]
        db.commit()
    finally:
        db.close()


class TestSemanticInvariant:
    def test_claim_model_rejects_ai_assumption(self):
        from ai_engine.models.study_state import Claim
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Claim(
                statement="fake estimate",
                source_type="ai_assumption",
                confidence=0.4,
            )

    def test_filter_drops_ai_assumption_claims(self):
        from ai_engine.models.study_state import filter_evidence_claims

        cleaned = filter_evidence_claims(
            [
                {
                    "statement": "estimate",
                    "source_type": "ai_assumption",
                    "confidence": 0.4,
                },
                {
                    "statement": "SAMA circular X applies",
                    "source_type": "official",
                    "source_url": "https://example.gov.sa/x",
                    "source_title": "SAMA",
                    "confidence": 0.8,
                },
            ]
        )
        assert len(cleaned) == 1
        assert cleaned[0].source_type == "official"

    def test_illegal_transition_rejected(self):
        from ai_engine.models.study_state import assert_legal_transition

        with pytest.raises(ValueError):
            assert_legal_transition("DRAFT", "FUNDING_READY")


class TestInformationGate:
    def test_manual_stays_needs_information(self):
        headers = _auth("manual")
        create = client.post(
            "/api/v2/studies",
            json={"project_id": "p_manual", "language": "en"},
            headers=headers,
        )
        study_id = create.json()["study_id"]
        _seed_needs_information(study_id)

        r = client.post(
            f"/api/v2/studies/{study_id}/information-gate",
            json={"choice": "manual"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["phase"] == "NEEDS_INFORMATION"
        assert body["gate_choice"] == "manual"
        assert body["claims_count"] == 0
        assert (body.get("profile") or {}).get("missing_information")

    def test_research_never_fabricates_evidence_without_provider(self):
        headers = _auth("research")
        create = client.post(
            "/api/v2/studies",
            json={"project_id": "p_research", "language": "en"},
            headers=headers,
        )
        study_id = create.json()["study_id"]
        _seed_needs_information(study_id)

        with patch(
            "ai_engine.agents.evidence.get_llm",
            side_effect=ValueError("GROQ_API_KEY is not set"),
        ):
            r = client.post(
                f"/api/v2/studies/{study_id}/information-gate",
                json={"choice": "research"},
                headers=headers,
            )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["phase"] == "EVIDENCE_REVIEW"
        assert body["gate_choice"] == "research"
        assert body["claims_count"] == 0
        assert body["evidence_status"] in {"empty", "degraded"}
        assert all(c.get("source_type") != "ai_assumption" for c in body.get("claims") or [])

    def test_provisional_creates_assumptions_not_evidence(self):
        headers = _auth("prov")
        create = client.post(
            "/api/v2/studies",
            json={"project_id": "p_prov", "language": "en"},
            headers=headers,
        )
        study_id = create.json()["study_id"]
        _seed_needs_information(study_id)

        with patch(
            "ai_engine.agents.assumption.get_llm",
            side_effect=ValueError("GROQ_API_KEY is not set"),
        ):
            r = client.post(
                f"/api/v2/studies/{study_id}/information-gate",
                json={"choice": "provisional"},
                headers=headers,
            )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["phase"] == "ASSUMPTIONS_REVIEW"
        assert body["gate_choice"] == "provisional"
        assert body["claims_count"] == 0
        assert body["evidence_status"] == "empty"
        assert body["assumptions_count"] >= 1
        assert all(
            a.get("origin") == "provisional_estimate" for a in body.get("assumptions") or []
        )

    def test_legacy_approve_profile_rejected(self):
        headers = _auth("legacy")
        create = client.post(
            "/api/v2/studies",
            json={"project_id": "p_legacy", "language": "en"},
            headers=headers,
        )
        study_id = create.json()["study_id"]
        _seed_needs_information(study_id)
        r = client.post(
            f"/api/v2/studies/{study_id}/approve/profile",
            json={"approved": True},
            headers=headers,
        )
        assert r.status_code == 400
        assert "information-gate" in r.json()["detail"]

    def test_item_action_approve_assumption(self):
        headers = _auth("item")
        create = client.post(
            "/api/v2/studies",
            json={"project_id": "p_item", "language": "en"},
            headers=headers,
        )
        study_id = create.json()["study_id"]
        _seed_needs_information(study_id)
        with patch(
            "ai_engine.agents.assumption.get_llm",
            side_effect=ValueError("GROQ_API_KEY is not set"),
        ):
            client.post(
                f"/api/v2/studies/{study_id}/information-gate",
                json={"choice": "provisional"},
                headers=headers,
            )
        r = client.post(
            f"/api/v2/studies/{study_id}/item-action",
            json={"target": "assumption", "index": 0, "action": "approve"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["assumptions"][0]["status"] == "approved"

    def test_persistence_after_provisional_reload(self):
        headers = _auth("persist")
        create = client.post(
            "/api/v2/studies",
            json={"project_id": "p_persist", "language": "en"},
            headers=headers,
        )
        study_id = create.json()["study_id"]
        _seed_needs_information(study_id)
        with patch(
            "ai_engine.agents.assumption.get_llm",
            side_effect=ValueError("GROQ_API_KEY is not set"),
        ):
            client.post(
                f"/api/v2/studies/{study_id}/information-gate",
                json={"choice": "provisional"},
                headers=headers,
            )
        g = client.get(f"/api/v2/studies/{study_id}", headers=headers)
        assert g.status_code == 200
        body = g.json()
        assert body["phase"] == "ASSUMPTIONS_REVIEW"
        assert body["claims_count"] == 0
        assert body["assumptions_count"] >= 1
        assert body["gate_choice"] == "provisional"


class TestAIFirstProductPrinciples:
    """Acceptance: AI-first autonomous platform — not a manual form builder."""

    PREFERRED_GATE = "research"
    FALLBACK_GATE = "provisional"
    OPTIONAL_GATE = "manual"
    PRIMARY_CTA_EN = "Generate AI Study Draft"
    PRIMARY_CTA_AR = "إنشاء مسودة دراسة بالذكاء الاصطناعي"
    GOVERNED_GATES = (
        "Project Profile approval",
        "Evidence and Assumptions approval",
        "Final Decision approval",
    )

    def test_gate_choice_hierarchy_is_documented(self):
        assert self.PREFERRED_GATE == "research"
        assert self.FALLBACK_GATE == "provisional"
        assert self.OPTIONAL_GATE == "manual"
        assert "AI Study Draft" in self.PRIMARY_CTA_EN
        assert "مسودة دراسة" in self.PRIMARY_CTA_AR
        assert len(self.GOVERNED_GATES) == 3

    def test_research_path_remains_open_for_later_phases(self):
        """Research must stay callable and never fabricate Evidence (Phases B–F unblock)."""
        headers = _auth("ai_first")
        create = client.post(
            "/api/v2/studies",
            json={"project_id": "p_ai_first", "language": "en"},
            headers=headers,
        )
        study_id = create.json()["study_id"]
        _seed_needs_information(study_id)
        with patch(
            "ai_engine.agents.evidence.get_llm",
            side_effect=ValueError("GROQ_API_KEY is not set"),
        ):
            r = client.post(
                f"/api/v2/studies/{study_id}/information-gate",
                json={"choice": self.PREFERRED_GATE},
                headers=headers,
            )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["gate_choice"] == "research"
        assert body["phase"] == "EVIDENCE_REVIEW"
        assert body["claims_count"] == 0
        assert body.get("evidence_status") in {"empty", "degraded"}
        banned = {"ai_assumption", "provisional", "estimate", "llm"}
        for claim in body.get("claims") or []:
            assert claim.get("source_type") not in banned

    def test_manual_is_optional_not_forced_happy_path(self):
        headers = _auth("ai_manual_opt")
        create = client.post(
            "/api/v2/studies",
            json={"project_id": "p_ai_manual", "language": "en"},
            headers=headers,
        )
        study_id = create.json()["study_id"]
        _seed_needs_information(study_id)
        r = client.post(
            f"/api/v2/studies/{study_id}/information-gate",
            json={"choice": self.OPTIONAL_GATE},
            headers=headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["phase"] == "NEEDS_INFORMATION"
        assert body["gate_choice"] == "manual"
        assert body["claims_count"] == 0
        # Manual must not auto-advance into Evidence/Assumptions (form-builder anti-pattern)
        assert body.get("assumptions_count", 0) == 0

    def test_three_choices_are_semantically_distinct(self):
        outcomes = {}
        for choice, prefix in (
            ("manual", "dist_m"),
            ("research", "dist_r"),
            ("provisional", "dist_p"),
        ):
            headers = _auth(prefix)
            create = client.post(
                "/api/v2/studies",
                json={"project_id": f"p_{prefix}", "language": "en"},
                headers=headers,
            )
            study_id = create.json()["study_id"]
            _seed_needs_information(study_id)
            with patch(
                "ai_engine.agents.evidence.get_llm",
                side_effect=ValueError("GROQ_API_KEY is not set"),
            ), patch(
                "ai_engine.agents.assumption.get_llm",
                side_effect=ValueError("GROQ_API_KEY is not set"),
            ):
                r = client.post(
                    f"/api/v2/studies/{study_id}/information-gate",
                    json={"choice": choice},
                    headers=headers,
                )
            assert r.status_code == 200, r.text
            body = r.json()
            outcomes[choice] = (
                body["phase"],
                body["gate_choice"],
                body["claims_count"],
                body.get("assumptions_count", 0),
            )
        assert outcomes["manual"][0] == "NEEDS_INFORMATION"
        assert outcomes["research"][0] == "EVIDENCE_REVIEW"
        assert outcomes["provisional"][0] == "ASSUMPTIONS_REVIEW"
        assert outcomes["research"][2] == 0
        assert outcomes["provisional"][2] == 0
        assert outcomes["provisional"][3] >= 1
        assert len({outcomes[c][0] for c in outcomes}) == 3
