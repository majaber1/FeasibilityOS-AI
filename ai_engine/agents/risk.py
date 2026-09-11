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
        risk_data = _extract_json(response_text)
    except Exception as e:
        # Deterministic fallback so journeys can complete when Groq is rate-limited.
        arch = state.profile.archetype if state.profile else "other"
        variant = getattr(state.profile, "services_variant", None) if state.profile else None
        risk_data = _fallback_risks(arch, services_variant=variant)
        response_text = (
            f"Risk assessment fallback ({e}).\n\n```json\n{json.dumps(risk_data, ensure_ascii=False)}\n```"
        )

    if risk_data:
        state.decision_risks = risk_data.get("critical_risks", [])
        if risk_data.get("risk_assessment_complete", False):
            state.phase = "DECISION_READY"
            state.error = None

    state.messages.append(AIMessage(content=response_text))
    state.next_action = "review_risks"
    return state


def _fallback_risks(archetype: str, services_variant: str | None = None) -> dict:
    by_arch = {
        "saas_digital": ["Customer acquisition cost inflation", "Churn above plan", "Saudi data-residency compliance"],
        "real_estate": ["Absorption delay", "Construction cost overrun", "Wafi / off-plan regulatory timing"],
        "data_center": ["Power availability / PUE miss", "Slow rack occupancy", "Cooling / uptime SLA breach"],
        "industrial": ["Raw-material price spike", "Utilization below plan", "Export / SFDA regulatory delay"],
        "services": ["Billable utilization shortfall", "Key consultant attrition", "Retainer churn"],
        "retail": ["Inventory turns miss", "Footfall below plan", "Lease cost escalation"],
    }
    if archetype == "services" and services_variant == "mobility":
        critical = [
            "Driver supply / take-rate pressure",
            "Trip volume below plan",
            "Regulatory / licensing delay for ride-hailing",
        ]
    else:
        critical = by_arch.get(archetype, ["Market demand uncertainty", "Funding gap", "Execution capacity"])
    return {
        "risks": [
            {
                "category": "market",
                "description": critical[0],
                "likelihood": "medium",
                "impact": "high",
                "mitigation": "Pilot before full scale and track leading indicators weekly",
            }
        ],
        "overall_risk_level": "medium",
        "critical_risks": critical,
        "risk_assessment_complete": True,
    }


def _extract_json(text: str) -> dict | None:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None
