from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

from ..config import get_llm
from ..models.study_state import StudyState, ProjectProfile

SYSTEM_PROMPT_AR = """
أنت مستشار أعمال خبير متخصص في السوق السعودي.
مهمتك: فهم المشروع الذي يصفه المستخدم وتصنيفه بدقة.

خطوات العمل:
1. اقرأ وصف المشروع بعناية
2. حدد نوع المشروع (SaaS / عقار / مركز بيانات / تجزئة / صناعة / خدمات)
3. حدد مرحلته (فكرة / MVP / تشغيل / توسع)
4. اسأل الأسئلة المناسبة لنوع المشروع فقط — لا تسأل نفس الأسئلة لكل المشاريع
5. اكتشف المعلومات الناقصة

قواعد صارمة:
- فضّل استنتاج المرحلة (فكرة/MVP/تشغيل/توسع) وهدف القرار
  (استثمار/تمويل/جدوى/توسع) من وصف المشروع عندما يكون واضحاً.
  لا تُرجع "unknown" لهذه الحقول إذا كان النص يدل عليها.
- ضع في missing_information فقط الفجوات الحقيقية (التسعير، العملاء، CAC، التكاليف).
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
  "recommended_model": "saas_v1|real_estate_v1|data_center_v1|general_v1",
  "next_questions": ["السؤال الأول؟", "السؤال الثاني؟"]
}
"""

SYSTEM_PROMPT_EN = """
You are an expert business advisor specializing in the Saudi Arabian market.
Your task: understand and classify the project the user describes.

Steps:
1. Read the project description carefully
2. Identify project type (SaaS / Real Estate / Data Center / Retail / Industrial / Services)
3. Identify stage (idea / MVP / operational / expansion)
4. Ask questions appropriate to THIS project type only
5. Identify missing information

Strict rules:
- Prefer inferring stage (idea/mvp/operational/expansion) and decision_goal
  (investment/funding/feasibility/expansion) from the description when clear.
  Avoid returning "unknown" for those fields when the text already implies them.
- Put only true blockers in missing_information (pricing, customers, CAC, costs).
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
  "recommended_model": "saas_v1|real_estate_v1|data_center_v1|general_v1",
  "next_questions": ["Question 1?", "Question 2?"]
}
"""

ARCHETYPE_QUESTIONS = {
    "saas_digital": {
        "ar": [
            "ما سعر الاشتراك الشهري أو السنوي؟",
            "كم عدد العملاء المستهدفين في السنة الأولى؟",
            "ما تكلفة اكتساب العميل الواحد (CAC)؟",
            "ما نسبة التسرب الشهري المتوقعة (Churn)?",
            "ما التكلفة الشهرية للبنية التحتية والـ API؟",
            "ما حجم الفريق والتكلفة التشغيلية؟",
        ],
        "en": [
            "What is the monthly or annual subscription price?",
            "How many customers targeted in year 1?",
            "What is your expected Customer Acquisition Cost (CAC)?",
            "What is your expected monthly churn rate?",
            "What are your monthly infrastructure and API costs?",
            "What is your team size and operational cost?",
        ],
    },
    "real_estate": {
        "ar": [
            "هل الأرض مملوكة أم مستأجرة؟ وما مساحتها؟",
            "ما حالة الرخصة والتصاريح؟",
            "ما تكلفة البناء الإجمالية (BOQ)؟",
            "ما عدد الوحدات وأنواعها؟",
            "ما نسبة الإنجاز الحالية؟",
            "ما متوسط سعر البيع أو الإيجار المستهدف للوحدة؟",
        ],
        "en": [
            "Is the land owned or leased? What is the area?",
            "What is the license and permit status?",
            "What is the total construction cost (BOQ)?",
            "How many units and what types?",
            "What is the current completion percentage?",
            "What is the target sale or rent price per unit?",
        ],
    },
    "data_center": {
        "ar": [
            "ما سعة الطاقة الكهربائية (ميجاواط)؟",
            "ما Tier المستهدف (I/II/III/IV)؟",
            "ما PUE المستهدف؟",
            "ما سعة Rack الإجمالية؟",
            "ما نسبة الإشغال المستهدفة في السنة الأولى؟",
            "ما تكلفة الكيلوواط ساعة؟",
            "ما نموذج الإيراد (Colocation/Wholesale/Retail)?",
        ],
        "en": [
            "What is the power capacity (MW)?",
            "What Tier is targeted (I/II/III/IV)?",
            "What is the target PUE?",
            "What is total Rack capacity?",
            "What is target occupancy in year 1?",
            "What is the cost per kWh?",
            "What is the revenue model (Colocation/Wholesale/Retail)?",
        ],
    },
}


def run_discovery(state: StudyState) -> StudyState:
    # Confirm Profile already accepted the profile — do not re-gate on missing fields.
    if state.profile_confirmed:
        state.phase = "EVIDENCE_REVIEW"
        state.next_action = "review_evidence"
        state.error = None
        return state

    lang = state.language
    system_prompt = SYSTEM_PROMPT_AR if lang == "ar" else SYSTEM_PROMPT_EN
    llm = get_llm("questions")

    context = ""
    if state.profile and state.profile.archetype != "unknown":
        archetype = state.profile.archetype
        questions = ARCHETYPE_QUESTIONS.get(archetype, {}).get(lang, [])
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

        state.profile = ProjectProfile(
            archetype=profile_data.get("archetype", "unknown"),
            sector=profile_data.get("sector", ""),
            stage=stage,
            decision_goal=decision_goal,
            language=lang,
            missing_information=profile_data.get("missing_information", []) or [],
            recommended_model=profile_data.get("recommended_model", ""),
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
