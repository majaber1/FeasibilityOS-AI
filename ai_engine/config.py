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
        "risk": smart,
        "decision": smart,
        "general": smart,
    }
    return routing.get(task, smart)


# Back-compat aliases for anything that imported the previous constants.
GROQ_FAST = DEFAULT_GROQ_FAST
GROQ_SMART = DEFAULT_GROQ_SMART


class _FallbackChatModel:
    """Prefer the task model; on Groq daily token (TPD) 429, retry with FAST.

    Risk/decision normally use GROQ_MODEL_PRIMARY (120b). When that tier is
    exhausted, fall back to GROQ_MODEL_FAST (20b) so studies can still complete.
    """

    def __init__(self, primary, fallback):
        self._primary = primary
        self._fallback = fallback
        self._use_fallback = False

    def _is_rate_limit(self, exc: Exception) -> bool:
        text = str(exc).lower()
        return (
            "429" in text
            or "rate_limit" in text
            or "tokens per day" in text
            or "tpd" in text
        )

    def invoke(self, *args, **kwargs):
        model = self._fallback if self._use_fallback else self._primary
        try:
            return model.invoke(*args, **kwargs)
        except Exception as exc:
            if self._use_fallback or not self._is_rate_limit(exc):
                raise
            self._use_fallback = True
            return self._fallback.invoke(*args, **kwargs)

    async def ainvoke(self, *args, **kwargs):
        model = self._fallback if self._use_fallback else self._primary
        try:
            return await model.ainvoke(*args, **kwargs)
        except Exception as exc:
            if self._use_fallback or not self._is_rate_limit(exc):
                raise
            self._use_fallback = True
            return await self._fallback.ainvoke(*args, **kwargs)


def get_llm(task: str = "general"):
    from langchain_groq import ChatGroq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set")

    primary_id = _model_for_task(task)
    fast_id = resolve_groq_model(os.getenv("GROQ_MODEL_FAST", DEFAULT_GROQ_FAST))

    primary = ChatGroq(
        model=primary_id,
        api_key=api_key,
        temperature=0.1,
        max_tokens=2000,
    )
    if primary_id == fast_id:
        return primary

    fallback = ChatGroq(
        model=fast_id,
        api_key=api_key,
        temperature=0.1,
        max_tokens=2000,
    )
    return _FallbackChatModel(primary, fallback)


def get_langfuse():
    try:
        if os.getenv("LANGFUSE_PUBLIC_KEY"):
            from langfuse import Langfuse
            return Langfuse()
    except Exception:
        pass
    return None
