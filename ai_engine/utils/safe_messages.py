"""User-facing message sanitization — never leak provider IDs, stacks, or raw model JSON."""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

USER_SAFE_AI_ERROR = (
    "We could not complete this AI step right now. Please try again in a moment. "
    "If the problem continues, refresh the page or continue with the review panels."
)
USER_SAFE_AI_ERROR_AR = (
    "تعذر إكمال خطوة الذكاء الاصطناعي حالياً. حاول مرة أخرى بعد لحظات. "
    "إذا استمرت المشكلة، حدّث الصفحة أو تابع عبر لوحات المراجعة."
)

AI_UNAVAILABLE_CLASSIFY = (
    "AI classification is temporarily unavailable. "
    "Please confirm the project archetype below before continuing — "
    "we will not silently lock a classification."
)
AI_UNAVAILABLE_CLASSIFY_AR = (
    "تصنيف الذكاء الاصطناعي غير متاح مؤقتاً. "
    "يرجى تأكيد نوع المشروع أدناه قبل المتابعة — "
    "لن نثبّت التصنيف تلقائياً دون تأكيدك."
)

_PROVIDER_ID_RE = re.compile(
    r"\b(req_[a-zA-Z0-9]+|chatcmpl-[a-zA-Z0-9]+|call_[a-zA-Z0-9]+|"
    r"org_[a-zA-Z0-9]+|proj_[a-zA-Z0-9]+)\b",
    re.IGNORECASE,
)
_MODEL_NAME_RE = re.compile(
    r"\b(llama-[\w.\-]+|gpt-oss-[\w.\-]+|gpt-4[\w.\-]*|gpt-3\.5[\w.\-]*|"
    r"openai/[\w.\-]+|mixtral-[\w.\-]+|gemma-[\w.\-]+|"
    r"groq/[^\s,;]+)\b",
    re.IGNORECASE,
)
_BILLING_URL_RE = re.compile(
    r"https?://[^\s]*(?:console\.groq\.com|platform\.openai\.com|"
    r"billing|usage|rate-limits|settings/billing)[^\s]*",
    re.IGNORECASE,
)
_TOKEN_LIMIT_RE = re.compile(
    r"\b(\d+\s*[KkMm]?\s*(?:TPM|TPD|tokens?(?:\s*/\s*day)?|"
    r"token(?:s)?\s*(?:per|/)\s*(?:day|minute|month)|"
    r"daily\s+token|quota|credits?))\b|"
    r"\b(tokens?\s+per\s+day|token\s+limit|context\s+length|"
    r"max_tokens|max tokens)\b",
    re.IGNORECASE,
)
_HTTP_STATUS_RE = re.compile(
    r"(Error code:\s*\d+|HTTP\s*/?\s*\d{3}|status[_ ]?code[=:\s]+\d{3}|"
    r"rate[_ ]?limit|429|503|401|403|500)\b",
    re.IGNORECASE,
)
_STACK_RE = re.compile(
    r"(Traceback \(most recent call last\):|File \"[^\"]+\", line \d+|"
    r"^\s*at .+\(.+:\d+:\d+\)|"
    r"groq\.|openai\.|httpx\.|urllib3\.|requests\.exceptions)",
    re.IGNORECASE | re.MULTILINE,
)
_JSON_FENCE_RE = re.compile(r"```(?:json|javascript|js|tool|xml)?\s*[\s\S]*?```", re.IGNORECASE)
_BARE_JSON_RE = re.compile(r"^\s*[\{\[][\s\S]*[\}\]]\s*$")
_TOOL_CALL_RE = re.compile(
    r"(<tool_call>[\s\S]*?</tool_call>|"
    r"\"tool_calls\"\s*:|"
    r"function_call\s*[:=]|"
    r"invoke\s+[a-zA-Z_]+\s*with)",
    re.IGNORECASE,
)
_PROMPT_LEAK_RE = re.compile(
    r"(You are an expert|SYSTEM_PROMPT|Strict rules:|Output JSON inside|"
    r"Fill evidence now\. For each missing item|"
    r"املأ الأدلة الآن|"
    r"Do not invent|"
    r"```json)",
    re.IGNORECASE,
)
_FINANCIAL_PAYLOAD_RE = re.compile(
    r"(\"(?:npv|irr|payback_months|capex|annual_revenues|annual_costs|"
    r"revenue_projections|cost_projections|scenarios|assumptions|"
    r"claims|critical_risks|verdict)\"\s*:)|"
    r"^\s*\{[\s\S]*\"(?:npv|irr|capex|assumptions)\"[\s\S]*\}\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_INTERNAL_INSTRUCTION_MARKERS = (
    "fill evidence now",
    "create an ai_assumption",
    "set evidence_sufficient",
    "املأ الأدلة الآن",
    "بقيمة تقديرية واقعية",
    "do not invent",
    "output json inside",
    "strict rules:",
)


