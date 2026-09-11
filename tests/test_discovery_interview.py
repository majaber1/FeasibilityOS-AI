"""Discovery Advisor interview model — does not mutate frozen engines."""
from __future__ import annotations

from ai_engine.discovery import (
    ANSWER_TYPES,
    ARCHETYPE_CATEGORY_PACKS,
    build_discovery_interview,
    is_question_satisfied,
    unanswered_required,
)


def test_saas_interview_covers_required_topics():
    qs = build_discovery_interview("saas_digital", "en")
    assert qs
    cats = {q["category"] for q in qs}
    for needed in ARCHETYPE_CATEGORY_PACKS["saas_digital"]:
        assert needed in cats, f"missing category {needed} in {cats}"
    for q in qs:
        assert q["answer_type"] in ANSWER_TYPES
        assert "allow_ai_estimate" in q
        assert q.get("question") or q.get("prompt")
        assert q["explanation"]
        assert q["id"]


def test_professional_services_topics():
    qs = build_discovery_interview(
        "services",
        "en",
        services_variant="professional",
        context_text="cybersecurity MSSP consulting",
    )
    ids = {q["id"] for q in qs}
    assert "drivers" not in ids
    assert "take_rate" not in ids
    cats = {q["category"] for q in qs}
    for needed in ARCHETYPE_CATEGORY_PACKS["services_professional"]:
        assert needed in cats, f"missing {needed} in {cats}"


def test_mobility_topics():
    qs = build_discovery_interview(
        "services",
        "en",
        services_variant="mobility",
        context_text="Uber drivers trips take rate",
    )
    ids = {q["id"] for q in qs}
    assert "drivers" in ids
    assert any("trip" in i for i in ids)
    assert "take_rate" in ids
    cats = {q["category"] for q in qs}
    for needed in ARCHETYPE_CATEGORY_PACKS["services_mobility"]:
        assert needed in cats


def test_real_estate_and_dc_topics():
    re_qs = build_discovery_interview("real_estate", "en")
    re_cats = {q["category"] for q in re_qs}
    for needed in ARCHETYPE_CATEGORY_PACKS["real_estate"]:
        assert needed in re_cats, f"RE missing {needed}"

    dc_qs = build_discovery_interview("data_center", "en")
    dc_cats = {q["category"] for q in dc_qs}
    for needed in ARCHETYPE_CATEGORY_PACKS["data_center"]:
        assert needed in dc_cats, f"DC missing {needed}"


def test_ai_estimate_satisfies_without_answer_value():
    q = {
        "id": "cac",
        "required": True,
        "answered": True,
        "ai_estimated": True,
        "answer": None,
    }
    assert is_question_satisfied(q, {})
    assert unanswered_required([q], {}) == []


def test_select_answer_type_normalization():
    qs = build_discovery_interview("real_estate", "en")
    financing = next(q for q in qs if "financ" in q["id"])
    assert financing["answer_type"] == "SELECT"
    assert financing["allow_ai_estimate"] is True
