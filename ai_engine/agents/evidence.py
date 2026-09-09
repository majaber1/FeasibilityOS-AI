from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

from ..config import get_llm
from ..models.study_state import StudyState

SYSTEM_PROMPT_AR = """
أنت محلل أدلة متخصص في السوق السعودي.
مهمتك: جمع وتقييم الأدلة والمصادر التي يقدمها المستخدم لدعم دراسة الجدوى.

خطوات العمل:
1. راجع المعلومات المقدمة من المستخدم
2. صنّف كل معلومة حسب مصدرها (رسمي / مدخل مستخدم / مستند / افتراض AI / غير موثق)
3. قيّم مستوى الثقة لكل معلومة (0.0 إلى 1.0)
4. حدد المعلومات الناقصة التي تحتاج تأكيد

قواعد صارمة:
- لا تخترع أرقاماً أو مصادر
- وثّق كل مصدر بوضوح
- إذا لم يكن هناك مصدر رسمي، صنّف كـ "user_input" أو "ai_assumption"
- أجب بالعربية ما لم يكتب المستخدم بالإنجليزية

أخرج JSON داخل ```json ... ```:
{
  "claims": [
    {
      "statement": "النص",
      "source_type": "official|user_input|document|ai_assumption|unverified",
      "confidence": 0.0-1.0,
      "source_url": "رابط إن وجد أو null"
    }
  ],
  "gaps": ["معلومات ناقصة"],
  "evidence_sufficient": true/false
}
"""

SYSTEM_PROMPT_EN = """
You are an evidence analyst specializing in the Saudi Arabian market.
Your task: collect and evaluate evidence and sources the user provides for the feasibility study.

Steps:
1. Review user-provided information
2. Classify each piece by source (official / user_input / document / ai_assumption / unverified)
3. Assess confidence level for each (0.0 to 1.0)
4. Identify missing information that needs confirmation

Strict rules:
- Never invent numbers or sources
- Document every source clearly
- If no official source, classify as "user_input" or "ai_assumption"
- Reply in English if user writes in English

Output JSON inside ```json ... ```:
{
  "claims": [
    {
      "statement": "text",
      "source_type": "official|user_input|document|ai_assumption|unverified",
      "confidence": 0.0-1.0,
      "source_url": "url if available or null"
    }
  ],
  "gaps": ["missing information"],
  "evidence_sufficient": true/false
}
"""


def run_evidence(state: StudyState) -> StudyState:
    lang = state.language
    system_prompt = SYSTEM_PROMPT_AR if lang == "ar" else SYSTEM_PROMPT_EN
    llm = get_llm("extraction")

    messages = [SystemMessage(content=system_prompt)] + state.messages

    try:
        response = llm.invoke(messages)
        response_text = response.content
    except Exception as e:
        state.error = str(e)
        state.next_action = "retry"
        return state

    evidence_data = _extract_json(response_text)
    if evidence_data:
        from ..models.study_state import Claim

        allowed = {"official", "user_input", "document", "ai_assumption", "unverified"}
        aliases = {
            "derived": "ai_assumption",
            "calculated": "ai_assumption",
            "estimate": "ai_assumption",
            "estimated": "ai_assumption",
            "assumption": "ai_assumption",
            "ai": "ai_assumption",
            "user": "user_input",
            "input": "user_input",
            "manual": "user_input",
            "gov": "official",
            "government": "official",
            "regulation": "official",
            "regulatory": "official",
            "file": "document",
            "doc": "document",
            "unknown": "unverified",
            "other": "unverified",
        }

        claims = []
        for c in evidence_data.get("claims", []):
            raw_type = str(c.get("source_type") or "unverified").strip().lower()
            source_type = raw_type if raw_type in allowed else aliases.get(raw_type, "unverified")
            try:
                confidence = float(c.get("confidence", 0.0) or 0.0)
            except (TypeError, ValueError):
                confidence = 0.0
            claims.append(Claim(
                statement=c.get("statement", "") or "",
                source_type=source_type,
                confidence=max(0.0, min(1.0, confidence)),
                source_url=c.get("source_url"),
            ))
        state.claims = claims
        state.error = None

        if evidence_data.get("evidence_sufficient", False):
            state.phase = "ASSUMPTIONS_REVIEW"
            state.evidence_approved = True
        else:
            state.phase = "EVIDENCE_REVIEW"

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
