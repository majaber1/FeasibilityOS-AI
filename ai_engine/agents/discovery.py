from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..config import get_llm
from ..models.study_state import DiscoveryQuestion, ProjectProfile, StudyState
from .discovery_catalog import (
    build_questions_for_archetype,
    classify_archetype_from_text,
)

SYSTEM_PROMPT_AR = """
أنت مستشار أعمال خبير متخصص في السوق السعودي.
مهمتك: فهم المشروع وتصنيفه فقط — لا تكتب قوائم Markdown للأسئلة.

أخرج JSON داخل ```json ... ``` فقط بهذا الشكل:
{
  "archetype": "saas_digital|real_estate|data_center|government_contract|retail|industrial|services|franchise|unknown",
  "sector": "وصف القطاع",
  "stage": "idea|mvp|operational|expansion",
  "decision_goal": "investment|funding|feasibility|expansion",
  "missing_information": ["فجوات حقيقية فقط"],
  "recommended_model": "saas_v1|real_estate_v1|data_center_v1|government_v1|general_v1",
  "summary": "جملة أو جملتان تلخّص فهمك للمشروع بدون أسئلة مرقّمة وبدون عناوين Markdown"
}

قواعد:
- صنّف حسب نوع المشروع الحقيقي (تقنية / عقار / مركز بيانات / ترسية حكومية).
- لا تكتب ### أو قوائم 1. 2. 3. خارج JSON.
- لا تخترع أرقاماً مالية.
"""

SYSTEM_PROMPT_EN = """
You are an expert Saudi-market business advisor.
Classify the project only — do not emit Markdown clarification lists.

Output JSON inside ```json ... ``` only:
{
  "archetype": "saas_digital|real_estate|data_center|government_contract|retail|industrial|services|franchise|unknown",
  "sector": "sector description",
  "stage": "idea|mvp|operational|expansion",
  "decision_goal": "investment|funding|feasibility|expansion",
  "missing_information": ["true gaps only"],
  "recommended_model": "saas_v1|real_estate_v1|data_center_v1|government_v1|general_v1",
  "summary": "One or two sentences summarizing the project with no numbered questions and no Markdown headings"
}

Rules:
- Classify by real project type (tech / real estate / data center / government award).
- Do not write ### or numbered lists outside JSON.
- Do not invent financial numbers.
"""

MODEL_BY_ARCHETYPE = {
    "saas_digital": "saas_v1",
    "real_estate": "real_estate_v1",
    "data_center": "data_center_v1",
    "government_contract": "government_v1",
}


def _user_text(state: StudyState) -> str:
    parts: list[str] = []
    for msg in state.messages or []:
        content = getattr(msg, "content", None)
        if content and (getattr(msg, "type", "") in {"human", "user"} or isinstance(msg, HumanMessage)):
            parts.append(str(content))
    return "\n".join(parts)


