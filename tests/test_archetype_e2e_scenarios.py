"""Deterministic end-to-end path for Uber / Residential / Data Center archetypes.

LLM calls are mocked so CI does not require Groq. Verifies:
- archetype-specific assumptions
- no SaaS leakage on non-SaaS projects
- phases reach Financial → Risk → Decision → Report
"""
from __future__ import annotations

import json

import pytest

from ai_engine.models.study_state import StudyState, ProjectProfile, Claim, Assumption
from ai_engine.agents import discovery as discovery_mod
from ai_engine.agents import evidence as evidence_mod
from ai_engine.agents import assumption as assumption_mod
from ai_engine.agents import financial_analyst as financial_mod
from ai_engine.agents import risk as risk_mod
from ai_engine.agents import decision as decision_mod
from ai_engine.archetypes import assert_no_saas_leakage, schema_keys_for


SCENARIOS = {
    "uber": {
        "text": "Uber-like ride hailing platform in Riyadh with drivers, trips and take rate",
        "archetype": "services",
        "answers": {
            "take_rate": 20,
            "monthly_trips": 500000,
            "drivers": 8000,
            "driver_cac": 400,
            "avg_trip_value": 35,
            "monthly_fixed_opex": 1200000,
            "initial_investment": 8000000,
        },
        "must_have": {"take_rate", "monthly_trips", "drivers", "driver_cac"},
        "must_not": {"cac", "arr", "mrr", "churn"},
    },
    "residential": {
        "text": "Residential compound 400 villas near Riyadh with land cost and construction BOQ",
        "archetype": "real_estate",
        "answers": {
            "land_cost": 80000000,
            "construction_boq": 220000000,
            "units": 400,
            "selling_price": 1800000,
            "absorption_rate": 80,
            "financing": "Mixed (equity + debt)",
        },
        "must_have": {"land_cost", "construction_boq", "units", "selling_price"},
        "must_not": {"cac", "arr", "mrr", "churn"},
    },
    "datacenter": {
        "text": "40MW hyperscale data center in Dammam with racks, PUE and occupancy pricing",
        "archetype": "data_center",
        "answers": {
            "mw_capacity": 40,
            "rack_count": 4000,
            "pue": 1.35,
            "power_cost": 0.18,
            "occupancy": 55,
            "pricing_per_kw": 450,
        },
        "must_have": {"mw_capacity", "rack_count", "pue", "occupancy"},
        "must_not": {"cac", "arr", "mrr", "churn"},
    },
}


class _Resp:
    def __init__(self, content: str):
        self.content = content


def _fake_llm(payload: dict):
    class LLM:
        def invoke(self, messages):
            return _Resp("```json\n" + json.dumps(payload) + "\n```")

    return LLM()


