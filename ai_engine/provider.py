"""LLM provider access with safe routing / fallback (no invented AI results)."""
from __future__ import annotations

import logging
import os
from typing import Any

from .config import (
    DEFAULT_GROQ_FAST,
    DEFAULT_GROQ_SMART,
    _model_for_task,
    resolve_groq_model,
)

logger = logging.getLogger(__name__)


class ProviderUnavailableError(RuntimeError):
    """Raised when all configured providers/models fail. Agents must degrade safely."""


_RATE_LIMIT_MARKERS = (
    "rate limit",
    "429",
    "tokens per day",
    "tpd",
    "tpm",
    "quota",
    "insufficient_quota",
    "billing",
)


def _is_rate_limit_or_quota(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(m in text for m in _RATE_LIMIT_MARKERS)


def _candidate_models(task: str) -> list[str]:
    """Ordered model candidates for a task — primary then alternate, no duplicates."""
    primary = _model_for_task(task)
    fast = resolve_groq_model(os.getenv("GROQ_MODEL_FAST", DEFAULT_GROQ_FAST))
    smart = resolve_groq_model(os.getenv("GROQ_MODEL_PRIMARY", DEFAULT_GROQ_SMART))
    alt = smart if primary == fast else fast
    out: list[str] = []
    for m in (primary, alt):
        if m and m not in out:
            out.append(m)
    return out


def _build_chat_groq(model: str):
    from langchain_groq import ChatGroq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ProviderUnavailableError("AI provider is not configured")
    return ChatGroq(
        model=model,
        api_key=api_key,
        temperature=0.1,
        max_tokens=2000,
    )


def get_llm(task: str = "general"):
    """Return a ChatGroq client for the preferred model of ``task``.

    Prefer :func:`invoke_llm` for call-site resilience (model fallback on rate limit).
    """
    models = _candidate_models(task)
    return _build_chat_groq(models[0])


def invoke_llm(task: str, messages: list[Any], *, context: str = ""):
    """Invoke LLM with model fallback on rate-limit / quota errors.

    Does **not** invent results. If every candidate fails, raises
    :class:`ProviderUnavailableError` so agents can ask for confirmation or
    use deterministic rule fallbacks without corrupting study state.
    """
    last_exc: BaseException | None = None
    for idx, model in enumerate(_candidate_models(task)):
        try:
            llm = _build_chat_groq(model)
            return llm.invoke(messages)
        except Exception as e:  # noqa: BLE001 — provider SDK raises many types
            last_exc = e
            logger.warning(
                "LLM invoke failed (task=%s model=%s attempt=%s context=%s): %s",
                task,
                model,
                idx + 1,
                context or "-",
                e,
            )
            continue
    raise ProviderUnavailableError(
        f"AI provider unavailable for task={task}"
    ) from last_exc
