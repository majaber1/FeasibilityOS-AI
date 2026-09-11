"""Structured discovery questions per archetype (yes/no, select, numeric).

Interview enrichment (category, explanation, allow_ai_estimate, answer_type)
lives in ai_engine.discovery — this module stays a thin schema→question map.
"""
from __future__ import annotations

from typing import Any

from .schemas import get_assumption_schema


def get_structured_questions(
    archetype: str,
    *,
    context_text: str | None = None,
    services_variant: str | None = None,
) -> list[dict[str, Any]]:
    """Map assumption schema fields into discovery question payloads."""
    questions: list[dict[str, Any]] = []
    for field in get_assumption_schema(
        archetype, context_text=context_text, services_variant=services_variant
    ):
        qtype = {
            "yes_no": "YES_NO",
            "single_select": "SINGLE_SELECT",
            "multi_select": "MULTI_SELECT",
            "number": "NUMBER",
            "currency": "CURRENCY",
            "percent": "PERCENTAGE",
            "text": "SHORT_TEXT",
        }.get(field["input_type"], "SHORT_TEXT")
        questions.append(
            {
                "id": field["key"],
                "field_key": field["key"],
                "prompt_en": field["label_en"],
                "prompt_ar": field["label_ar"],
                "question_type": qtype,
                "unit": field.get("unit"),
                "required": bool(field.get("required", True)),
                "options_en": field.get("options_en") or [],
                "options_ar": field.get("options_ar") or [],
                "description_en": field.get("description_en") or "",
                "description_ar": field.get("description_ar") or "",
                "answer": None,
                "answered": False,
                "ai_estimated": False,
            }
        )
    return questions


def questions_for_language(
    archetype: str,
    language: str = "en",
    *,
    context_text: str | None = None,
    services_variant: str | None = None,
) -> list[dict[str, Any]]:
    """Return interview-ready questions (Discovery Advisor enrichment applied)."""
    from ai_engine.discovery import build_discovery_interview

    return build_discovery_interview(
        archetype,
        language,
        context_text=context_text,
        services_variant=services_variant,
    )
