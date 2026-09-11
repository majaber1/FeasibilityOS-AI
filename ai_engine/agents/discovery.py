"""Discovery agent: mandatory archetype classification then structured questions."""
from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

from ..config import get_llm
from ..models.study_state import StudyState, ProjectProfile
from ..archetypes import (
    classify_archetype,
    normalize_archetype,
    questions_for_language,
    ARCHETYPE_LABELS,
    detect_services_variant,
)

SYSTEM_PROMPT_AR = """
أنت مستشار أعمال خبير متخصص في السوق السعودي.
مهمتك: فهم المشروع وتصنيفه ثم طلب معلومات مناسبة لنوعه فقط.

قواعد صارمة:
- صنّف المشروع أولاً إلى أحد: saas_digital | real_estate | data_center | industrial | retail | services | other
- اسأل فقط أسئلة مناسبة لهذا التصنيف
- ممنوع سؤال CAC أو Churn أو ARR أو MRR أو تسعير SaaS لمشاريع العقار أو مراكز البيانات أو الصناعة أو التجزئة
- مشاريع التنقل/التوصيل/الأسواق والاستشارات/الأمن السيبراني/الخدمات المهنية تُصنَّف services وليست saas_digital أو industrial
- لا تخترع أرقاماً مالية دقيقة في هذه المرحلة

أخرج JSON داخل ```json ... ```:
{
  "archetype": "saas_digital|real_estate|data_center|industrial|retail|services|other",
  "sector": "وصف القطاع",
  "stage": "idea|mvp|operational|expansion",
  "decision_goal": "investment|funding|feasibility|expansion",
  "missing_information": ["فجوات حقيقية فقط"],
  "recommended_model": "model_id"
}
"""

SYSTEM_PROMPT_EN = """
You are an expert business advisor for the Saudi market.
Task: understand and classify the project, then ask ONLY archetype-appropriate questions.

Strict rules:
- Classify first into: saas_digital | real_estate | data_center | industrial | retail | services | other
- Ask only questions appropriate for that archetype
- NEVER ask CAC, Churn, ARR, MRR, or SaaS pricing for real estate, data centers, industrial, or retail
- Mobility / ride-hailing / marketplaces AND consulting / cybersecurity / professional services classify as services (NOT saas_digital or industrial)
- Do not invent precise financial numbers in this step

Output JSON inside ```json ... ```:
{
  "archetype": "saas_digital|real_estate|data_center|industrial|retail|services|other",
  "sector": "sector description",
  "stage": "idea|mvp|operational|expansion",
  "decision_goal": "investment|funding|feasibility|expansion",
  "missing_information": ["true gaps only"],
  "recommended_model": "model_id"
}
"""


def run_discovery(state: StudyState) -> StudyState:
    # Once archetype is locked, never re-classify — only advance structured Qs / evidence.
    if state.profile and state.profile.archetype_confirmed:
        if state.profile_confirmed:
            state.phase = "EVIDENCE_REVIEW"
            state.next_action = "review_evidence"
            state.error = None
            return state
        unanswered = _unanswered_required(state)
        if unanswered or (state.profile.missing_information):
            state.phase = "NEEDS_INFORMATION"
            state.next_action = "answer_structured_questions"
        else:
            state.phase = "EVIDENCE_REVIEW"
            state.next_action = "review_evidence"
            state.profile_confirmed = True
        state.error = None
        return state

    lang = state.language
    system_prompt = SYSTEM_PROMPT_AR if lang == "ar" else SYSTEM_PROMPT_EN
    llm = get_llm("classification")

    last_user = _last_user_text(state)
    heuristic = classify_archetype(last_user) if last_user else "other"

    messages = [SystemMessage(content=system_prompt)] + list(state.messages[-8:] if state.messages else [])

    try:
        response = llm.invoke(messages)
        response_text = response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        response_text = (
            f"Classified as {heuristic} via keyword fallback ({e}). "
            "Please confirm the project archetype to continue."
        )
        profile_data = {
            "archetype": heuristic,
            "sector": "",
            "stage": "idea",
            "decision_goal": "feasibility",
            "missing_information": [],
            "recommended_model": f"{heuristic}_v1",
        }
        return _apply_profile(state, profile_data, response_text, lang, heuristic)

    profile_data = _extract_json(response_text) or {}
    llm_arch = normalize_archetype(profile_data.get("archetype"))
    if heuristic in {"services", "real_estate", "data_center", "industrial"} and llm_arch in {
        "saas_digital",
        "other",
        "unknown",
    }:
        chosen = heuristic
    elif llm_arch not in {"other", "unknown"}:
        chosen = llm_arch
    else:
        chosen = heuristic

    profile_data["archetype"] = chosen
    return _apply_profile(state, profile_data, response_text, lang, chosen)


