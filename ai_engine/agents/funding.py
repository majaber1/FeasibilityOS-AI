"""Intelligent Funding for V2 studies — reuses funding-engine matcher (no duplicate engine)."""
from __future__ import annotations

import sys
from pathlib import Path

from langchain_core.messages import AIMessage

from ..models.study_state import StudyState

_ENGINE_ROOT = Path(__file__).resolve().parents[2] / "funding-engine"
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

from matcher import match  # noqa: E402


ARCHETYPE_INDUSTRY = {
    "saas_digital": "saas",
    "real_estate": "industrial",
    "data_center": "technology",
    "government_contract": "general",
    "retail": "retail",
    "industrial": "industrial",
    "services": "services",
    "franchise": "retail",
    "unknown": "general",
}

ARCHETYPE_STAGE = {
    "idea": "idea",
    "mvp": "mvp",
    "operational": "early_revenue",
    "expansion": "growth",
    "يعمل بالفعل": "early_revenue",
    "توسع": "growth",
    "فكرة": "idea",
}


def _blockers_for(state: StudyState) -> list[str]:
    blockers: list[str] = []
    fr = state.financial_results or {}
    if fr.get("status") == "MODEL_INCOMPLETE" or not fr.get("analysis_complete"):
        blockers.append("financial_model_incomplete")
    if state.verdict in {None, "INSUFFICIENT_EVIDENCE", "NEED_MORE_VALIDATION"}:
        blockers.append("decision_not_ready")
    if state.verdict == "NO_GO":
        blockers.append("verdict_no_go")
    answers = (state.profile.structured_answers if state.profile else {}) or {}
    archetype = state.profile.archetype if state.profile else "unknown"
    if archetype == "government_contract" and not answers.get("award_value"):
        blockers.append("missing_award_value")
    if archetype == "real_estate" and not (
        answers.get("remaining_construction_cost") or answers.get("required_funding")
    ):
        blockers.append("missing_construction_or_funding_need")
    if archetype == "saas_digital" and not answers.get("funding_goal"):
        # soft blocker — explain only
        pass
    return blockers


def run_funding(state: StudyState) -> StudyState:
    """Match funding programs from project archetype + stage + decision context."""
    lang = state.language
    profile = state.profile
    archetype = profile.archetype if profile else "unknown"
    stage_raw = (profile.stage if profile else "idea") or "idea"
    stage = ARCHETYPE_STAGE.get(stage_raw, ARCHETYPE_STAGE.get(stage_raw.lower(), "idea"))
    industry = ARCHETYPE_INDUSTRY.get(archetype, "general")
    answers = (profile.structured_answers if profile else {}) or {}

    has_mvp = stage in {"mvp", "early_revenue", "growth"} or str(
        answers.get("project_stage") or answers.get("stage") or ""
    ).lower() in {"mvp", "يعمل بالفعل", "already operating", "expansion", "توسع"}

    matches = match(
        industry=industry,
        stage=stage,
        has_mvp=has_mvp,
        has_technical_team=True,
    )

    # Archetype-specific program emphasis (still same matcher — post-filter labels).
    emphasis: list[str] = []
    if archetype == "saas_digital":
        emphasis = ["NTDP", "SVC", "RDIA", "MONSHAAT"]
    elif archetype == "real_estate":
        emphasis = ["KAFALAH", "MONSHAAT"]
    elif archetype == "data_center":
        emphasis = ["NTDP", "KAFALAH", "SVC"]
    elif archetype == "government_contract":
        emphasis = ["KAFALAH", "MONSHAAT"]

    if emphasis:
        rank = {code: i for i, code in enumerate(emphasis)}
        matches = sorted(
            matches,
            key=lambda m: (rank.get(m.get("program"), 99), -float(m.get("score_percent") or 0)),
        )

    blockers = _blockers_for(state)
    top = matches[0] if matches else None
    score = float(top.get("score_percent") or 0) if top else 0.0
    if blockers:
        score = min(score, 40.0)

    readiness = {
        "score_percent": score,
        "score_explained": True,
        "blockers": blockers,
        "blocker_labels": {
            "financial_model_incomplete": (
                "النموذج المالي غير مكتمل" if lang == "ar" else "Financial model incomplete"
            ),
            "decision_not_ready": (
                "القرار الاستثماري غير جاهز" if lang == "ar" else "Investment decision not ready"
            ),
            "verdict_no_go": (
                "قرار عدم الجدوى يمنع التمويل" if lang == "ar" else "NO_GO verdict blocks funding"
            ),
            "missing_award_value": (
                "قيمة الترسية غير معروفة" if lang == "ar" else "Award value missing"
            ),
            "missing_construction_or_funding_need": (
                "احتياج التمويل/تكلفة البناء المتبقية غير محددة"
                if lang == "ar"
                else "Remaining construction cost / funding need missing"
            ),
        },
        "archetype": archetype,
        "industry_used": industry,
        "stage_used": stage,
        "use_of_funds_hints": _use_of_funds(archetype, lang),
        "matches": matches[:8],
    }

    state.workflow_meta = dict(state.workflow_meta or {})
    state.workflow_meta["funding"] = readiness
    state.phase = "FUNDING_READY"
    state.next_action = "review_funding_then_report"

    if lang == "ar":
        lines = [
            f"جاهزية التمويل: {score:.0f}% — مفسَّرة وليست نسبة مبهمة.",
        ]
        if blockers:
            lines.append("العوائق:")
            for b in blockers:
                lines.append(f"- {readiness['blocker_labels'].get(b, b)}")
        if top:
            lines.append(f"أقرب برنامج: {top.get('name_ar') or top.get('name')} ({top.get('score_percent')}%).")
            for r in (top.get("reasons") or [])[:3]:
                lines.append(f"  · {r}")
        msg = "\n".join(lines)
    else:
        lines = [
            f"Funding readiness: {score:.0f}% — explained score, not a vague percentage.",
        ]
        if blockers:
            lines.append("Blockers:")
            for b in blockers:
                lines.append(f"- {readiness['blocker_labels'].get(b, b)}")
        if top:
            lines.append(f"Top program: {top.get('name')} ({top.get('score_percent')}%).")
            for r in (top.get("reasons") or [])[:3]:
                lines.append(f"  · {r}")
        msg = "\n".join(lines)

    state.messages.append(AIMessage(content=msg))
    state.error = None
    return state


def _use_of_funds(archetype: str, lang: str) -> list[str]:
    if lang == "ar":
        mapping = {
            "saas_digital": ["تطوير المنتج", "اكتساب العملاء", "تكاليف سحابة/ذكاء اصطناعي", "فريق"],
            "real_estate": ["إكمال البناء", "رأس مال عامل للمبيعات", "ضمانات", "تصاريح"],
            "data_center": ["CAPEX للبنية", "طاقة وتبريد", "ربط شبكي", "تشغيل"],
            "government_contract": ["تمويل رأس المال العامل", "ضمانات حسن تنفيذ", "فجوة التدفق النقدي"],
        }
    else:
        mapping = {
            "saas_digital": ["Product development", "Customer acquisition", "Cloud/AI costs", "Team"],
            "real_estate": ["Complete construction", "Sales working capital", "Guarantees", "Permits"],
            "data_center": ["Infrastructure CAPEX", "Power/cooling", "Connectivity", "Operations"],
            "government_contract": ["Working capital", "Performance guarantees", "Cash-flow gap"],
        }
    return mapping.get(archetype, mapping.get("saas_digital", []))
