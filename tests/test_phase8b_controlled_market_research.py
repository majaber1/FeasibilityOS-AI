"""Phase 8B — Controlled Market Research Intelligence tests."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from ai_engine.models.study_state import Claim, ProjectProfile, StudyState
from ai_engine.orchestrator import PHASE_TRANSITIONS, build_graph
from ai_engine.research.market.competitor import research_competitors
from ai_engine.research.market.market_signal import research_market_signals
from ai_engine.research.market.planner import (
    build_market_plan,
    classify_research_types,
    select_sources,
)
from ai_engine.research.market.pricing_signal import research_pricing_signals
from ai_engine.research.market.regulation import (
    REGULATION_PLACEHOLDERS,
    build_regulation_framework,
)
from ai_engine.research.market.schemas import LIVE_MARKET_SOURCES
from ai_engine.research.market.service import (
    clear_market_cache,
    execute_market_research,
    market_result_to_research_claims,
)
from ai_engine.research.nodes.research import merge_evidence_claims
from ai_engine.research.planner import build_research_plan
from ai_engine.research.schemas import ResearchClaim
from ai_engine.research.service import execute_research


class TestMarketPlanner:
    def test_classify_competitor_and_pricing(self):
        types = classify_research_types("Who are competitors and pricing fees?")
        assert "COMPETITOR" in types
        assert "PRICING" in types

    def test_select_sources_only_governed(self):
        selected, placeholders = select_sources(
            ["SECTOR_SIGNAL", "REGULATION", "COMPETITOR"]
        )
        assert set(selected).issubset(set(LIVE_MARKET_SOURCES))
        assert "monshaat" not in selected
        assert set(placeholders).issubset({"sama", "zatca", "nca"})

    def test_build_plan_default_types(self):
        plan = build_market_plan(study_id="s1", business_idea="Riyadh retail SME")
        assert plan.research_types
        assert all(s in LIVE_MARKET_SOURCES for s in plan.selected_sources)


class TestCompetitorIntelligence:
    def test_no_evidence_returns_not_found(self):
        comps, status = research_competitors(
            business_idea="coffee shop",
            sector="retail",
            evidence_items=[],
        )
        assert status == "NOT_FOUND"
        assert comps[0].status == "NOT_FOUND"
        assert comps[0].name == ""

    def test_never_invents_fake_companies(self):
        comps, status = research_competitors(
            business_idea="Uber-like mobility in Riyadh",
            sector="services",
            evidence_items=[],
        )
        names = [c.name for c in comps if c.name]
        assert names == []
        assert status == "NOT_FOUND"

    def test_sourced_competitor_verified(self):
        comps, status = research_competitors(
            business_idea="retail",
            sector="retail",
            evidence_items=[
                {
                    "competitor_name": "Acme Retail Co",
                    "statement": "Competitor Acme Retail Co operates in Riyadh.",
                    "source_url": "https://www.stats.gov.sa/en/w/news/180",
                    "source_key": "gastat",
                    "document_id": "d1",
                    "source_type": "document",
                }
            ],
        )
        assert status == "VERIFIED"
        assert any(c.name == "Acme Retail Co" and c.status == "VERIFIED" for c in comps)

    def test_mention_without_source_not_verified(self):
        comps, status = research_competitors(
            business_idea="retail",
            sector="retail",
            evidence_items=[
                {
                    "competitor_name": "NoSource Mart",
                    "statement": "NoSource Mart is a competitor",
                }
            ],
        )
        assert status == "NOT_VERIFIED"
        assert comps[0].status == "NOT_VERIFIED"


class TestMarketSignals:
    def test_extract_cpi_from_official_evidence(self):
        signals, conflicts, status = research_market_signals(
            [
                {
                    "statement": "Inflation CPI reached 1.6% in March 2025",
                    "source_type": "official",
                    "source_url": "https://www.stats.gov.sa/en/w/news/180",
                    "source_key": "gastat",
                    "document_id": "g1",
                }
            ]
        )
        assert status == "VERIFIED"
        assert conflicts == []
        assert any(s.metric == "cpi_inflation" and s.value == 1.6 for s in signals)

    def test_missing_values_not_estimated(self):
        signals, conflicts, status = research_market_signals(
            [
                {
                    "statement": "Market is growing strongly this year",
                    "source_type": "official",
                    "source_url": "https://www.stats.gov.sa/en",
                    "source_key": "gastat",
                    "document_id": "g2",
                }
            ]
        )
        assert status == "NOT_FOUND"
        assert signals == []

    def test_conflict_detected(self):
        signals, conflicts, status = research_market_signals(
            [
                {
                    "statement": "CPI inflation was 1.6% in March 2025",
                    "source_type": "official",
                    "source_url": "https://www.stats.gov.sa/a",
                    "source_key": "gastat",
                    "document_id": "d1",
                },
                {
                    "statement": "CPI inflation was 2.1% in March 2025",
                    "source_type": "official",
                    "source_url": "https://www.stats.gov.sa/b",
                    "source_key": "gastat",
                    "document_id": "d2",
                },
            ]
        )
        assert status == "CONFLICT"
        assert conflicts
        assert all(s.status == "CONFLICT" for s in signals)


class TestPricingSignals:
    def test_no_llm_guessed_prices(self):
        signals, status = research_pricing_signals([])
        assert status == "NOT_FOUND"
        assert signals[0].price is None

    def test_sourced_price_verified(self):
        signals, status = research_pricing_signals(
            [
                {
                    "statement": "Subscription fee price is SAR 99 per month",
                    "source_url": "https://misa.gov.sa/activities/investment-development/",
                    "source_key": "misa",
                    "document_id": "p1",
                    "source_type": "document",
                }
            ]
        )
        assert status == "VERIFIED"
        assert signals[0].price == 99
        assert signals[0].currency == "SAR"

    def test_ai_assumption_prices_rejected(self):
        signals, status = research_pricing_signals(
            [
                {
                    "statement": "Typical price SAR 50",
                    "source_type": "ai_assumption",
                    "origin": "ai_assumption",
                    "source_url": "https://example.com",
                }
            ]
        )
        assert status == "NOT_FOUND"


class TestRegulationFramework:
    def test_placeholders_only_no_new_connectors(self):
        regs, status = build_regulation_framework(sector="retail")
        assert status == "PARTIAL"
        keys = {r.source_key for r in regs}
        assert keys == set(REGULATION_PLACEHOLDERS)
        assert all(r.status == "PARTIAL" for r in regs)


class TestMarketServiceScenarios:
    def setup_method(self):
        clear_market_cache()

    def test_scenario_a_retail_sme(self):
        evidence = [
            {
                "statement": "Inflation CPI reached 1.6% in March 2025",
                "source_type": "official",
                "source_url": "https://www.stats.gov.sa/en/w/news/180",
                "source_key": "gastat",
                "document_id": "g1",
            }
        ]
        result = execute_market_research(
            study_id="retail-a",
            business_idea="Riyadh retail SME grocery",
            sector="retail",
            gaps=["competitors", "market indicators", "pricing"],
            evidence_items=evidence,
            use_cache=False,
        )
        assert (
            "gastat" in result.plan.selected_sources
            or "misa" in result.plan.selected_sources
        )
        assert any(c.status == "NOT_FOUND" for c in result.competitors)
        assert any(s.metric == "cpi_inflation" for s in result.market_signals)
        assert result.insights
        claims = market_result_to_research_claims(result)
        assert all(c.source_type in {"official", "document"} for c in claims)
        assert all(c.origin == "market_research" for c in claims)

    def test_scenario_b_investment_misa(self):
        evidence = [
            {
                "statement": "FDI foreign direct investment inflows rose 12.5% in 2024",
                "source_type": "official",
                "source_url": "https://misa.gov.sa/activities/national-investment-strategy/",
                "source_key": "misa",
                "document_id": "m1",
            }
        ]
        result = execute_market_research(
            study_id="invest-b",
            business_idea="FDI manufacturing plant",
            sector="industrial",
            gaps=["investment climate FDI"],
            evidence_items=evidence,
            use_cache=False,
        )
        assert "misa" in result.plan.selected_sources or any(
            s.source_key == "misa" for s in result.market_signals
        )
        assert any(s.metric == "fdi_inflow" for s in result.market_signals)

    def test_scenario_c_no_evidence(self):
        result = execute_market_research(
            study_id="empty-c",
            business_idea="unknown niche",
            sector="other",
            gaps=["competitors", "pricing", "market size"],
            evidence_items=[],
            use_cache=False,
        )
        assert result.status in {"NOT_FOUND", "PARTIAL"}
        claims = market_result_to_research_claims(result)
        assert claims == []

    def test_scenario_d_conflicting_evidence(self):
        result = execute_market_research(
            study_id="conflict-d",
            gaps=["inflation"],
            evidence_items=[
                {
                    "statement": "CPI inflation was 1.6% in March 2025",
                    "source_type": "official",
                    "source_url": "https://www.stats.gov.sa/a",
                    "source_key": "gastat",
                    "document_id": "d1",
                },
                {
                    "statement": "CPI inflation was 2.1% in March 2025",
                    "source_type": "official",
                    "source_url": "https://www.stats.gov.sa/b",
                    "source_key": "gastat",
                    "document_id": "d2",
                },
            ],
            use_cache=False,
        )
        assert result.status == "CONFLICT"
        assert result.conflicts
        assert any(i.status == "CONFLICT" for i in result.insights)


class TestAiTrustAudit:
    def test_competitors_question_never_invents(self):
        result = execute_market_research(
            study_id="trust-comp",
            business_idea="Who are the competitors for a Riyadh cafe?",
            gaps=["competitors"],
            evidence_items=[],
            use_cache=False,
        )
        named = [c.name for c in result.competitors if c.name]
        assert named == []

    def test_market_size_unknown_without_evidence(self):
        result = execute_market_research(
            study_id="trust-size",
            gaps=["market size TAM"],
            evidence_items=[],
            use_cache=False,
        )
        assert result.market_signals == []
        claims = market_result_to_research_claims(result)
        assert not any(
            "TAM" in c.statement and c.source_type == "ai_assumption" for c in claims
        )


class TestKnowledgeIntegrationAndTrust:
    def test_official_beats_ai_assumption_after_market_merge(self):
        existing = [
            Claim(
                statement="Generic AI market estimate 12%",
                source_type="ai_assumption",
                confidence=0.9,
                origin="ai_assumption",
            )
        ]
        research = [
            ResearchClaim(
                statement="CPI inflation 1.6% (official)",
                source_type="official",
                source_url="https://www.stats.gov.sa/en/w/news/180",
                source_key="gastat",
                origin="market_research",
                confidence=0.85,
            )
        ]
        merged = merge_evidence_claims(existing, research)
        assert any(c.source_type == "official" for c in merged)
        assert not any(c.source_type == "ai_assumption" for c in merged)

    def test_execute_research_attaches_market_payload(self):
        plan = build_research_plan(
            study_id="wire1", gaps=["Saudi inflation CPI consumer price"]
        )
        with patch("ai_engine.research.service._knowledge_retrieve", return_value=[]):
            with patch(
                "ai_engine.research.service._live_fetch",
                return_value=(
                    [
                        ResearchClaim(
                            statement="Inflation CPI reached 1.6% in March 2025",
                            source_type="official",
                            source_url="https://www.stats.gov.sa/en/w/news/180",
                            source_key="gastat",
                            document_id="live-1",
                            origin="research",
                        )
                    ],
                    {"source_key": "gastat", "outcome": "ok", "path": "mcp_live"},
                    [],
                ),
            ):
                result = execute_research(plan)
        assert result.market_research is not None
        assert result.market_research.get("status")
        assert any(a.get("source_key") == "market_research" for a in result.attempts)


class TestSecurityControls:
    def test_market_module_does_not_fetch_arbitrary_urls(self):
        with patch("httpx.Client") as client:
            execute_market_research(
                study_id="sec1",
                gaps=["competitors pricing"],
                evidence_items=[
                    {
                        "competitor_name": "Safe Co",
                        "statement": "Competitor Safe Co",
                        "source_url": "https://evil.example/ssrf",
                        "document_id": "u1",
                        "source_type": "document",
                    }
                ],
                use_cache=False,
            )
            client.assert_not_called()

    def test_domain_allowlist_helpers_still_reject_private(self):
        from backend.app.integrations.research.security import (
            UrlSecurityError,
            validate_url,
        )

        with pytest.raises(UrlSecurityError):
            validate_url(
                "http://127.0.0.1/secret",
                allowed_domains=("stats.gov.sa",),
            )


class TestPerformanceCache:
    def test_repeated_research_uses_cache(self):
        clear_market_cache()
        evidence = [
            {
                "statement": "Inflation CPI reached 1.6% in March 2025",
                "source_type": "official",
                "source_url": "https://www.stats.gov.sa/en/w/news/180",
                "source_key": "gastat",
                "document_id": "g1",
            }
        ]
        t0 = time.perf_counter()
        a = execute_market_research(
            study_id="perf1", gaps=["inflation"], evidence_items=evidence, use_cache=True
        )
        t1 = time.perf_counter()
        b = execute_market_research(
            study_id="perf1", gaps=["inflation"], evidence_items=evidence, use_cache=True
        )
        t2 = time.perf_counter()
        assert b.cache_hits >= 1
        assert a.status == b.status
        assert (t2 - t1) <= max(0.25, (t1 - t0) * 3)


class TestOrchestratorSafety:
    def test_research_still_before_evidence_only(self):
        assert PHASE_TRANSITIONS["EVIDENCE_REVIEW"] == "research"
        assert PHASE_TRANSITIONS["READY_FOR_ANALYSIS"] == "financial"
        assert PHASE_TRANSITIONS["ANALYZED"] == "risk"
        assert PHASE_TRANSITIONS["DECISION_READY"] == "decision"
        nodes = set(build_graph().nodes.keys())
        assert "research" in nodes
        assert {"financial", "risk", "decision", "evidence"}.issubset(nodes)

    def test_study_state_has_market_context_field(self):
        state = StudyState(
            study_id="m1",
            project_id="p1",
            user_id="u1",
            profile=ProjectProfile(sector="retail"),
            market_research_context={"status": "NOT_FOUND", "insights": []},
        )
        assert state.market_research_context["status"] == "NOT_FOUND"


class TestUserAcceptancePayload:
    def test_insights_expose_source_url_confidence(self):
        result = execute_market_research(
            study_id="ux1",
            gaps=["inflation"],
            evidence_items=[
                {
                    "statement": "Inflation CPI reached 1.6% in March 2025",
                    "source_type": "official",
                    "source_url": "https://www.stats.gov.sa/en/w/news/180",
                    "source_key": "gastat",
                    "document_id": "g1",
                }
            ],
            use_cache=False,
        )
        public = result.to_public_dict()
        assert public["status"]
        assert public["plan"]["selected_sources"]
        assert public["insights"]
        hit = public["insights"][0]
        assert "insight" in hit
        assert "evidence_reference" in hit
        assert "confidence" in hit
        assert hit.get("official_url") or hit.get("source")
