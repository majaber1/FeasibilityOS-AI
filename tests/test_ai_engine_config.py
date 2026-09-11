"""Groq model routing: retired Llama IDs must remap to current replacements."""
import os
from unittest.mock import patch

from ai_engine.config import (
    DEFAULT_GROQ_FAST,
    DEFAULT_GROQ_SMART,
    _model_for_task,
    resolve_groq_model,
)


def test_resolve_maps_retired_llama_ids():
    assert resolve_groq_model("llama-3.3-70b-versatile") == DEFAULT_GROQ_SMART
    assert resolve_groq_model("llama-3.1-8b-instant") == DEFAULT_GROQ_FAST
    assert resolve_groq_model("llama-3.1-70b-versatile") == DEFAULT_GROQ_SMART


def test_resolve_leaves_current_ids_unchanged():
    assert resolve_groq_model("openai/gpt-oss-120b") == "openai/gpt-oss-120b"
    assert resolve_groq_model("qwen/qwen3.6-27b") == "qwen/qwen3.6-27b"


def test_defaults_are_current_groq_ids():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("GROQ_MODEL_PRIMARY", None)
        os.environ.pop("GROQ_MODEL_FAST", None)
        assert _model_for_task("general") == "openai/gpt-oss-120b"
        assert _model_for_task("extraction") == "openai/gpt-oss-20b"
        assert _model_for_task("questions") == "openai/gpt-oss-120b"


def test_env_override_still_remaps_retired_ids():
    with patch.dict(
        os.environ,
        {
            "GROQ_MODEL_PRIMARY": "llama-3.3-70b-versatile",
            "GROQ_MODEL_FAST": "llama-3.1-8b-instant",
        },
    ):
        # Phase 5A: decision/risk prefer FAST to stay within free-tier TPD.
        assert _model_for_task("decision") == "openai/gpt-oss-20b"
        assert _model_for_task("classification") == "openai/gpt-oss-20b"
        assert _model_for_task("questions") == "openai/gpt-oss-120b"


def test_explicit_current_override_is_honored():
    with patch.dict(
        os.environ,
        {
            "GROQ_MODEL_PRIMARY": "qwen/qwen3.6-27b",
            "GROQ_MODEL_FAST": "openai/gpt-oss-20b",
        },
    ):
        # decision/risk stay on FAST; smart tasks honor PRIMARY override.
        assert _model_for_task("decision") == "openai/gpt-oss-20b"
        assert _model_for_task("extraction") == "openai/gpt-oss-20b"
        assert _model_for_task("questions") == "qwen/qwen3.6-27b"