def _seed_state(text: str) -> StudyState:
    from langchain_core.messages import HumanMessage

    return StudyState(
        study_id="study_test",
        project_id="proj_test",
        user_id="user_test",
        language="en",
        phase="DRAFT",
        messages=[HumanMessage(content=text)],
    )


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_scenario_reaches_report_without_saas_leakage(name, monkeypatch):
    cfg = SCENARIOS[name]
    arch = cfg["archetype"]

    monkeypatch.setattr(
        discovery_mod,
        "get_llm",
        lambda task="classification": _fake_llm(
            {
                "archetype": arch,
                "sector": cfg["text"][:40],
                "stage": "idea",
                "decision_goal": "feasibility",
                "missing_information": [],
                "recommended_model": f"{arch}_v1",
            }
        ),
    )

    state = _seed_state(cfg["text"])
    state = discovery_mod.run_discovery(state)
    assert state.profile is not None
    assert state.profile.archetype == arch
    assert state.phase == "ARCHETYPE_CLASSIFICATION"

    # Confirm archetype + structured answers
    state.profile.archetype_confirmed = True
    state.structured_answers = dict(cfg["answers"])
    state.discovery_questions = [
        {**q, "answered": True, "answer": cfg["answers"].get(q["id"])}
        for q in (state.discovery_questions or [])
    ]
    state.profile_confirmed = True
    state.phase = "EVIDENCE_REVIEW"

    monkeypatch.setattr(
        evidence_mod,
        "get_llm",
        lambda task="extraction": _fake_llm(
            {
                "claims": [
                    {
                        "statement": f"Seed evidence for {arch}",
                        "source_type": "ai_assumption",
                        "confidence": 0.5,
                        "source_url": None,
                    }
                ],
                "gaps": [],
                "evidence_sufficient": True,
            }
        ),
    )
    state = evidence_mod.run_evidence(state)
    assert state.claims
    # Evidence must not introduce SaaS CAC language for non-SaaS
    if arch != "saas_digital":
        blob = " ".join(c.statement.lower() for c in state.claims)
        assert "year-1 cac" not in blob
        assert "arr/mrr" not in blob

    state.evidence_approved = True
    state.phase = "ASSUMPTIONS_REVIEW"

    # Build LLM payload using only schema keys (+ intentional SaaS bleed to ensure filter)
    schema_keys = sorted(schema_keys_for(arch))
    llm_assumptions = [
        {
            "key": k,
            "value": str(cfg["answers"].get(k, "1")),
            "source": "AI Estimated Assumption" if k not in cfg["answers"] else "user",
            "confidence": "confirmed" if k in cfg["answers"] else "low",
            "ai_estimated": k not in cfg["answers"],
            "low": "1",
            "base": str(cfg["answers"].get(k, "1")),
            "high": "2",
        }
        for k in schema_keys
    ] + [
        {"key": "cac", "value": "99", "source": "AI Estimated Assumption", "confidence": "low", "ai_estimated": True},
        {"key": "arr", "value": "99", "source": "AI Estimated Assumption", "confidence": "low", "ai_estimated": True},
    ]
    monkeypatch.setattr(
        assumption_mod,
        "get_llm",
        lambda task="assumptions": _fake_llm({"assumptions": llm_assumptions, "assumptions_complete": True}),
    )
    state = assumption_mod.run_assumptions(state)
    keys = {a.key for a in state.assumptions}
    assert cfg["must_have"].issubset(keys)
    assert keys.isdisjoint(cfg["must_not"])
    assert assert_no_saas_leakage(arch, keys) == []
    assert state.phase == "ASSUMPTIONS_REVIEW"
    assert state.assumptions_approved is False

    # Approve assumptions → financial
    state.assumptions_approved = True
    state.phase = "READY_FOR_ANALYSIS"

    def _fin_llm(task="general"):
        # Empty extraction JSON forces deterministic assumption-based path,
        # then explanation LLM fills narrative around computed numbers.
        if task == "extraction":
            return _fake_llm({})
        return _fake_llm(
            {
                "revenue_projections": [1, 2, 3],
                "cost_projections": [1, 1, 1],
                "capex": 1,
                "npv": 1,
                "irr": 0.2,
                "payback_months": 12,
                "breakeven_months": 12,
                "scenarios": {"base": {"npv": 1, "irr": 0.2}},
                "analysis_complete": True,
                "warnings": [],
            }
        )

    monkeypatch.setattr(financial_mod, "get_llm", _fin_llm)
    state = financial_mod.run_financial_analysis(state)
    assert state.phase == "ANALYZED"
    assert state.financial_results

    monkeypatch.setattr(
        risk_mod,
        "get_llm",
        lambda task="risk": _fake_llm(
            {
                "critical_risks": ["market risk"],
                "risk_score": 0.4,
                "mitigations": ["pilot"],
                "risk_assessment_complete": True,
            }
        ),
    )
    state = risk_mod.run_risk_analysis(state)
    assert state.phase == "DECISION_READY"

    monkeypatch.setattr(
        decision_mod,
        "get_llm",
        lambda task="decision": _fake_llm(
            {
                "verdict": "GO_WITH_CONDITIONS",
                "rationale": "Viable under base case with conditions",
                "conditions": ["Validate occupancy / absorption"],
                "key_risks": ["execution"],
            }
        ),
    )
    state = decision_mod.run_decision(state)
    assert state.phase in {"DECISION_READY", "REPORT_READY", "FUNDING_READY"}
    assert state.verdict in {"GO", "GO_WITH_CONDITIONS", "DEFER", "NO_GO", "INSUFFICIENT_EVIDENCE"}
    # Final anti-leakage gate
    assert assert_no_saas_leakage(arch, [a.key for a in state.assumptions]) == []