def user_safe_ai_error(language: str | None = "en") -> str:
    return USER_SAFE_AI_ERROR_AR if (language or "en").startswith("ar") else USER_SAFE_AI_ERROR


def ai_unavailable_classify_message(language: str | None = "en") -> str:
    return (
        AI_UNAVAILABLE_CLASSIFY_AR
        if (language or "en").startswith("ar")
        else AI_UNAVAILABLE_CLASSIFY
    )


def sanitize_error_for_user(exc: Any, *, language: str | None = "en", context: str = "") -> str:
    """Log technical details; return a stable user-safe string."""
    detail = exc if isinstance(exc, str) else f"{type(exc).__name__}: {exc}"
    logger.warning(
        "AI step failed%s: %s",
        f" ({context})" if context else "",
        detail,
        exc_info=not isinstance(exc, str),
    )
    return user_safe_ai_error(language)


def is_internal_instruction(text: str | None) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    return any(m in t for m in _INTERNAL_INSTRUCTION_MARKERS)


def _scrub_provider_fingerprints(text: str) -> str:
    cleaned = _PROVIDER_ID_RE.sub("[redacted]", text)
    cleaned = _BILLING_URL_RE.sub("[redacted-url]", cleaned)
    cleaned = _MODEL_NAME_RE.sub("[model]", cleaned)
    cleaned = _TOKEN_LIMIT_RE.sub("[limit]", cleaned)
    return cleaned


def sanitize_chat_content(
    text: str | None,
    *,
    language: str | None = "en",
    fallback: str | None = None,
) -> str:
    """Strip JSON, tool traces, provider IDs, model/billing leaks, and stack-like content."""
    if text is None:
        return ""
    raw = str(text)
    if not raw.strip():
        return ""

    if is_internal_instruction(raw):
        return ""

    cleaned = _JSON_FENCE_RE.sub("", raw)
    cleaned = _TOOL_CALL_RE.sub("", cleaned)
    cleaned = _scrub_provider_fingerprints(cleaned)
    # Drop embedded financial / structured payload objects even when preceded by prose.
    cleaned = re.sub(
        r"\{[^{}]*\"(?:npv|irr|capex|assumptions|claims|critical_risks|verdict)\"[^{}]*\}",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    kept_lines: list[str] = []
    for line in cleaned.splitlines():
        if _STACK_RE.search(line) or _HTTP_STATUS_RE.search(line):
            continue
        if re.search(r"(Exception|Error):\s*.{0,40}(groq|openai|api\.|httpx)", line, re.I):
            continue
        if re.search(
            r"(console\.groq|billing|tokens?\s+per\s+day|org_[a-z0-9]+)",
            line,
            re.I,
        ):
            continue
        if re.search(
            r"^(Classified as .+ via keyword fallback \(|Risk assessment fallback \(|"
            r"Decision fallback \(|Rule Fallback: assumption generation LLM unavailable \()",
            line,
        ):
            continue
        kept_lines.append(line)
    cleaned = "\n".join(kept_lines).strip()

    if _BARE_JSON_RE.match(cleaned) or (cleaned.startswith("{") and '"assumptions"' in cleaned):
        cleaned = ""
    if _FINANCIAL_PAYLOAD_RE.search(cleaned) and (
        cleaned.strip().startswith("{") or cleaned.strip().startswith("[")
    ):
        cleaned = ""
    if _PROMPT_LEAK_RE.search(cleaned) and (
        "```" in raw or '"archetype"' in cleaned or '"claims"' in cleaned
    ):
        cleaned = _JSON_FENCE_RE.sub("", cleaned)
        if _PROMPT_LEAK_RE.search(cleaned) and len(cleaned) < 80:
            cleaned = ""

    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    cleaned = cleaned.strip("`").strip()

    if not cleaned:
        return fallback if fallback is not None else ""
    return cleaned
