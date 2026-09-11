"""Discovery agent: mandatory archetype classification then structured questions."""
from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

from ..config import get_llm, invoke_llm
from ..models.study_state import StudyState, ProjectProfile
from ..archetypes import (
    classify_archetype,
    normalize_archetype,
    questions_for_language,
    ARCHETYPE_LABELS,
    detect_services_variant,
)
from ..utils.safe_messages import (
    ai_unavailable_classify_message,
    sanitize_chat_content,
    sanitize_error_for_user,
)
from ..provider import ProviderUnavailableError

import logging

logger = logging.getLogger(__name__)

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
        # Discovery Advisor interview is the source of truth — do not gate on
        # the legacy static missing_information list once questions exist.
        if unanswered:
            state.phase = "NEEDS_INFORMATION"
            state.next_action = "answer_structured_questions"
        else:
            state.phase = "EVIDENCE_REVIEW"
            state.next_action = "review_evidence"
            state.profile_confirmed = True
            if state.profile:
                state.profile.missing_information = []
        state.error = None
        return state

    lang = state.language
    system_prompt = SYSTEM_PROMPT_AR if lang == "ar" else SYSTEM_PROMPT_EN

    last_user = _last_user_text(state)
    heuristic = classify_archetype(last_user) if last_user else "other"

    messages = [SystemMessage(content=system_prompt)] + list(state.messages[-8:] if state.messages else [])

    try:
        response = invoke_llm("classification", messages, context="discovery.classify")
        response_text = response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        # Provider / rate-limit failure: do NOT silently lock a classification.
        sanitize_error_for_user(e, language=lang, context="discovery.classify")
        # Prefer mobility-safe heuristic for Uber-like text, still require confirmation.
        if _has_any(last_user or "", _MOBILITY_SIGNALS) and not _has_any(
            last_user or "", _STRONG_DC_SIGNALS
        ):
            heuristic = "services"
        response_text = ai_unavailable_classify_message(lang)
        profile_data = {
            "archetype": heuristic if heuristic not in {"other", "unknown"} else "other",
            "sector": "",
            "stage": "idea",
            "decision_goal": "feasibility",
            "missing_information": [],
            "recommended_model": f"{heuristic}_v1",
        }
        return _apply_profile(
            state,
            profile_data,
            response_text,
            lang,
            profile_data["archetype"],
            ambiguous=True,
            clarify_reason="llm_unavailable",
        )

    profile_data = _extract_json(response_text) or {}
    llm_arch = normalize_archetype(profile_data.get("archetype"))
    chosen, ambiguous, clarify_reason = _resolve_archetype(heuristic, llm_arch, last_user)
    profile_data["archetype"] = chosen
    # Keep structured model JSON out of chat; store it only in profile / audit fields.
    public_text = sanitize_chat_content(response_text, language=lang) or (
        "تم تحليل وصف المشروع واقتراح التصنيف."
        if lang == "ar"
        else "Project description reviewed and an archetype is suggested."
    )
    return _apply_profile(
        state, profile_data, public_text, lang, chosen,
        ambiguous=ambiguous, clarify_reason=clarify_reason,
        heuristic=heuristic, llm_arch=llm_arch,
    )


