from __future__ import annotations

import os

# Groq retired llama-3.1-8b-instant and llama-3.3-70b-versatile on 16 Aug 2026
# for free/developer tiers. See https://console.groq.com/docs/deprecations
DEFAULT_GROQ_FAST = "openai/gpt-oss-20b"
DEFAULT_GROQ_SMART = "openai/gpt-oss-120b"

DEPRECATED_GROQ_MODELS = {
    "llama-3.1-8b-instant": DEFAULT_GROQ_FAST,
    "llama-3.3-70b-versatile": DEFAULT_GROQ_SMART,
    "llama-3.1-70b-versatile": DEFAULT_GROQ_SMART,
    "llama3-8b-8192": DEFAULT_GROQ_FAST,
    "llama3-70b-8192": DEFAULT_GROQ_SMART,
}


def resolve_groq_model(model_id: str) -> str:
    """Map retired Groq model IDs to the current documented replacements.

    Env vars may still pin the old Llama names from .env.example / Vercel.
    Rewrite them at call time so production keeps working without a dashboard
    env edit.
    """
    return DEPRECATED_GROQ_MODELS.get(model_id.strip(), model_id)


def _model_for_task(task: str) -> str:
    fast = resolve_groq_model(os.getenv("GROQ_MODEL_FAST", DEFAULT_GROQ_FAST))
    smart = resolve_groq_model(os.getenv("GROQ_MODEL_PRIMARY", DEFAULT_GROQ_SMART))
    routing = {
        "classification": fast,
        "extraction": fast,
        "questions": smart,
        "assumptions": smart,
        # Prefer fast for risk/decision to stay within Groq free-tier TPD during E2E.
        "risk": fast,
        "decision": fast,
        "general": smart,
    }
    return routing.get(task, smart)


# Back-compat aliases for anything that imported the previous constants.
GROQ_FAST = DEFAULT_GROQ_FAST
GROQ_SMART = DEFAULT_GROQ_SMART


def get_llm(task: str = "general"):
    """Return preferred ChatGroq client for ``task``.

    For resilient invoke-with-fallback, use :func:`ai_engine.provider.invoke_llm`.
    """
    from .provider import get_llm as _provider_get_llm

    return _provider_get_llm(task)


def invoke_llm(task: str, messages, *, context: str = ""):
    """Invoke with model fallback on rate-limit; never invents results."""
    from .provider import invoke_llm as _provider_invoke

    return _provider_invoke(task, messages, context=context)


def get_langfuse():
    try:
        if os.getenv("LANGFUSE_PUBLIC_KEY"):
            from langfuse import Langfuse
            return Langfuse()
    except Exception:
        pass
    return None
