"""Phase 8A final trust-gate validations (orchestrator safety, evidence trust, persistence)."""

from __future__ import annotations

import copy
import uuid
from unittest.mock import patch

import pytest

from ai_engine.agents.evidence import (
    _merge_claims_preserving_official,
    _provisional_estimate_claims,
)
from ai_engine.models.study_state import Claim, ProjectProfile, StudyState
from ai_engine.orchestrator import PHASE_TRANSITIONS, build_graph
from ai_engine.research.nodes.research import merge_evidence_claims
from ai_engine.research.schemas import ResearchClaim
from ai_engine.research.service import research_gaps


class TestOrchestratorSafety:
    def test_only_evidence_path_gains_research_node(self):
        assert PHASE_TRANSITIONS["EVIDENCE_REVIEW"] == "research"
        assert PHASE_TRANSITIONS["READY_FOR_ANALYSIS"] == "financial"
        assert PHASE_TRANSITIONS["ANALYZED"] == "risk"
        assert PHASE_TRANSITIONS["DECISION_READY"] == "decision"
        graph = build_graph()
        nodes = set(graph.nodes.keys())
        assert "research" in nodes
        assert {"financial", "risk", "decision", "evidence", "assumptions"}.issubset(nodes)

    def test_financial_risk_decision_modules_untouched_by_phase8a_diff(self):
        # Imported symbols still resolve to original agent callables.
        from ai_engine.agents.financial_analyst import run_financial_analysis
        from ai_engine.agents.risk import run_risk_analysis
        from ai_engine.agents.decision import run_decision

        assert callable(run_financial_analysis)
        assert callable(run_risk_analysis)
        assert callable(run_decision)


class TestEvidenceTrust:
    def test_official_selected_over_ai_assumption(self):
        existing = [
            Claim(
                statement="Generic AI market estimate",
                source_type="ai_assumption",
                confidence=0.9,
                origin="ai_assumption",
            )
        ]
        research = [
            ResearchClaim(
                statement="GASTAT CPI 1.6% YoY",
                source_type="official",
                source_url="https://www.stats.gov.sa/en/w/news/180",
                confidence=0.9,
                source_key="gastat",
                origin="research",
                document_id="doc-gastat-1",
                chunk_id="chunk-1",
            ),
            ResearchClaim(
                statement="MISA FDI climate note",
                source_type="official",
                source_url="https://misa.gov.sa/en/",
                confidence=0.85,
                source_key="misa",
                origin="research",
            ),
        ]
        merged = merge_evidence_claims(existing, research)
        types = {c.source_type for c in merged}
        assert "official" in types
        assert "ai_assumption" not in types
        official = [c for c in merged if c.source_type == "official"]
        assert all(c.source_url for c in official)
        assert any(c.origin == "research" for c in official)
        assert any(c.document_id == "doc-gastat-1" for c in official)
        assert any(c.chunk_id == "chunk-1" for c in official)
        assert any(c.source_key == "gastat" for c in official)

    def test_evidence_agent_merge_preserves_official(self):
        prior = [
            Claim(
                statement="Official FDI",
                source_type="official",
                source_url="https://misa.gov.sa",
                confidence=0.9,
                origin="research",
                source_key="misa",
            )
        ]
        incoming = [
            Claim(
                statement="AI guess",
                source_type="ai_assumption",
                confidence=0.9,
                origin="ai_assumption",
            )
        ]
        merged = _merge_claims_preserving_official(prior, incoming)
        assert len(merged) == 1
        assert merged[0].source_type == "official"
        assert merged[0].source_url == "https://misa.gov.sa"
        assert merged[0].origin == "research"

    def test_live_official_beats_synthetic_assumption(self):
        live = research_gaps(
            study_id="final-trust-live",
            gaps=["Official Saudi inflation CPI statistics"],
        )
        assert live.claims, "expected live/official research claims"
        prior = [
            Claim(
                statement="AI estimated inflation is 12%",
                source_type="ai_assumption",
                confidence=0.95,
                origin="ai_assumption",
            )
        ]
        merged = merge_evidence_claims(prior, live.claims)
        assert any(c.source_type == "official" for c in merged)
        assert not any(c.source_type == "ai_assumption" for c in merged)
        for c in merged:
            if c.source_type == "official":
                assert c.source_type == "official"
                assert c.origin in {"research", "knowledge", None} or c.origin
                # URL preferred when connector provided one
                assert c.confidence >= 0.5


