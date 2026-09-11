"""Archetype classification + assumption schema anti-leakage tests."""
from __future__ import annotations

import pytest

from ai_engine.archetypes import (
    classify_archetype,
    normalize_archetype,
    schema_keys_for,
    assert_no_saas_leakage,
    questions_for_language,
    SAAS_LEAKAGE_KEYS,
)
from ai_engine.models.study_state import StudyState, ProjectProfile
from ai_engine.agents import assumption as assumption_mod


GOLDEN = [
    ("Uber ride hailing service marketplace in Riyadh with drivers and take rate", "services"),
    ("Cybersecurity consulting and managed security services company in Riyadh with retainers and utilization", "services"),
    ("Food manufacturing factory with production capacity and machinery", "industrial"),
    ("Residential compound 500 villas in Jeddah with land cost and BOQ", "real_estate"),
    ("50MW tier III data center in Dammam with racks and PUE", "data_center"),
]


@pytest.mark.parametrize("text,expected", GOLDEN)
def test_classify_golden_scenarios(text, expected):
    assert classify_archetype(text) == expected


def test_services_schema_uber_fields():
    keys = schema_keys_for("services")
    for required in ("take_rate", "monthly_trips", "drivers", "driver_cac"):
        assert required in keys
    assert assert_no_saas_leakage("services", keys) == []
    assert "cac" not in keys
    assert "arr" not in keys
    assert "churn" not in keys
    assert "mrr" not in keys


def test_real_estate_schema_fields():
    keys = schema_keys_for("real_estate")
    for required in ("land_cost", "construction_boq", "units", "selling_price", "absorption_rate", "financing"):
        assert required in keys
    assert assert_no_saas_leakage("real_estate", keys) == []


def test_data_center_schema_fields():
    keys = schema_keys_for("data_center")
    for required in ("mw_capacity", "rack_count", "pue", "occupancy", "pricing_per_kw"):
        assert required in keys
    assert assert_no_saas_leakage("data_center", keys) == []


@pytest.mark.parametrize(
    "archetype",
    ["real_estate", "data_center", "industrial", "retail", "services", "other"],
)
def test_no_saas_leakage_in_non_saas_schemas(archetype):
    keys = schema_keys_for(archetype)
    assert assert_no_saas_leakage(archetype, keys) == []
    banned = {k.lower() for k in SAAS_LEAKAGE_KEYS}
    assert not (set(keys) & banned)


def test_saas_schema_includes_cac_arr_churn():
    keys = schema_keys_for("saas_digital")
    for k in ("cac", "arr", "churn", "mrr", "pricing", "target_customers"):
        assert k in keys


def test_assert_detects_injected_saas_keys():
    leaked = assert_no_saas_leakage("real_estate", ["land_cost", "cac", "arr", "churn", "mrr"])
    assert set(leaked) == {"arr", "cac", "churn", "mrr"}


def test_structured_questions_are_typed():
    for arch in ("services", "real_estate", "data_center", "saas_digital"):
        qs = questions_for_language(arch, "en")
        assert qs
        types = {q["question_type"] for q in qs}
        assert types - {"SHORT_TEXT", "LONG_TEXT"}, f"{arch} should have structured types, got {types}"


def test_assumption_agent_filters_saas_bleed_without_llm(monkeypatch):
    class FakeLLM:
        def invoke(self, messages):
            class R:
                content = """```json
{"assumptions": [
  {"key": "land_cost", "value": "10000000", "source": "AI Estimated Assumption", "confidence": "low", "ai_estimated": true},
  {"key": "construction_boq", "value": "40000000", "source": "AI Estimated Assumption", "confidence": "low", "ai_estimated": true},
  {"key": "cac", "value": "120", "source": "AI Estimated Assumption", "confidence": "low", "ai_estimated": true},
  {"key": "arr", "value": "1", "source": "AI Estimated Assumption", "confidence": "low", "ai_estimated": true},
  {"key": "churn", "value": "0.05", "source": "AI Estimated Assumption", "confidence": "low", "ai_estimated": true}
], "assumptions_complete": true}
```"""

            return R()

    monkeypatch.setattr(assumption_mod, "get_llm", lambda task="assumptions": FakeLLM())

    state = StudyState(
        study_id="s1",
        project_id="p1",
        user_id="u1",
        language="en",
        phase="ASSUMPTIONS_REVIEW",
        profile=ProjectProfile(archetype="real_estate", sector="residential", archetype_confirmed=True),
        profile_confirmed=True,
        structured_answers={"units": "200", "selling_price": "900000"},
    )
    out = assumption_mod.run_assumptions(state)
    keys = {a.key for a in out.assumptions}
    assert "cac" not in keys
    assert "arr" not in keys
    assert "churn" not in keys
    assert "land_cost" in keys
    assert "units" in keys
    assert any(a.ai_estimated for a in out.assumptions)
    assert any(a.source == "AI Estimated Assumption" or a.ai_estimated for a in out.assumptions)
    assert out.phase == "ASSUMPTIONS_REVIEW"
    assert out.assumptions_approved is False


def test_normalize_aliases():
    assert normalize_archetype("SaaS") == "saas_digital"
    assert normalize_archetype("datacenter") == "data_center"
    assert normalize_archetype("service") == "services"
