"""AI Business Discovery Advisor — interview layer over archetype questions.

Does not modify Archetype / Assumption / Financial / Risk / Decision engines.
Enriches existing schema-backed questions with interview metadata and AI-estimate flags.
"""

from .interview import (
    ANSWER_TYPES,
    ARCHETYPE_CATEGORY_PACKS,
    build_discovery_interview,
    enrich_questions_for_language,
    is_question_satisfied,
    unanswered_required,
)

__all__ = [
    "ANSWER_TYPES",
    "ARCHETYPE_CATEGORY_PACKS",
    "build_discovery_interview",
    "enrich_questions_for_language",
    "is_question_satisfied",
    "unanswered_required",
]