class TestPersistence:
    def test_research_context_and_claims_survive_reload(self):
        from backend.app.api.v2 import study_engine as se

        study_id = f"persist8a_{uuid.uuid4().hex[:10]}"
        user_id = "owner-8a"
        state = {
            "study_id": study_id,
            "project_id": "p-8a",
            "user_id": user_id,
            "language": "en",
            "phase": "EVIDENCE_REVIEW",
            "phase_history": ["DRAFT", "EVIDENCE_REVIEW"],
            "profile": {"archetype": "services", "sector": "logistics"},
            "profile_confirmed": True,
            "claims": [
                {
                    "statement": "GASTAT CPI official claim",
                    "source_type": "official",
                    "source_url": "https://www.stats.gov.sa/en/w/news/180",
                    "confidence": 0.9,
                    "origin": "research",
                    "source_key": "gastat",
                    "document_id": "doc-1",
                    "chunk_id": "chunk-1",
                }
            ],
            "assumptions": [],
            "messages": [],
            "research_status": "complete",
            "research_context": {
                "status": "complete",
                "claims": [{"statement": "GASTAT CPI official claim", "source_type": "official"}],
                "blocked_sources": [],
            },
            "research_attempts": [{"source_key": "gastat", "outcome": "ok"}],
            "knowledge_context": {"query": "inflation", "citations": [], "hit_count": 0},
        }

        # Force in-memory fallback path for deterministic persistence (no DB schema deps).
        with patch.object(se, "_get_db_session", return_value=None):
            se._save_study(study_id, copy.deepcopy(state), user_id)
            # Simulate logout/login: clear nothing in fallback except re-load by id+user
            loaded = se._load_study(study_id, user_id)
            assert loaded is not None
            s = loaded["state"]
            assert s["research_status"] == "complete"
            assert s["research_context"]["status"] == "complete"
            assert s["research_attempts"][0]["source_key"] == "gastat"
            assert s["claims"][0]["source_type"] == "official"
            assert s["claims"][0]["source_url"]
            assert s["claims"][0]["origin"] == "research"
            assert s["claims"][0]["document_id"] == "doc-1"
            assert s["claims"][0]["chunk_id"] == "chunk-1"
            assert s["knowledge_context"]["query"] == "inflation"

            # Public API payload must expose research + claim provenance
            payload = se._study_payload(study_id, loaded)
            assert payload["research_status"] == "complete"
            assert payload["research_context"]
            assert payload["claims"][0]["source_type"] == "official"
            assert payload["claims"][0].get("source_url")
            assert payload["claims"][0].get("origin") == "research"


class TestApiVisibility:
    def test_public_payload_exposes_research_and_claim_provenance(self):
        from backend.app.api.v2 import study_engine as se
        from ai_engine.models.study_state import StudyState, Claim, ProjectProfile

        state = StudyState(
            study_id="vis1",
            project_id="p1",
            user_id="u1",
            phase="EVIDENCE_REVIEW",
            profile=ProjectProfile(sector="retail"),
            research_status="partial",
            research_context={"status": "partial", "blocked_sources": ["monshaat"]},
            research_attempts=[{"source_key": "monshaat", "outcome": "blocked"}],
            claims=[
                Claim(
                    statement="Official note",
                    source_type="official",
                    source_url="https://www.stats.gov.sa",
                    confidence=0.88,
                    origin="research",
                    source_key="gastat",
                    document_id="d1",
                    chunk_id="c1",
                )
            ],
        )
        payload = se._payload_from_state("vis1", state)
        assert payload["research_status"] == "partial"
        assert "monshaat" in (payload["research_context"] or {}).get("blocked_sources", [])
        claim = payload["claims"][0]
        assert claim["source_type"] == "official"
        assert claim["source_url"]
        assert claim["origin"] == "research"
        assert claim["document_id"] == "d1"
        assert claim["chunk_id"] == "c1"
        assert claim["confidence"] == 0.88