def _clean_summary(text: str, language: str) -> str:
    cleaned = re.sub(r"```json.*?```", "", text or "", flags=re.DOTALL).strip()
    cleaned = re.sub(r"^#{1,6}\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    if cleaned:
        return cleaned
    return (
        "تم تصنيف المشروع. أجب عن الأسئلة المنظمة أدناه لإكمال المعلومات الناقصة."
        if language == "ar"
        else "Project classified. Answer the structured questions below to complete missing information."
    )


def run_discovery(state: StudyState) -> StudyState:
    if state.profile_confirmed:
        state.phase = "EVIDENCE_REVIEW"
        state.next_action = "review_evidence"
        state.error = None
        return state

    # If structured questions already exist and some remain unanswered, stay gated.
    pending = [q for q in (state.discovery_questions or []) if q.required and not q.answered]
    if state.discovery_questions and pending:
        state.phase = "NEEDS_INFORMATION"
        state.next_action = "answer_structured_questions"
        return state

    lang = state.language
    system_prompt = SYSTEM_PROMPT_AR if lang == "ar" else SYSTEM_PROMPT_EN
    user_blob = _user_text(state)
    heuristic = classify_archetype_from_text(user_blob)

    profile_data: dict | None = None
    response_text = ""
    try:
        llm = get_llm("questions")
        messages = [SystemMessage(content=system_prompt)] + list(state.messages)
        response = llm.invoke(messages)
        response_text = response.content if hasattr(response, "content") else str(response)
        profile_data = _extract_json(response_text)
    except Exception as e:
        state.error = None
        state.blocking_reason = f"discovery_provider_unavailable:{e}"
        response_text = ""
        profile_data = None

    if not profile_data:
        profile_data = {
            "archetype": heuristic if heuristic != "unknown" else "saas_digital",
            "sector": "",
            "stage": "idea",
            "decision_goal": "feasibility",
            "missing_information": [],
            "recommended_model": MODEL_BY_ARCHETYPE.get(heuristic, "general_v1"),
            "summary": "",
        }

    archetype = str(profile_data.get("archetype") or heuristic or "unknown")
    if archetype == "unknown" and heuristic != "unknown":
        archetype = heuristic
    if archetype not in {
        "saas_digital",
        "real_estate",
        "data_center",
        "government_contract",
        "retail",
        "industrial",
        "services",
        "franchise",
        "unknown",
    }:
        archetype = heuristic if heuristic != "unknown" else "unknown"

    stage = str(profile_data.get("stage") or "").strip() or "idea"
    decision_goal = str(profile_data.get("decision_goal") or "").strip() or "feasibility"
    if stage.lower() in {"unknown", "n/a", "na", "none", ""}:
        stage = "idea"
    if decision_goal.lower() in {"unknown", "n/a", "na", "none", ""}:
        decision_goal = "feasibility"

    questions = [
        DiscoveryQuestion(**q)
        for q in build_questions_for_archetype(archetype, language=lang)
    ]
    state.discovery_questions = questions
    missing = [q.prompt for q in questions if q.required]
    state.profile = ProjectProfile(
        archetype=archetype,  # type: ignore[arg-type]
        sector=str(profile_data.get("sector") or ""),
        stage=stage,
        decision_goal=decision_goal,
        language=lang,
        missing_information=missing,
        recommended_model=str(
            profile_data.get("recommended_model")
            or MODEL_BY_ARCHETYPE.get(archetype, "general_v1")
        ),
        structured_answers={},
    )
    state.workflow_meta = dict(state.workflow_meta or {})
    state.workflow_meta["discovery_questions"] = [q.model_dump() for q in questions]

    summary = str(profile_data.get("summary") or "").strip() or _clean_summary(response_text, lang)
    state.messages.append(AIMessage(content=summary))
    state.phase = "NEEDS_INFORMATION" if missing else "EVIDENCE_REVIEW"
    state.next_action = "answer_structured_questions" if missing else "review_evidence"
    state.error = None
    return state


def apply_structured_answers(state: StudyState, answers: list[dict]) -> StudyState:
    """Persist structured answers onto discovery questions + profile."""
    by_id = {a.get("id"): a.get("value") for a in answers if a.get("id")}
    updated: list[DiscoveryQuestion] = []
    structured = dict((state.profile.structured_answers if state.profile else {}) or {})
    for q in state.discovery_questions or []:
        if q.id in by_id:
            value = by_id[q.id]
            q.answer = value
            q.answered = value is not None and value != "" and value != []
            key = q.field_key or q.id
            structured[key] = value
            if key == "stage" and isinstance(value, str) and state.profile:
                state.profile.stage = value
        updated.append(q)
    state.discovery_questions = updated
    if state.profile:
        state.profile.structured_answers = structured
        pending = [q.prompt for q in updated if q.required and not q.answered]
        state.profile.missing_information = pending
    state.workflow_meta = dict(state.workflow_meta or {})
    state.workflow_meta["discovery_questions"] = [q.model_dump() for q in updated]
    state.phase = "NEEDS_INFORMATION"
    state.next_action = "answer_structured_questions"
    if state.profile and not state.profile.missing_information:
        state.next_action = "choose_information_gate"
    return state


def _extract_json(text: str) -> dict | None:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Tolerate raw JSON object
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
    except Exception:
        return None
    return None