def _apply_profile(
    state: StudyState,
    profile_data: dict,
    response_text: str,
    lang: str,
    archetype: str,
    *,
    ambiguous: bool = False,
    clarify_reason: str | None = None,
    heuristic: str | None = None,
    llm_arch: str | None = None,
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
        if ambiguous:
            hint = f"{hint}\n\n{_confirmation_question(lang, clarify_reason, heuristic, llm_arch, archetype)}"
        safe = sanitize_chat_content(response_text, language=lang) or ""
        content = f"{safe}\n\n{hint}".strip() if safe else hint
        state.messages.append(AIMessage(content=content))
    elif _unanswered_required(state):
        state.phase = "NEEDS_INFORMATION"
        state.next_action = "answer_structured_questions"
        # Soft hints only — interview UI replaces the static missing list.
        safe = sanitize_chat_content(response_text, language=lang)
        if safe:
            state.messages.append(AIMessage(content=safe))
    else:
        state.phase = "EVIDENCE_REVIEW"
        state.next_action = "review_evidence"
        if state.profile:
            state.profile.missing_information = []
        safe = sanitize_chat_content(response_text, language=lang)
        if safe:
            state.messages.append(AIMessage(content=safe))

    state.error = None
    return state


# Ride-hailing / mobility / marketplace signals — must never resolve to data_center.
_MOBILITY_SIGNALS = (
    "uber", "careem", "ride-hailing", "ride hailing", "rideshare", "ride share",
    "taxi", "take rate", "take-rate", "monthly trips", "drivers", "delivery platform",
    "marketplace", "two-sided marketplace", "gig platform",
    "سائق", "مشاوير", "توصيل", "سوق إلكتروني",
)
# Consulting / cybersecurity / professional services — never silently become data_center.
_PROFESSIONAL_SERVICES_SIGNALS = (
    "consulting", "consultancy", "cybersecurity", "cyber security", "cyber-security",
    "professional services", "managed services", "managed security", "managed soc",
    "mssp", "soc services", "penetration test", "retainer", "advisory",
    "billable consultants", "استشارات", "خدمات مهنية", "أمن سيبراني",
)
_STRONG_DC_SIGNALS = (
    "data center", "datacenter", "مركز بيانات", "colocation", "colo ",
    "hyperscaler", "pue", "tier iii", "tier 3", "tier iv", "tier 4",
    "rack count", "mw capacity", "it load", "power capacity",
)


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    t = (text or "").lower()
    return any(n in t for n in needles)


def _resolve_archetype(
    heuristic: str,
    llm_arch: str,
    text: str | None,
) -> tuple[str, bool, str | None]:
    """Validate classification confidence before discovery.

    Returns (chosen, needs_confirmation_question, reason).
    Uber / mobility descriptions must never become data_center.
    """
    t = text or ""
    mobility = _has_any(t, _MOBILITY_SIGNALS)
    professional = _has_any(t, _PROFESSIONAL_SERVICES_SIGNALS)
    # Negated "not a data center" must not count as a strong DC signal.
    t_dc = re.sub(
        r"\bnot\s+(a\s+)?(data[\s\-]?center|datacenter|colo(?:cation)?)\b",
        " ",
        (t or "").lower(),
    )
    strong_dc = _has_any(t_dc, _STRONG_DC_SIGNALS)

    if (mobility or professional) and not strong_dc:
        if heuristic == "data_center" or llm_arch == "data_center":
            reason = "mobility_vs_data_center" if mobility else "services_vs_data_center"
            logger.info(
                "classification_guard blocked data_center for %s text "
                "(heuristic=%s llm=%s)",
                "mobility" if mobility else "professional_services",
                heuristic,
                llm_arch,
            )
            return "services", True, reason

    if mobility and not strong_dc:
        if heuristic == "services":
            if llm_arch in {"saas_digital", "industrial", "other", "unknown", "retail"}:
                return (
                    "services",
                    llm_arch not in {"services", "other", "unknown"},
                    "mobility_keep_services",
                )
            if llm_arch == "services":
                return "services", False, None
            if llm_arch not in {"other", "unknown"} and llm_arch != "services":
                return "services", True, "mobility_llm_conflict"

    if professional and not strong_dc and heuristic == "services":
        if llm_arch in {"saas_digital", "industrial", "other", "unknown", "retail"}:
            return (
                "services",
                llm_arch not in {"services", "other", "unknown"},
                "professional_keep_services",
            )
        if llm_arch == "services":
            return "services", False, None

    if heuristic == "services" and llm_arch == "data_center" and not strong_dc:
        logger.info("classification_guard blocked services→data_center LLM override")
        return "services", True, "services_vs_data_center"

    if heuristic in {"services", "real_estate", "data_center", "industrial"} and llm_arch in {
        "saas_digital",
        "other",
        "unknown",
    }:
        return heuristic, False, None

    if llm_arch not in {"other", "unknown"}:
        chosen = llm_arch
    else:
        chosen = heuristic

    ambiguous = (
        heuristic not in {"other", "unknown"}
        and llm_arch not in {"other", "unknown"}
        and heuristic != llm_arch
    )
    if ambiguous:
        if {heuristic, llm_arch} == {"services", "data_center"}:
            chosen = "services" if not strong_dc else "data_center"
            return chosen, True, "services_data_center_ambiguous"
        return chosen, True, "heuristic_llm_disagree"

    if chosen in {"other", "unknown"}:
        return "other", True, "low_confidence_other"
    return chosen, False, None


def _confirmation_question(
    lang: str,
    reason: str | None,
    heuristic: str | None,
    llm_arch: str | None,
    chosen: str,
) -> str:
    if reason in {
        "mobility_vs_data_center",
        "services_vs_data_center",
        "services_data_center_ambiguous",
    }:
        if lang == "ar":
            return (
                "للتأكيد قبل المتابعة: هل المشروع منصة تنقل/توصيل أو خدمات مهنية، "
                "أم مركز بيانات / بنية تحتية (colo)؟ اختر التصنيف الصحيح أدناه."
            )
        return (
            "Before we continue: is this a ride-hailing / delivery / professional services business, "
            "or a data center / colo facility? Please confirm the correct archetype below."
        )
    if reason == "llm_unavailable":
        if lang == "ar":
            return (
                "الذكاء الاصطناعي غير متاح مؤقتاً. تم اقتراح تصنيف أولي فقط — "
                "يرجى تأكيد نوع المشروع أدناه قبل المتابعة. لن نثبّت التصنيف دون تأكيدك."
            )
        return (
            "AI is temporarily unavailable. A provisional archetype is suggested only — "
            "please confirm the project type below before continuing. "
            "We will not lock classification without your confirmation."
        )
    if reason == "heuristic_llm_disagree":
        h = heuristic or "other"
        l = llm_arch or "other"
        if lang == "ar":
            return (
                f"التصنيف غير حاسم (تقريبي: `{h}`، نموذج: `{l}`). "
                f"المقترح الآن: `{chosen}`. هل هذا صحيح؟ أكّد أو اختر التصنيف المناسب."
            )
        return (
            f"Classification is ambiguous (keyword: `{h}`, model: `{l}`). "
            f"Suggested now: `{chosen}`. Is that correct? Confirm or pick the right archetype."
        )
    if lang == "ar":
        return "التصنيف غير مؤكد بعد. يرجى تأكيد نوع المشروع قبل بدء أسئلة الاكتشاف."
    return "Classification confidence is low. Please confirm the project archetype before discovery questions."


def _unanswered_required(state: StudyState) -> bool:
    from ai_engine.discovery import unanswered_required

    return bool(unanswered_required(state.discovery_questions, state.structured_answers))


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
