from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

from ..archetypes import (
    ARCHETYPE_QUESTIONS,
    discovery_prompt_hardening,
    questions_for,
    recommended_model_for,
)
from ..config import get_llm
from ..models.study_state import StudyState, ProjectProfile

SYSTEM_PROMPT_AR = """
أنت مستشار أعمال خبير متخصص في السوق السعودي.
مهمتك: فهم المشروع الذي يصفه المستخدم وتصنيفه بدقة.

خطوات العمل:
1. اقرأ وصف المشروع بعناية
2. حدد نوع المشروع (SaaS / عقار / مركز بيانات / تجزئة / صناعة / خدمات / امتياز)
3. حدد مرحلته (فكرة / MVP / تشغيل / توسع)
4. اسأل الأسئلة المناسبة لنوع المشروع فقط — لا تسأل نفس الأسئلة لكل المشاريع
5. اكتشف المعلومات الناقصة

قواعد صارمة:
- فضّل استنتاج المرحلة (فكرة/MVP/تشغيل/توسع) وهدف القرار
  (استثمار/تمويل/جدوى/توسع) من وصف المشروع عندما يكون واضحاً.
  لا تُرجع "unknown" لهذه الحقول إذا كان النص يدل عليها.
- ضع في missing_information فقط الفجوات الحقيقية المناسبة لنوع المشروع
  (مثلاً: تسعير الوحدات للعقار، ميغاواط لمركز البيانات، عمولة/حجم معاملات للخدمات).
  لا توقف التصنيف بسبب المرحلة/هدف القرار إذا أمكن استنتاجهما.
- لا تخترع أرقاماً مالية دقيقة في هذه المرحلة
- لا تعطِ توصية مالية قبل اكتمال البيانات
- إذا لم تفهم المشروع، اسأل قبل التصنيف
- أجب دائماً بالعربية ما لم يكتب المستخدم بالإنجليزية

في النهاية أخرج JSON بهذا الشكل (داخل ```json ... ```):
{
  "archetype": "saas_digital|real_estate|data_center|retail|industrial|services|franchise|unknown",
  "sector": "وصف القطاع",
  "stage": "idea|mvp|operational|expansion",
  "decision_goal": "investment|funding|feasibility|expansion",
  "missing_information": ["قائمة", "بالمعلومات", "الناقصة"],
  "recommended_model": "saas_v1|real_estate_v1|data_center_v1|marketplace_services_v1|retail_v1|industrial_v1|franchise_v1|general_v1",
  "next_questions": ["السؤال الأول؟", "السؤال الثاني؟"]
}
"""

SYSTEM_PROMPT_EN = """
You are an expert business advisor specializing in the Saudi Arabian market.
Your task: understand and classify the project the user describes.

Steps:
1. Read the project description carefully
2. Identify project type (SaaS / Real Estate / Data Center / Retail / Industrial / Services / Franchise)
3. Identify stage (idea / MVP / operational / expansion)
4. Ask questions appropriate to THIS project type only
5. Identify missing information

Strict rules:
- Prefer inferring stage (idea/mvp/operational/expansion) and decision_goal
  (investment/funding/feasibility/expansion) from the description when clear.
  Avoid returning "unknown" for those fields when the text already implies them.
- Put only true archetype-appropriate blockers in missing_information
  (e.g. unit pricing for real estate, MW for data centers, take-rate/volume for services).
  Do not block on stage/decision_goal when they can be inferred.
- Never invent precise financial numbers in this step
- Never give a financial recommendation before data is complete
- If you don't understand the project, ask before classifying
- Reply in English if user writes in English

At the end, output JSON inside ```json ... ```:
{
  "archetype": "saas_digital|real_estate|data_center|retail|industrial|services|franchise|unknown",
  "sector": "sector description",
  "stage": "idea|mvp|operational|expansion",
  "decision_goal": "investment|funding|feasibility|expansion",
  "missing_information": ["list", "of", "gaps"],
  "recommended_model": "saas_v1|real_estate_v1|data_center_v1|marketplace_services_v1|retail_v1|industrial_v1|franchise_v1|general_v1",
  "next_questions": ["Question 1?", "Question 2?"]
}
"""


def run_discovery(state: StudyState) -> StudyState:
    # Confirm Profile already accepted the profile — do not re-gate on missing fields.
    if state.profile_confirmed:
        state.phase = "EVIDENCE_REVIEW"
        state.next_action = "review_evidence"
        state.error = None
        return state

    lang = state.language
    system_prompt = SYSTEM_PROMPT_AR if lang == "ar" else SYSTEM_PROMPT_EN
    system_prompt = system_prompt + discovery_prompt_hardening(lang)
    llm = get_llm("questions")

    context = ""
    if state.profile and state.profile.archetype != "unknown":
        archetype = state.profile.archetype
        questions = questions_for(archetype, lang)
        if questions:
            q_text = "\n".join(f"- {q}" for q in questions)
            if lang == "ar":
                context = f"\n\nبناءً على تصنيف المشروع ({archetype})، هذه الأسئلة ذات الصلة:\n{q_text}"
            else:
                context = f"\n\nBased on project type ({archetype}), relevant questions:\n{q_text}"

    messages = [SystemMessage(content=system_prompt + context)] + state.messages

    try:
        response = llm.invoke(messages)
        response_text = response.content
    except Exception as e:
        state.error = str(e)
        state.next_action = "retry"
        return state

    profile_data = _extract_json(response_text)
    if profile_data:
        stage = str(profile_data.get("stage") or "").strip() or "unknown"
        decision_goal = str(profile_data.get("decision_goal") or "").strip() or "unknown"
        # Prefer inferred labels over blank/unknown when description already implies them.
        if stage.lower() in {"unknown", "n/a", "na", "none", ""}:
            stage = "idea"
        if decision_goal.lower() in {"unknown", "n/a", "na", "none", ""}:
            decision_goal = "feasibility"

        archetype = profile_data.get("archetype", "unknown") or "unknown"
        recommended = profile_data.get("recommended_model") or recommended_model_for(archetype)
        state.profile = ProjectProfile(
            archetype=archetype,
            sector=profile_data.get("sector", ""),
            stage=stage,
            decision_goal=decision_goal,
            language=lang,
            missing_information=profile_data.get("missing_information", []) or [],
            recommended_model=recommended,
        )
        if state.profile.missing_information:
            state.phase = "NEEDS_INFORMATION"
        else:
            state.phase = "EVIDENCE_REVIEW"

    state.messages.append(AIMessage(content=response_text))
    state.next_action = "review_profile" if state.profile else "answer_questions"
    return state


def _extract_json(text: str) -> dict | None:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None
