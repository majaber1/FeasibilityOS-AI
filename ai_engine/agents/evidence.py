from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

from ..config import get_llm
from ..models.study_state import (
    Claim,
    StudyState,
    compute_evidence_status,
    filter_evidence_claims,
    is_source_backed_claim,
)

SYSTEM_PROMPT_AR = """
أنت باحث أدلة خبير في دراسات الجدوى للسوق السعودي.
مهمتك: جمع أدلة قابلة للتتبع من مصادر فقط.

قواعد صارمة (لا تُكسر):
- NO SOURCE → NOT EVIDENCE
- لا تخترع أرقاماً أو مصادر أو تقديرات داخل قائمة claims
- التقديرات والافتراضات التخطيطية ليست أدلة — لا تضعها في claims
- وثّق كل مصدر بوضوح (نوع المصدر + رابط أو عنوان المصدر)
- إذا لم تتوفر مصادر، أعد claims=[] و evidence_sufficient=false و evidence_status="empty" أو "degraded"

أخرج JSON داخل ```json ... ```:
{
  "claims": [
    {
      "statement": "بيان مدعوم بمصدر",
      "source_type": "official|user_input|document",
      "source_url": "https://...",
      "source_title": "اسم المصدر",
      "confidence": 0.0
    }
  ],
  "gaps": ["..."],
  "evidence_sufficient": false,
  "evidence_status": "empty|degraded|available"
}
"""

SYSTEM_PROMPT_EN = """
You are an evidence researcher for Saudi feasibility studies.
Your job: collect traceable, source-backed evidence only.

Strict rules (non-negotiable):
- NO SOURCE → NOT EVIDENCE
- Never invent numbers, sources, or estimates inside claims
- Planning estimates are NOT evidence — do not put them in claims
- Document every source clearly (source_type + URL or source_title)
- If no sources are available, return claims=[] and evidence_sufficient=false
  with evidence_status "empty" or "degraded"

Output JSON inside ```json ... ```:
{
  "claims": [
    {
      "statement": "source-backed statement",
      "source_type": "official|user_input|document",
      "source_url": "https://...",
      "source_title": "source name",
      "confidence": 0.0
    }
  ],
  "gaps": ["..."],
  "evidence_sufficient": false,
  "evidence_status": "empty|degraded|available"
}
"""


def run_evidence(state: StudyState) -> StudyState:
    lang = state.language
    system_prompt = SYSTEM_PROMPT_AR if lang == "ar" else SYSTEM_PROMPT_EN

    try:
        llm = get_llm("extraction")
    except Exception as e:
        # Honest degraded path — NEVER fabricate Evidence.
        state.claims = []
        state.evidence_status = "degraded"
        state.phase = "EVIDENCE_REVIEW"
        state.next_action = "review_evidence"
        state.error = None
        state.blocking_reason = "evidence_provider_unavailable"
        note = (
            "تعذر تهيئة مزود الأدلة. لا توجد أدلة مصدرية حالياً (حالة degraded). "
            "التقديرات ليست أدلة — استخدم مسار الدراسة التقديرية للافتراضات."
            if lang == "ar"
            else "Evidence provider could not be initialized. No source-backed evidence is available "
            "(degraded). Estimates are not Evidence — use the provisional-study path for assumptions."
        )
        state.messages.append(AIMessage(content=f"{note}\n\n(Details: {e})"))
        return state

    messages = [SystemMessage(content=system_prompt)] + state.messages

    try:
        response = llm.invoke(messages)
        response_text = response.content
    except Exception as e:
        state.claims = []
        state.evidence_status = "degraded"
        state.phase = "EVIDENCE_REVIEW"
        state.next_action = "review_evidence"
        state.error = None
        state.blocking_reason = "evidence_provider_unavailable"
        note = (
            "تعذر الاتصال بمزود الأدلة. بقيت قائمة الأدلة فارغة بصدق."
            if lang == "ar"
            else "Evidence provider call failed. Evidence list left honestly empty."
        )
        state.messages.append(AIMessage(content=f"{note}\n\n(Details: {e})"))
        return state

    evidence_data = _extract_json(response_text)
    if evidence_data:
        claims: list[Claim] = []
        for c in evidence_data.get("claims", []) or []:
            payload = {
                "statement": c.get("statement", ""),
                "source_type": c.get("source_type"),
                "source_url": c.get("source_url"),
                "source_title": c.get("source_title"),
                "retrieved_date": c.get("retrieved_date"),
                "confidence": float(c.get("confidence") or 0.0),
                "status": "draft",
            }
            if payload["source_type"] == "ai_assumption":
                continue
            if not is_source_backed_claim(payload):
                continue
            try:
                conf = max(0.0, min(1.0, float(payload["confidence"])))
                claims.append(
                    Claim(
                        statement=payload["statement"],
                        source_type=payload["source_type"],
                        source_url=payload.get("source_url"),
                        source_title=payload.get("source_title"),
                        retrieved_date=payload.get("retrieved_date"),
                        confidence=conf,
                        status="draft",
                    )
                )
            except Exception:
                continue

        state.claims = filter_evidence_claims(claims)
        state.evidence_status = compute_evidence_status(state.claims)
        status_hint = evidence_data.get("evidence_status")
        if status_hint in ("empty", "degraded", "available") and not state.claims:
            state.evidence_status = status_hint if status_hint != "available" else "empty"
        state.error = None

        if evidence_data.get("evidence_sufficient", False) and state.claims:
            state.phase = "ASSUMPTIONS_REVIEW"
            state.evidence_approved = True
        else:
            state.phase = "EVIDENCE_REVIEW"
    else:
        state.claims = []
        state.evidence_status = "degraded"
        state.phase = "EVIDENCE_REVIEW"
        state.error = None
        response_text = (
            "تعذر استخراج JSON من نموذج الأدلة؛ لم يتم إنشاء أدلة مصطنعة."
            if lang == "ar"
            else "Could not parse evidence JSON; no synthetic evidence was created."
        )

    state.messages.append(AIMessage(content=response_text))
    state.next_action = "review_evidence"
    return state


def _extract_json(text: str) -> dict | None:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None