def _apply_profile(
    state: StudyState,
    profile_data: dict,
    response_text: str,
    lang: str,
    archetype: str,
) -> StudyState:
    stage = str(profile_data.get("stage") or "").strip() or "idea"
    decision_goal = str(profile_data.get("decision_goal") or "").strip() or "feasibility"
    if stage.lower() in {"unknown", "n/a", "na", "none", ""}:
        stage = "idea"
    if decision_goal.lower() in {"unknown", "n/a", "na", "none", ""}:
        decision_goal = "feasibility"

    confirmed = bool(state.profile and state.profile.archetype_confirmed)
    # Preserve prior variant if already locked; otherwise detect from user text.
    prior_variant = None
    if state.profile and getattr(state.profile, "services_variant", None):
        prior_variant = state.profile.services_variant
    context_text = _last_user_text(state)
    services_variant = None
    if archetype == "services":
        services_variant = detect_services_variant(context_text, explicit=prior_variant)

    state.profile = ProjectProfile(
        archetype=archetype if archetype != "unknown" else "other",  # type: ignore[arg-type]
        sector=str(profile_data.get("sector") or ""),
        stage=stage,
        decision_goal=decision_goal,
        language=lang,  # type: ignore[arg-type]
        missing_information=list(profile_data.get("missing_information") or []),
        recommended_model=str(profile_data.get("recommended_model") or f"{archetype}_v1"),
        archetype_confirmed=confirmed,
        services_variant=services_variant,
    )

    state.discovery_questions = questions_for_language(
        archetype,
        lang,
        context_text=context_text,
        services_variant=services_variant,
    )

    label = ARCHETYPE_LABELS.get(archetype, ARCHETYPE_LABELS["other"])[
        lang if lang in ("ar", "en") else "en"
    ]
    if not confirmed:
        state.phase = "ARCHETYPE_CLASSIFICATION"
        state.next_action = "confirm_archetype"
        hint = (
            f"تم اقتراح التصنيف: **{label}** (`{archetype}`). أكّد التصنيف ثم أجب على الأسئلة المنظمة."
            if lang == "ar"
            else f"Suggested archetype: **{label}** (`{archetype}`). Confirm the archetype, then answer the structured questions."
        )
        state.messages.append(AIMessage(content=f"{response_text}\n\n{hint}"))
    elif state.profile.missing_information or _unanswered_required(state):
        state.phase = "NEEDS_INFORMATION"
        state.next_action = "answer_structured_questions"
        state.messages.append(AIMessage(content=response_text))
    else:
        state.phase = "EVIDENCE_REVIEW"
        state.next_action = "review_evidence"
        state.messages.append(AIMessage(content=response_text))

    state.error = None
    return state


def _unanswered_required(state: StudyState) -> bool:
    answers = state.structured_answers or {}
    for q in state.discovery_questions or []:
        if q.get("required", True) and not q.get("answered") and q.get("id") not in answers:
            return True
    return False


def _last_user_text(state: StudyState) -> str:
    for msg in reversed(list(state.messages or [])):
        role = getattr(msg, "type", None) or getattr(msg, "role", None)
        content = getattr(msg, "content", None)
        if isinstance(msg, dict):
            role = msg.get("type") or msg.get("role")
            content = msg.get("content")
        if role in {"human", "user"} and content:
            return str(content)
    return ""


def _extract_json(text: str) -> dict | None:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None
