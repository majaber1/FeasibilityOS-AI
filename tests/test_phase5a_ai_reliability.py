"""Phase 5A — AI reliability: sanitization + classification guards."""
from __future__ import annotations

import pytest

from ai_engine.utils.safe_messages import (
    is_internal_instruction,
    sanitize_chat_content,
    sanitize_error_for_user,
)
from ai_engine.agents.discovery import _resolve_archetype
from ai_engine.archetypes.schemas import schema_keys_for, assert_no_saas_leakage


def test_sanitize_error_hides_org_model_billing_token_limits():
    msg = sanitize_error_for_user(
        Exception(
            "Error code: 429 org_abc123 model=llama-3.3-70b-versatile "
            "https://console.groq.com/settings/billing exceeded 200K TPD / 100K TPM"
        ),
        context="provider",
    )
    low = msg.lower()
    assert "429" not in low
    assert "org_" not in low
    assert "llama" not in low
    assert "groq" not in low
    assert "billing" not in low
    assert "tpd" not in low
    assert "tpm" not in low
    assert "try again" in low or "moment" in low


def test_sanitize_chat_strips_financial_payload():
    raw = 'Here you go\n{"npv": 123456, "irr": 0.22, "capex": 900000, "assumptions": []}\n'
    cleaned = sanitize_chat_content(raw)
    assert "npv" not in cleaned.lower()
    assert "capex" not in cleaned.lower()
    assert "assumptions" not in cleaned.lower()


def test_provider_invoke_falls_back_then_raises():
    from unittest.mock import patch, MagicMock
    from ai_engine.provider import invoke_llm, ProviderUnavailableError

    calls = {"n": 0}

    def boom_factory(model: str):
        calls["n"] += 1
        llm = MagicMock()
        llm.invoke.side_effect = Exception(f"Error code: 429 rate_limit on {model}")
        return llm

    with patch("ai_engine.provider._build_chat_groq", side_effect=boom_factory):
        with pytest.raises(ProviderUnavailableError):
            invoke_llm("classification", [MagicMock()], context="unit")
    assert calls["n"] >= 2  # primary + alternate


def test_marketplace_never_becomes_data_center():
    chosen, ambiguous, reason = _resolve_archetype(
        "other",
        "data_center",
        "Two-sided marketplace for gig drivers like Uber/Careem in Jeddah",
    )
    assert chosen == "services"
    assert ambiguous is True


def test_sanitize_chat_strips_json_and_tool_traces():
    raw = (
        "Here is analysis.\n"
        "```json\n{\"assumptions\": [{\"key\": \"arr\"}]}\n```\n"
        "<tool_call>lookup</tool_call>\n"
        "req_deadbeef more text"
    )
    cleaned = sanitize_chat_content(raw)
    assert "```" not in cleaned
    assert "assumptions" not in cleaned
    assert "tool_call" not in cleaned
    assert "req_deadbeef" not in cleaned
    assert "Here is analysis" in cleaned or "more text" in cleaned


def test_sanitize_chat_drops_bare_json_and_internal_prompts():
    assert sanitize_chat_content('{"claims": []}') == ""
    assert is_internal_instruction(
        "Fill evidence now. For each missing item create an ai_assumption"
    )
    assert sanitize_chat_content(
        "Fill evidence now. For each missing item create an ai_assumption"
    ) == ""


def test_uber_never_becomes_data_center():
    chosen, ambiguous, reason = _resolve_archetype(
        "services", "data_center", "Build an Uber-like ride hailing app in Riyadh"
    )
    assert chosen == "services"
    assert chosen != "data_center"
    assert ambiguous is True
    assert reason == "mobility_vs_data_center"

    chosen2, _, _ = _resolve_archetype(
        "other", "data_center", "Careem clone with drivers and take-rate"
    )
    assert chosen2 == "services"


def test_true_data_center_still_allowed():
    chosen, ambiguous, reason = _resolve_archetype(
        "data_center",
        "data_center",
        "20MW data center with racks, PUE 1.3, and colocation in NEOM",
    )
    assert chosen == "data_center"
    assert ambiguous is False


def test_ambiguous_classification_asks_confirmation():
    chosen, ambiguous, reason = _resolve_archetype(
        "real_estate", "industrial", "We develop mixed industrial residential compounds"
    )
    assert ambiguous is True
    assert reason == "heuristic_llm_disagree"


def test_saas_schema_has_capex_opex_and_unit_economics():
    keys = set(schema_keys_for("saas_digital"))
    for k in ("capex", "opex_annual", "arr", "cac", "ltv", "churn"):
        assert k in keys


@pytest.mark.parametrize(
    "archetype",
    ["real_estate", "data_center", "industrial", "retail", "services"],
)
def test_non_saas_isolation_unchanged(archetype):
    keys = schema_keys_for(archetype)
    assert assert_no_saas_leakage(archetype, keys) == []
