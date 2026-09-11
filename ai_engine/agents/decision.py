from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

from ..archetypes import recommended_model_for, risk_themes_for
from ..config import get_llm
from ..models.study_state import StudyState

SYSTEM_PROMPT_AR = """
أنت مستشار قرارات استثمارية خبير في السوق السعودي.
مهمتك: إصدار القرار النهائي بناءً على كل التحليلات السابقة.

المدخلات المتاحة:
- ملف المشروع (النوع، القطاع، المرحلة)
- الأدلة والمصادر
- الافتراضات المعتمدة
- التحليل المالي (NPV, IRR, فترة الاسترداد)
- تقييم المخاطر

القرارات الممكنة:
- GO: المشروع مجدي ويُنصح بالمضي فيه
- GO_WITH_CONDITIONS: مجدي لكن بشروط محددة
- DEFER: يحتاج مزيد من المعلومات أو الانتظار
- NO_GO: غير مجدي في الوضع الحالي
- INSUFFICIENT_EVIDENCE: لا تكفي البيانات لاتخاذ قرار

قواعد صارمة:
- لا تعطِ GO إذا كان IRR سالب أو NPV سالب بشكل واضح
- لا تعطِ GO إذا كانت المخاطر الحرجة بدون خطة تخفيف
- DEFER أفضل من GO مع بيانات ناقصة
- كن صريحاً وموضوعياً
- أجب بالعربية ما لم يكتب المستخدم بالإنجليزية

أخرج JSON داخل ```json ... ```:
{
  "verdict": "GO|GO_WITH_CONDITIONS|DEFER|NO_GO|INSUFFICIENT_EVIDENCE",
  "rationale": "شرح مفصل للقرار",
  "conditions": ["الشروط إن وجدت"],
  "key_risks": ["المخاطر الرئيسية"],
  "confidence_score": 0.0-1.0,
  "next_steps": ["الخطوات التالية المقترحة"]
}
"""

SYSTEM_PROMPT_EN = """
You are an expert investment decision advisor for the Saudi market.
Your task: issue the final verdict based on all previous analyses.

Available inputs:
- Project profile (type, sector, stage)
- Evidence and sources
- Approved assumptions
- Financial analysis (NPV, IRR, payback)
- Risk assessment

Possible verdicts:
- GO: Project is feasible, recommended to proceed
- GO_WITH_CONDITIONS: Feasible but with specific conditions
- DEFER: Needs more information or should wait
- NO_GO: Not feasible in current state
- INSUFFICIENT_EVIDENCE: Not enough data for a decision

Strict rules:
- Never give GO if IRR is negative or NPV is clearly negative
- Never give GO if critical risks have no mitigation plan
- DEFER is better than GO with incomplete data
- Be honest and objective
- Reply in English if user writes in English

Output JSON inside ```json ... ```:
{
  "verdict": "GO|GO_WITH_CONDITIONS|DEFER|NO_GO|INSUFFICIENT_EVIDENCE",
  "rationale": "detailed explanation",
  "conditions": ["conditions if any"],
  "key_risks": ["key risks"],
  "confidence_score": 0.0-1.0,
  "next_steps": ["suggested next steps"]
}
"""


def run_decision(state: StudyState) -> StudyState:
    lang = state.language
    system_prompt = SYSTEM_PROMPT_AR if lang == "ar" else SYSTEM_PROMPT_EN
    llm = get_llm("decision")

    context_parts = []
    if state.profile:
        archetype = state.profile.archetype
        context_parts.append(
            f"Project: {archetype} / {state.profile.sector} / "
            f"Stage: {state.profile.stage} / Goal: {state.profile.decision_goal} / "
            f"Model: {state.profile.recommended_model or recommended_model_for(archetype)}"
        )
        themes = risk_themes_for(archetype)
        if themes:
            context_parts.append("Decision must reflect archetype-specific risks: " + "; ".join(themes))
    if state.claims:
        claims_text = "\n".join(f"- {c.statement} ({c.source_type}, conf: {c.confidence})" for c in state.claims[:10])
        context_parts.append(f"Evidence:\n{claims_text}")
    if state.assumptions:
        assumptions_text = "\n".join(
            f"- {a.key}: {a.value} ({a.confidence}) [low:{a.low} / base:{a.base} / high:{a.high}]"
            for a in state.assumptions
        )
        context_parts.append(f"Assumptions:\n{assumptions_text}")
    if state.financial_results:
        fr = state.financial_results
        context_parts.append(
            f"Financials: NPV={fr.get('npv')}, IRR={fr.get('irr')}, "
            f"Payback={fr.get('payback_months')}m, Breakeven={fr.get('breakeven_months')}m"
        )
        scenarios = fr.get("scenarios", {})
        if scenarios:
            context_parts.append(f"Scenarios: {json.dumps(scenarios)}")
    if state.decision_risks:
        context_parts.append(f"Critical risks: {', '.join(state.decision_risks)}")

    extra = ""
    if context_parts:
        extra = "\n\nFull Context:\n" + "\n".join(context_parts)

    # Decision context is already complete in `extra`. Do NOT append the full
    # chat history — long Uber-like threads exceed Groq TPM on fallback models
    # (gpt-oss-20b ~8k TPM) and block verdict generation (413 request too large).
    recent = list(state.messages[-2:]) if state.messages else []
    messages = [SystemMessage(content=system_prompt + extra)] + recent

    try:
        response = llm.invoke(messages)
        response_text = response.content
    except Exception as e:
        state.error = str(e)
        state.next_action = "retry"
        return state

    decision_data = _extract_json(response_text)
    if decision_data:
        state.verdict = decision_data.get("verdict", "INSUFFICIENT_EVIDENCE")
        state.decision_rationale = decision_data.get("rationale", "")
        state.decision_conditions = decision_data.get("conditions", [])
        state.decision_risks = decision_data.get("key_risks", state.decision_risks)
        state.decision_version += 1
        # Insufficient evidence overrides firm investment verdicts when claim
        # confidence is below threshold (or evidence volume is too low).
        from .report_builder import apply_evidence_verdict_override

        apply_evidence_verdict_override(state)
        # After a verdict is issued, advance into funding readiness.
        state.phase = "FUNDING_READY"

    state.messages.append(AIMessage(content=response_text))
    state.next_action = "present_decision"
    return state


def _extract_json(text: str) -> dict | None:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None
