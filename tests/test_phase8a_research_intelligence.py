"""Phase 8A — Research Intelligence MVP tests (Knowledge-first before AI assumption)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ai_engine.models.study_state import Claim, ProjectProfile, StudyState
from ai_engine.research.planner import (
    BLOCKED_SOURCES,
    PHASE8A_LIVE_SOURCES,
    build_research_plan,
    classify_gap,
    extract_gaps_from_state,
)
from ai_engine.research.schemas import ResearchClaim, ResearchResult
from ai_engine.research.service import execute_research, research_gaps
from ai_engine.research.nodes.research import (
    merge_evidence_claims,
    run_research,
    validate_research_before_assumption,
)
from ai_engine.research.nodes.evidence_validator import run_evidence_validator
from ai_engine.agents.evidence import (
    _merge_claims_preserving_official,
    _provisional_estimate_claims,
    _research_has_run,
)


class TestResearchPlanner:
    def test_classify_inflation_to_gastat(self):
        assert "gastat" in classify_gap("Saudi inflation CPI")

    def test_classify_fdi_to_misa(self):
        assert "misa" in classify_gap("FDI investment inflows")

    def test_classify_sme_to_blocked_monshaat(self):
        keys = classify_gap("SME monshaat small business")
        assert "monshaat" in keys
        assert "monshaat" in BLOCKED_SOURCES

    def test_build_plan_marks_monshaat_blocked(self):
        plan = build_research_plan(
            study_id="s1",
            gaps=["SME monshaat ecosystem", "Saudi inflation"],
        )
        by_key = {s.source_key: s for s in plan.sources}
        assert by_key["monshaat"].blocked is True
        assert by_key["monshaat"].block_reason == "BLOCKED_EXTERNAL_REACHABILITY"
        assert by_key["gastat"].blocked is False
        assert set(PHASE8A_LIVE_SOURCES) == {"gastat", "misa"}

    def test_extract_gaps_includes_official_indicators(self):
        state = StudyState(
            study_id="s1",
            project_id="p1",
            user_id="1",
            profile=ProjectProfile(sector="logistics", archetype="services"),
        )
        gaps = extract_gaps_from_state(state)
        assert any(
            any(k in g.lower() for k in ("statistic", "inflation", "gdp", "labor"))
            for g in gaps
        )
        assert any(any(k in g.lower() for k in ("investment", "fdi")) for g in gaps)


class TestResearchService:
    def test_knowledge_hit_skips_live_for_that_source(self):
        plan = build_research_plan(study_id="s1", gaps=["Saudi inflation"])
        with patch(
            "ai_engine.research.service._knowledge_retrieve",
            return_value=[
                ResearchClaim(
                    statement="Knowledge CPI hit",
                    source_type="official",
                    source_key="gastat",
                    from_knowledge=True,
                    confidence=0.8,
                )
            ],
        ), patch(
            "ai_engine.research.service._live_fetch",
            side_effect=AssertionError("live must not run after knowledge hit"),
        ):
            result = execute_research(plan, owner_id=1, db=MagicMock())
        assert result.knowledge_hits >= 1
        assert result.live_fetches == 0
        assert any(c.from_knowledge for c in result.claims)

    def test_live_mcp_fetch_produces_official_claims(self):
        fake_status = {
            "ok": True,
            "status": "healthy",
            "detail": "ok",
            "connector_id": "live.gastat",
        }
        fake_fetch = {
            "ok": True,
            "documents": [
                {
                    "title": "CPI",
                    "content_preview": "CPI 1.6% YoY",
                    "url": "https://gastat.gov.sa/cpi",
                    "canonical_url": "https://gastat.gov.sa/cpi",
                }
            ],
        }
        with patch(
            "backend.app.integrations.mcp.boundary.source_status_payload",
            return_value=fake_status,
        ), patch(
            "backend.app.integrations.mcp.boundary.source_fetch_payload",
            return_value=fake_fetch,
        ), patch(
            "backend.app.integrations.mcp.boundary.connector_for_key",
            side_effect=Exception("skip ingest"),
        ):
            result = research_gaps(study_id="s1", gaps=["Saudi inflation CPI"])
        assert result.status in {"complete", "partial"}
        assert result.live_fetches >= 1
        assert result.claims
        assert result.claims[0].source_type == "official"


class TestBlockedMonshaat:
    def test_monshaat_blocked_does_not_raise(self):
        plan = build_research_plan(study_id="s1", gaps=["monshaat SME only"])
        assert all(s.blocked for s in plan.sources)
        result = execute_research(plan)
        assert "monshaat" in result.blocked_sources
        assert result.status in {"blocked", "partial", "failed"}


class TestTrustGate:
    def test_merge_drops_assumptions_when_official_present(self):
        existing = [
            Claim(statement="guess revenue", source_type="ai_assumption", confidence=0.4),
            Claim(statement="user note", source_type="user_input", confidence=0.9),
        ]
        research = [
            ResearchClaim(
                statement="Official CPI 1.6%",
                source_type="official",
                confidence=0.9,
                source_url="https://gastat.gov.sa",
            )
        ]
        merged = merge_evidence_claims(existing, research)
        types = {c.source_type for c in merged}
        assert "official" in types
        assert "ai_assumption" not in types
        assert "user_input" in types

    def test_evidence_agent_preserves_official(self):
        prior = [Claim(statement="Official FDI", source_type="official", confidence=0.9)]
        incoming = [
            Claim(statement="AI guess", source_type="ai_assumption", confidence=0.9)
        ]
        merged = _merge_claims_preserving_official(prior, incoming)
        assert len(merged) == 1
        assert merged[0].source_type == "official"

    def test_assumption_only_after_research(self):
        state = StudyState(
            study_id="s1",
            project_id="p1",
            user_id="1",
            profile_confirmed=True,
            profile=ProjectProfile(sector="retail"),
        )
        assert _research_has_run(state) is False
        assert _provisional_estimate_claims(state) == []
        state.research_status = "partial"
        claims = _provisional_estimate_claims(state)
        assert claims
        assert all(c.source_type == "ai_assumption" for c in claims)
        assert all(c.confidence <= 0.45 for c in claims)

    def test_validate_research_before_assumption_gate(self):
        gate = validate_research_before_assumption(None)
        assert gate["research_ran"] is False
        assert gate["allow_ai_assumption"] is False


class TestOrchestratorWiring:
    def test_evidence_review_routes_to_research(self):
        from ai_engine.orchestrator import route_by_phase, PHASE_TRANSITIONS, build_graph

        assert PHASE_TRANSITIONS["EVIDENCE_REVIEW"] == "research"
        state = StudyState(
            study_id="s1", project_id="p1", user_id="1", phase="EVIDENCE_REVIEW"
        )
        assert route_by_phase(state) == "research"
        graph = build_graph()
        assert "research" in graph.nodes
        assert "evidence" in graph.nodes


class TestResearchNodeAndValidator:
    def test_run_research_with_mocked_service(self):
        state = StudyState(
            study_id="s1",
            project_id="p1",
            user_id="1",
            phase="EVIDENCE_REVIEW",
            profile=ProjectProfile(sector="logistics"),
            claims=[
                Claim(statement="old guess", source_type="ai_assumption", confidence=0.4)
            ],
        )
        fake = ResearchResult(
            plan=build_research_plan(study_id="s1", gaps=["inflation"]),
            status="complete",
            claims=[
                ResearchClaim(
                    statement="Official CPI",
                    source_type="official",
                    confidence=0.9,
                    source_url="https://gastat.gov.sa",
                )
            ],
            live_fetches=1,
        )
        with patch(
            "ai_engine.research.nodes.research.research_gaps", return_value=fake
        ), patch(
            "ai_engine.research.nodes.research._open_db", return_value=None
        ):
            out = run_research(state)
        assert out.research_status == "complete"
        assert out.research_context
        assert any(c.source_type == "official" for c in out.claims)
        assert not any(c.source_type == "ai_assumption" for c in out.claims)

    def test_evidence_validator_flags_assumption_without_research(self):
        state = {
            "study_id": "s1",
            "claims": [
                {"statement": "guess", "source_type": "ai_assumption", "confidence": 0.4}
            ],
            "research_context": {},
            "research_status": None,
        }
        out = run_evidence_validator(state)
        validation = out["research_context"]["evidence_validation"]
        assert validation["ok"] is False
        assert "ai_assumption_without_prior_research" in validation["violations"]
