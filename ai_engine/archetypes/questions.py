"""Structured discovery questions per archetype (yes/no, select, numeric)."""
from __future__ import annotations

from typing import Any

from .schemas import get_assumption_schema


def get_structured_questions(archetype: str) -> list[dict[str, Any]]:
    """Map assumption schema fields into discovery question payloads."""
    questions: list[dict[str, Any]] = []
    for field in get_assumption_schema(archetype):
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
            }
        )
    return questions


def questions_for_language(archetype: str, language: str = "en") -> list[dict[str, Any]]:
    lang = "ar" if language == "ar" else "en"
    out = []
    for q in get_structured_questions(archetype):
        out.append(
            {
                **q,
                "prompt": q["prompt_ar"] if lang == "ar" else q["prompt_en"],
                "options": q["options_ar"] if lang == "ar" else q["options_en"],
                "description": q["description_ar"] if lang == "ar" else q["description_en"],
            }
        )
    return out
