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


def test_sanitize_error_hides_provider_details():
    msg = sanitize_error_for_user(
        Exception("Error code: 429 req_abc123 rate_limit from groq"),
        context="unit",
    )
    assert "429" not in msg
    assert "req_abc" not in msg
    assert "groq" not in msg.lower()
    assert "try again" in msg.lower() or "moment" in msg.lower()


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
