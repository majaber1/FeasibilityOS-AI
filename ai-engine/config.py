from __future__ import annotations

import os
from langchain_groq import ChatGroq

GROQ_FAST = os.getenv("GROQ_MODEL_FAST", "llama-3.1-8b-instant")
GROQ_SMART = os.getenv("GROQ_MODEL_PRIMARY", "llama-3.3-70b-versatile")

_TASK_ROUTING = {
    "classification": GROQ_FAST,
    "extraction": GROQ_FAST,
    "questions": GROQ_SMART,
    "assumptions": GROQ_SMART,
    "risk": GROQ_SMART,
    "decision": GROQ_SMART,
    "general": GROQ_SMART,
}


def get_llm(task: str = "general") -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set")

    model = _TASK_ROUTING.get(task, GROQ_SMART)

    return ChatGroq(
        model=model,
        api_key=api_key,
        temperature=0.1,
        max_tokens=2000,
    )


def get_langfuse():
    try:
        if os.getenv("LANGFUSE_PUBLIC_KEY"):
            from langfuse import Langfuse
            return Langfuse()
    except Exception:
        pass
    return None
