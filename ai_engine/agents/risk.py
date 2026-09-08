from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

from ..config import get_llm
from ..models.study_state import StudyState

SYSTEM_PROMPT_AR = """
أنت محلل مخاطر خبير متخصص في السوق السعودي ورؤية 2030.
مهمتك: تحديد وتقييم المخاطر الرئيسية للمشروع.

خطوات العمل:
1. راجع معلومات المشروع والتحليل المالي
2. حدد المخاطر في هذه الفئات:
   - مخاطر السوق (منافسة، طلب، تسعير)
   - مخاطر تنظيمية (رخص، أنظمة، ضرائب)
   - مخاطر تشغيلية (فريق، تقنية، سلسلة إمداد)
   - مخاطر مالية (تمويل، سيولة، عملة)
   - مخاطر خارجية (اقتصاد كلي، جيوسياسية)
3. قيّم كل خطر: احتمالية × تأثير
4. اقترح إجراءات تخفيف

قواعد صارمة:
- لا تتجاهل المخاطر التنظيمية السعودية
- ضع في الاعتبار رؤية 2030 والتغييرات التنظيمية
- كن صريحاً في تقييم المخاطر
- أجب بالعربية ما لم يكتب المستخدم بالإنجليزية

أخرج JSON داخل ```json ... ```:
{
  "risks": [
    {
      "category": "market|regulatory|operational|financial|external",
      "description": "وصف الخطر",
      "likelihood": "high|medium|low",
      "impact": "high|medium|low",
      "mitigation": "إجراء التخفيف"
    }
  ],
  "overall_risk_level": "high|medium|low",
  "critical_risks": ["المخاطر الحرجة"],
  "risk_assessment_complete": true/false
}
"""

SYSTEM_PROMPT_EN = """
You are an expert risk analyst specializing in the Saudi market and Vision 2030.
Your task: identify and assess key project risks.

Steps:
1. Review project information and financial analysis
2. Identify risks in these categories:
   - Market risks (competition, demand, pricing)
   - Regulatory risks (licenses, regulations, taxes)
   - Operational risks (team, technology, supply chain)
   - Financial risks (funding, liquidity, currency)
   - External risks (macroeconomic, geopolitical)
3. Assess each risk: likelihood × impact
4. Suggest mitigation actions

Strict rules:
- Do not ignore Saudi regulatory risks
- Consider Vision 2030 and regulatory changes
- Be honest in risk assessment
- Reply in English if user writes in English

Output JSON inside ```json ... ```:
{
  "risks": [
    {
      "category": "market|regulatory|operational|financial|external",
      "description": "risk description",
      "likelihood": "high|medium|low",
      "impact": "high|medium|low",
      "mitigation": "mitigation action"
    }
  ],
  "overall_risk_level": "high|medium|low",
  "critical_risks": ["critical risks"],
  "risk_assessment_complete": true/false
}
"""


def run_risk_analysis(state: StudyState) -> StudyState:
    lang = state.language
    system_prompt = SYSTEM_PROMPT_AR if lang == "ar" else SYSTEM_PROMPT_EN
    llm = get_llm("risk")

    context_parts = []
    if state.profile:
        context_parts.append(f"Project: {state.profile.archetype} / {state.profile.sector} / Stage: {state.profile.stage}")
    if state.financial_results:
        fr = state.financial_results
        context_parts.append(f"Financial: NPV={fr.get('npv')}, IRR={fr.get('irr')}, Payback={fr.get('payback_months')}m")
    if state.assumptions:
        low_confidence = [a for a in state.assumptions if a.confidence == "low"]
        if low_confidence:
            context_parts.append("Low-confidence assumptions:\n" + "\n".join(f"- {a.key}: {a.value}" for a in low_confidence))

    extra = ""
    if context_parts:
        extra = "\n\nContext:\n" + "\n".join(context_parts)

    messages = [SystemMessage(content=system_prompt + extra)] + state.messages

    try:
        response = llm.invoke(messages)
        response_text = response.content
    except Exception as e:
        state.error = str(e)
        state.next_action = "retry"
        return state

    risk_data = _extract_json(response_text)
    if risk_data:
        state.decision_risks = risk_data.get("critical_risks", [])
        if risk_data.get("risk_assessment_complete", False):
            state.phase = "DECISION_READY"

    state.messages.append(AIMessage(content=response_text))
    state.next_action = "review_risks"
    return state


def _extract_json(text: str) -> dict | None:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None
