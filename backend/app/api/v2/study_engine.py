from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, UniqueConstraint, text
from sqlalchemy.orm import Session

from app.db import DB_ENABLED, SessionLocal, Base
from ..auth import get_current_user

router = APIRouter(prefix="/api/v2/studies", tags=["v2-studies"])


def _safe_ai_error(exc, language: str = "en", context: str = "") -> str:
    """User-safe AI error for API payloads; technical detail stays in logs only."""
    try:
        from ai_engine.utils.safe_messages import sanitize_error_for_user
        return sanitize_error_for_user(exc, language=language, context=context)
    except Exception:
        import logging
        logging.getLogger(__name__).warning("AI error (%s): %s", context, exc)
        return (
            "تعذر إكمال خطوة الذكاء الاصطناعي حالياً. حاول مرة أخرى بعد لحظات."
            if (language or "en").startswith("ar")
            else "We could not complete this AI step right now. Please try again in a moment."
        )



class StudyStateRow(Base):
    __tablename__ = "study_states_v2"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    study_id = Column(String(64), unique=True, nullable=False, index=True)
    project_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    language = Column(String(5), nullable=False, server_default="ar")
    phase = Column(String(32), nullable=False, server_default="DRAFT")
    phase_history = Column(JSON, nullable=False, server_default="[]")
    profile_json = Column(JSON, nullable=True)
    profile_confirmed = Column(Boolean, nullable=False, server_default=text("false"))
    claims_json = Column(JSON, nullable=False, server_default="[]")
    evidence_approved = Column(Boolean, nullable=False, server_default=text("false"))
    assumptions_json = Column(JSON, nullable=False, server_default="[]")
    assumptions_approved = Column(Boolean, nullable=False, server_default=text("false"))
    assumptions_version = Column(Integer, nullable=False, server_default=text("0"))
    discovery_questions_json = Column(JSON, nullable=False, server_default="[]")
    structured_answers_json = Column(JSON, nullable=False, server_default="{}")
    financial_results_json = Column(JSON, nullable=True)
    verdict = Column(String(32), nullable=True)
    decision_rationale = Column(Text, nullable=True)
    decision_conditions = Column(JSON, nullable=False, server_default="[]")
    decision_risks = Column(JSON, nullable=False, server_default="[]")
    decision_version = Column(Integer, nullable=False, server_default=text("0"))
    messages_json = Column(JSON, nullable=False, server_default="[]")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class StudyVersionRow(Base):
    __tablename__ = "study_state_versions"
    __table_args__ = (
        UniqueConstraint("study_id", "version", name="uq_study_version"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    study_id = Column(String(64), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    phase = Column(String(32), nullable=False)
    snapshot_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


_fallback_studies: dict[str, dict] = {}


def _get_db_session() -> Session | None:
    if not DB_ENABLED or SessionLocal is None:
        return None
    return SessionLocal()


def _load_study(study_id: str, user_id: str) -> dict | None:
    db = _get_db_session()
    if db is not None:
        try:
            row = db.query(StudyStateRow).filter_by(study_id=study_id, user_id=user_id).first()
            if row:
                record = _row_to_dict(row)
                # Phase 8A: restore research_* / knowledge_context from latest version
                # snapshot (full state_dict). Row columns predate these fields.
                try:
                    last = (
                        db.query(StudyVersionRow)
                        .filter_by(study_id=study_id)
                        .order_by(StudyVersionRow.version.desc())
                        .first()
                    )
                    snap = getattr(last, "snapshot_json", None) if last else None
                    if isinstance(snap, dict):
                        state = record.setdefault("state", {})
                        for key in (
                            "research_context",
                            "research_status",
                            "research_attempts",
                            "knowledge_context",
                        ):
                            if key in snap and snap[key] is not None:
                                state[key] = snap[key]
                except Exception:
                    pass
                return record
        except Exception:
            pass
        finally:
            db.close()
    return _fallback_studies.get(study_id)


def _save_study(study_id: str, state_dict: dict, user_id: str):
    now = datetime.now(timezone.utc).isoformat()
    db = _get_db_session()
    if db is not None:
        try:
            row = db.query(StudyStateRow).filter_by(study_id=study_id).first()
            if row:
                row.language = state_dict.get("language", "ar")
                row.phase = state_dict.get("phase", "DRAFT")
                row.phase_history = state_dict.get("phase_history", [])
                row.profile_json = state_dict.get("profile")
                row.profile_confirmed = state_dict.get("profile_confirmed", False)
                row.claims_json = [c if isinstance(c, dict) else c for c in state_dict.get("claims", [])]
                row.evidence_approved = state_dict.get("evidence_approved", False)
                row.assumptions_json = [a if isinstance(a, dict) else a for a in state_dict.get("assumptions", [])]
                row.assumptions_approved = state_dict.get("assumptions_approved", False)
                row.assumptions_version = state_dict.get("assumptions_version", 0)
                row.discovery_questions_json = state_dict.get("discovery_questions", [])
                row.structured_answers_json = state_dict.get("structured_answers", {})
                row.financial_results_json = state_dict.get("financial_results")
                row.verdict = state_dict.get("verdict")
                row.decision_rationale = state_dict.get("decision_rationale")
                row.decision_conditions = state_dict.get("decision_conditions", [])
                row.decision_risks = state_dict.get("decision_risks", [])
                row.decision_version = state_dict.get("decision_version", 0)
                row.messages_json = _serialize_messages(state_dict.get("messages", []))
                row.error = state_dict.get("error")
                row.updated_at = datetime.now(timezone.utc)
            else:
                row = StudyStateRow(
                    study_id=study_id,
                    project_id=state_dict.get("project_id", ""),
                    user_id=user_id,
                    language=state_dict.get("language", "ar"),
                    phase=state_dict.get("phase", "DRAFT"),
                    phase_history=state_dict.get("phase_history", []),
                    profile_json=state_dict.get("profile"),
                    profile_confirmed=state_dict.get("profile_confirmed", False),
                    claims_json=[c if isinstance(c, dict) else c for c in state_dict.get("claims", [])],
                    evidence_approved=state_dict.get("evidence_approved", False),
                    assumptions_json=[a if isinstance(a, dict) else a for a in state_dict.get("assumptions", [])],
                    assumptions_approved=state_dict.get("assumptions_approved", False),
                    assumptions_version=state_dict.get("assumptions_version", 0),
                    discovery_questions_json=state_dict.get("discovery_questions", []),
                    structured_answers_json=state_dict.get("structured_answers", {}),
                    financial_results_json=state_dict.get("financial_results"),
                    verdict=state_dict.get("verdict"),
                    decision_rationale=state_dict.get("decision_rationale"),
                    decision_conditions=state_dict.get("decision_conditions", []),
                    decision_risks=state_dict.get("decision_risks", []),
                    decision_version=state_dict.get("decision_version", 0),
                    messages_json=_serialize_messages(state_dict.get("messages", [])),
                    error=state_dict.get("error"),
                )
                db.add(row)

            last_ver = db.query(StudyVersionRow).filter_by(study_id=study_id).order_by(StudyVersionRow.version.desc()).first()
            version_num = (last_ver.version + 1) if last_ver else 1
            version_row = StudyVersionRow(
                study_id=study_id,
                version=version_num,
                phase=state_dict.get("phase", "DRAFT"),
                snapshot_json=state_dict,
            )
            db.add(version_row)
            db.commit()
            return
        except Exception:
            db.rollback()
        finally:
            db.close()

    _fallback_studies[study_id] = {
        "state": state_dict,
        "user_id": user_id,
        "created_at": _fallback_studies.get(study_id, {}).get("created_at", now),
        "updated_at": now,
    }


def _serialize_messages(messages) -> list:
    result = []
    for msg in messages:
        if isinstance(msg, dict):
            result.append(msg)
        elif hasattr(msg, "type") and hasattr(msg, "content"):
            result.append({"type": msg.type, "content": msg.content})
        else:
            result.append({"type": "unknown", "content": str(msg)})
    return result


def _row_to_dict(row: StudyStateRow) -> dict:
    return {
        "state": {
            "study_id": row.study_id,
            "project_id": row.project_id,
            "user_id": row.user_id,
            "language": row.language,
            "phase": row.phase,
            "phase_history": row.phase_history or [],
            "profile": row.profile_json,
            "profile_confirmed": row.profile_confirmed,
            "claims": row.claims_json or [],
            "evidence_approved": row.evidence_approved,
            "assumptions": row.assumptions_json or [],
            "assumptions_approved": row.assumptions_approved,
            "assumptions_version": getattr(row, "assumptions_version", 0) or 0,
            "discovery_questions": getattr(row, "discovery_questions_json", None) or [],
            "structured_answers": getattr(row, "structured_answers_json", None) or {},
            "financial_results": row.financial_results_json,
            "verdict": row.verdict,
            "decision_rationale": row.decision_rationale,
            "decision_conditions": row.decision_conditions or [],
            "decision_risks": row.decision_risks or [],
            "decision_version": row.decision_version,
            "messages": row.messages_json or [],
            "error": row.error,
        },
        "user_id": row.user_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _list_user_studies(user_id: str) -> list[dict]:
    db = _get_db_session()
    if db is not None:
        try:
            rows = db.query(StudyStateRow).filter_by(user_id=user_id).order_by(StudyStateRow.updated_at.desc()).all()
            return [
                {
                    "study_id": r.study_id,
                    "project_id": r.project_id,
                    "phase": r.phase,
                    "archetype": (r.profile_json or {}).get("archetype") if isinstance(r.profile_json, dict) else None,
                    "verdict": r.verdict,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in rows
            ]
        except Exception:
            pass
        finally:
            db.close()

    results = []
    for sid, record in _fallback_studies.items():
        if record["user_id"] == user_id:
            s = record["state"]
            results.append({
                "study_id": sid,
                "project_id": s.get("project_id"),
                "phase": s.get("phase"),
                "archetype": (s.get("profile") or {}).get("archetype") if isinstance(s.get("profile"), dict) else None,
                "verdict": s.get("verdict"),
                "created_at": record.get("created_at"),
                "updated_at": record.get("updated_at"),
            })
    return results


class StudyCreateRequest(BaseModel):
    project_id: str
    language: str = "ar"
    description: str = ""


class StudyMessageRequest(BaseModel):
    message: str
    language: Optional[str] = None


class StudyApprovalRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None


class ArchetypeSelectRequest(BaseModel):
    archetype: str
    approved: bool = True


class StructuredAnswersRequest(BaseModel):
    answers: dict = {}
    mark_answered: bool = True
    # Question ids the user asked the AI to estimate (reuse Assumption Engine).
    ai_estimates: list[str] = []


class AssumptionEditRequest(BaseModel):
    key: str
    value: str
    low: Optional[str] = None
    base: Optional[str] = None
    high: Optional[str] = None
    explanation: Optional[str] = None


class AssumptionActionRequest(BaseModel):
    """Per-card actions using the existing Assumption fields (no status enum)."""
    key: str
    action: str  # approve | reject | regenerate
    value: Optional[str] = None
    explanation: Optional[str] = None



def _normalize_profile_label(value: str | None, *, fallback: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned or cleaned.lower() in {"unknown", "n/a", "na", "none", "null", "-", "غير معروف"}:
        return fallback
    return cleaned



def _finalize_archetype_confirmation(state, req: StudyApprovalRequest):
    """Lock archetype, attach schema questions, then collect structured answers."""
    from langchain_core.messages import AIMessage
    from ai_engine.archetypes import (
        normalize_archetype,
        questions_for_language,
        ARCHETYPE_LABELS,
    )
    from ai_engine.models.study_state import ProjectProfile

    chosen = None
    if req.feedback and "archetype=" in req.feedback:
        chosen = normalize_archetype(req.feedback.split("archetype=", 1)[1].strip().split()[0])
    if state.profile and state.profile.archetype and state.profile.archetype != "unknown":
        if not chosen:
            chosen = normalize_archetype(state.profile.archetype)
    chosen = chosen or "other"

    if state.profile is None:
        state.profile = ProjectProfile(archetype=chosen)  # type: ignore[arg-type]
    else:
        state.profile.archetype = chosen  # type: ignore[assignment]
    state.profile.archetype_confirmed = True
    state.profile_confirmed = False
    from ai_engine.archetypes import detect_services_variant
    context_bits = []
    for msg in reversed(list(state.messages or [])):
        role = getattr(msg, "type", None) or getattr(msg, "role", None)
        content = getattr(msg, "content", None)
        if isinstance(msg, dict):
            role = msg.get("type") or msg.get("role")
            content = msg.get("content")
        if role in {"human", "user"} and content:
            context_bits.append(str(content))
            if len(context_bits) >= 3:
                break
    context_text = "\n".join(reversed(context_bits))
    services_variant = None
    if chosen == "services":
        prior = getattr(state.profile, "services_variant", None)
        services_variant = detect_services_variant(context_text, explicit=prior)
        state.profile.services_variant = services_variant
    state.discovery_questions = questions_for_language(
        chosen, state.language, context_text=context_text, services_variant=services_variant
    )
    state.structured_answers = state.structured_answers or {}

    label = ARCHETYPE_LABELS.get(chosen, ARCHETYPE_LABELS["other"])[
        state.language if state.language in ("ar", "en") else "en"
    ]
    if state.language == "ar":
        state.messages.append(
            AIMessage(content=f"تم تأكيد التصنيف: **{label}**. أجب على الأسئلة المنظمة التالية قبل المتابعة.")
        )
    else:
        state.messages.append(
            AIMessage(content=f"Archetype confirmed: **{label}**. Answer the structured questions next.")
        )

    unanswered = [
        q for q in state.discovery_questions
        if q.get("required", True) and q.get("id") not in (state.structured_answers or {})
    ]
    if unanswered:
        state.phase = "NEEDS_INFORMATION"
        state.next_action = "answer_structured_questions"
    else:
        state.phase = "EVIDENCE_REVIEW"
        state.next_action = "review_evidence"
        state.profile_confirmed = True
    state.error = None
    state.blocking_reason = None
    return state

def _finalize_profile_confirmation(state):
    """Confirm Profile means: proceed even if gaps remain; AI must fill estimates next."""
    from langchain_core.messages import AIMessage, HumanMessage

    state.profile_confirmed = True
    gaps: list[str] = []
    if state.profile:
        state.profile.stage = _normalize_profile_label(state.profile.stage, fallback="idea")
        state.profile.decision_goal = _normalize_profile_label(
            state.profile.decision_goal, fallback="feasibility"
        )
        gaps = list(state.profile.missing_information or [])
        # Stop blocking the gate; later agents use conversation + estimates.
        state.profile.missing_information = []

    lang = getattr(state, "language", "en")
    if gaps:
        gap_lines = "\n".join(f"- {g}" for g in gaps)
        if lang == "ar":
            note = (
                "تم تأكيد ملف المشروع. سأملأ الآن الأدلة والافتراضات "
                "بتقديرات صريحة وواضحة للعناصر الناقصة التالية:\n"
                + gap_lines
            )
            instruct = (
                "تم تأكيد الملف. املأ الأدلة الآن. لكل عنصر ناقص أدناه، أنشئ claim "
                "من نوع ai_assumption بقيمة تقديرية واقعية للسوق السعودي، مع ذكر أنها تقدير:\n"
                + gap_lines
                + "\nثم اضبط evidence_sufficient=true إذا أصبحت التقديرات كافية للمتابعة."
            )
        else:
            note = (
                "Profile confirmed. I will now fill evidence and assumptions "
                "with explicit estimates for these remaining gaps:\n"
                + gap_lines
            )
            instruct = (
                "Profile confirmed. Fill evidence now. For each missing item below, create an "
                "ai_assumption claim with a realistic Saudi-market estimate and label it as an estimate:\n"
                + gap_lines
                + "\nThen set evidence_sufficient=true if these estimates are enough to continue."
            )
        state.messages.append(AIMessage(content=note))
        # Seed the next agent turn with an explicit fill request.
        state.messages.append(HumanMessage(content=instruct))
    else:
        if lang == "ar":
            state.messages.append(AIMessage(content="تم تأكيد الملف. المتابعة إلى جمع الأدلة."))
        else:
            state.messages.append(AIMessage(content="Profile confirmed. Continuing to evidence collection."))

    state.phase = "EVIDENCE_REVIEW"
    state.next_action = "review_evidence"
    # Clear any prior LLM failure so the orchestrator routes to evidence, not error_handler.
    state.error = None
    state.blocking_reason = None
    return state


def _import_engine():
    try:
        from ai_engine.models.study_state import StudyState
        from ai_engine.orchestrator import run_study_step
        return StudyState, run_study_step
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="AI engine not available. Please install ai-engine dependencies.",
        )


def _state_from_record(record: dict):
    from ai_engine.models.study_state import StudyState
    # Copy so we do not mutate the cached/persisted record when popping messages.
    state_data = dict(record["state"])
    msgs = state_data.pop("messages", []) or []
    state = StudyState(**state_data)
    for m in msgs:
        if isinstance(m, dict):
            mtype = m.get("type", "human")
            content = m.get("content", "")
            if mtype == "ai":
                from langchain_core.messages import AIMessage
                state.messages.append(AIMessage(content=content))
            elif mtype == "system":
                from langchain_core.messages import SystemMessage
                state.messages.append(SystemMessage(content=content))
            else:
                from langchain_core.messages import HumanMessage
                state.messages.append(HumanMessage(content=content))
    return state


def _public_messages(raw_messages) -> list[dict]:
    """Normalize persisted / LangChain messages for the workspace UI.

    Strips internal instruction prompts, raw JSON/tool traces, and system noise.
    Structured data remains in profile / assumptions / financial payloads only.
    """
    try:
        from ai_engine.utils.safe_messages import (
            is_internal_instruction,
            sanitize_chat_content,
        )
    except Exception:
        is_internal_instruction = lambda _t: False  # noqa: E731
        sanitize_chat_content = lambda text, **_k: (text or "")  # noqa: E731

    out: list[dict] = []
    for msg in raw_messages or []:
        if isinstance(msg, dict):
            mtype = msg.get("type") or msg.get("role") or "human"
            content = msg.get("content", "")
        elif hasattr(msg, "type") and hasattr(msg, "content"):
            mtype = msg.type
            content = msg.content
        else:
            continue
        if not content:
            continue
        text = str(content)
        if mtype in ("system",):
            continue
        if mtype in ("ai", "assistant"):
            role = "assistant"
            text = sanitize_chat_content(text) or ""
        else:
            role = "user"
            if is_internal_instruction(text):
                continue
        if not text:
            continue
        out.append({"role": role, "content": text})
    return out



def _attach_archetype_meta(payload: dict, state_like) -> dict:
    """Expose classification options + schema hints for the workspace UI."""
    try:
        from ai_engine.archetypes import classification_payload, get_assumption_schema, normalize_archetype
        lang = "en"
        profile = None
        if hasattr(state_like, "get"):
            profile = state_like.get("profile")
            lang = state_like.get("language") or "en"
        else:
            profile = getattr(state_like, "profile", None)
            lang = getattr(state_like, "language", "en") or "en"
            if profile is not None and hasattr(profile, "model_dump"):
                profile = profile.model_dump()
        payload["archetype_options"] = classification_payload(lang)
        arch = "other"
        services_variant = None
        if isinstance(profile, dict):
            arch = normalize_archetype(profile.get("archetype"))
            services_variant = profile.get("services_variant")
        payload["assumption_schema"] = get_assumption_schema(
            arch, services_variant=services_variant
        )
        if services_variant:
            payload["services_variant"] = services_variant
    except Exception:
        payload.setdefault("archetype_options", [])
        payload.setdefault("assumption_schema", [])
    return payload


def _enrich_financial_results(financial_results, language: str = "en"):
    """Attach user-facing IRR/payback display states; keep raw nulls for logs only."""
    if not isinstance(financial_results, dict):
        return financial_results
    try:
        from ai_engine.tools.financial_trust import attach_financial_display_fields
        return attach_financial_display_fields(financial_results, language=language or "en")
    except Exception:
        return financial_results


def _study_payload(study_id: str, record: dict, *, response: str | None = None) -> dict:
    """Full study payload so the UI can show AI-filled information."""
    s = record["state"] if "state" in record else record
    claims = s.get("claims") or []
    assumptions = s.get("assumptions") or []
    profile = s.get("profile")
    payload = {
        "study_id": study_id,
        "project_id": s.get("project_id"),
        "phase": s.get("phase"),
        "profile": profile,
        "claims": claims,
        "assumptions": assumptions,
        "claims_count": len(claims),
        "assumptions_count": len(assumptions),
        "discovery_questions": s.get("discovery_questions") or [],
        "structured_answers": s.get("structured_answers") or {},
        "assumptions_version": s.get("assumptions_version", 0),
        "archetype_options": None,
        "financial_results": _enrich_financial_results(
            s.get("financial_results"),
            language=s.get("language")
            or ((s.get("profile") or {}).get("language") if isinstance(s.get("profile"), dict) else None)
            or "en",
        ),
        "verdict": s.get("verdict"),
        "decision_rationale": s.get("decision_rationale"),
        "decision_conditions": s.get("decision_conditions") or [],
        "decision_risks": s.get("decision_risks") or [],
        "messages": _public_messages(s.get("messages")),
        "next_action": s.get("next_action"),
        "error": s.get("error"),
        "knowledge_context": _public_knowledge_context(s.get("knowledge_context")),
        "research_context": s.get("research_context"),
        "research_status": s.get("research_status"),
        "research_attempts": s.get("research_attempts") or [],
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }
    if response is not None:
        payload["response"] = response
    return _attach_archetype_meta(payload, s)


def _public_knowledge_context(kc) -> dict | None:
    """Expose Evidence Pack for UI/debug. Never include embeddings."""
    if not kc or not isinstance(kc, dict):
        return None
    return {
        "query": kc.get("query") or "",
        "hit_count": int(kc.get("hit_count") or 0),
        "comparable_projects": (kc.get("comparable_projects") or [])[:8],
        "similar_projects": (kc.get("similar_projects") or [])[:8],
        "assumption_hints": (kc.get("assumption_hints") or [])[:12],
        "risk_hints": (kc.get("risk_hints") or [])[:8],
        "financial_patterns": (kc.get("financial_patterns") or [])[:8],
        "citations": (kc.get("citations") or [])[:12],
    }


def _payload_from_state(study_id: str, state, *, response: str | None = None, record_meta: dict | None = None) -> dict:
    claims = [c.model_dump() if hasattr(c, "model_dump") else c for c in (state.claims or [])]
    assumptions = [a.model_dump() if hasattr(a, "model_dump") else a for a in (state.assumptions or [])]
    profile = state.profile.model_dump() if state.profile and hasattr(state.profile, "model_dump") else state.profile
    payload = {
        "study_id": study_id,
        "project_id": state.project_id,
        "phase": state.phase,
        "profile": profile,
        "claims": claims,
        "assumptions": assumptions,
        "claims_count": len(claims),
        "assumptions_count": len(assumptions),
        "discovery_questions": getattr(state, "discovery_questions", None) or [],
        "structured_answers": getattr(state, "structured_answers", None) or {},
        "assumptions_version": getattr(state, "assumptions_version", 0) or 0,
        "archetype_options": None,
        "financial_results": _enrich_financial_results(state.financial_results, language=getattr(state, "language", None) or "en"),
        "verdict": state.verdict,
        "decision_rationale": state.decision_rationale,
        "decision_conditions": state.decision_conditions or [],
        "decision_risks": state.decision_risks or [],
        "messages": _public_messages(state.messages),
        "next_action": state.next_action,
        "error": state.error,
        "knowledge_context": _public_knowledge_context(getattr(state, "knowledge_context", None)),
        "research_context": getattr(state, "research_context", None),
        "research_status": getattr(state, "research_status", None),
        "research_attempts": list(getattr(state, "research_attempts", None) or []),
        "created_at": (record_meta or {}).get("created_at"),
        "updated_at": (record_meta or {}).get("updated_at"),
    }
    if response is not None:
        payload["response"] = response
    return _attach_archetype_meta(payload, state)



def _attach_knowledge_context(state, user_id: str):
    """Load Evidence Pack into state before assumption generation (tenant-scoped).

    Must run BEFORE run_study_step/run_assumptions so the assumption agent can
    ground origins/refs. Knowledge failures never block the study flow.
    """
    try:
        from app.db import DB_ENABLED, SessionLocal
        from app.services import knowledge_service as ks
        if not DB_ENABLED:
            return state
        profile = getattr(state, "profile", None)
        archetype = getattr(profile, "archetype", None) if profile else None
        sector = getattr(profile, "sector", None) if profile else None
        bits = []
        if archetype:
            bits.append(str(archetype).replace("_", " "))
            # Expand frozen archetype labels into retrieval vocabulary.
            _ARCH_EXPAND = {
                "services": "cybersecurity MSSP managed SOC consulting utilization contracts",
                "saas_digital": "SaaS ARR MRR churn subscription digital product",
                "real_estate": "residential compound occupancy absorption units land construction",
                "data_center": "data center colocation MW PUE rack power capex",
            }
            bits.append(_ARCH_EXPAND.get(str(archetype), ""))
        if sector:
            bits.append(str(sector))
        for msg in list(getattr(state, "messages", None) or [])[-5:]:
            content = getattr(msg, "content", None)
            if isinstance(msg, dict):
                content = msg.get("content")
            if content:
                bits.append(str(content)[:400])
        answers = getattr(state, "structured_answers", None) or {}
        if answers:
            bits.append(" ".join(f"{k}={v}" for k, v in list(answers.items())[:12]))
        query = " | ".join(b for b in bits if b)[:2000] or "feasibility study Saudi Arabia"
        assumption_keys = [a.key for a in (getattr(state, "assumptions", None) or [])]
        if not assumption_keys:
            try:
                from ai_engine.archetypes import get_assumption_schema, normalize_archetype
                arch = normalize_archetype(archetype or "other")
                schema = get_assumption_schema(arch)
                assumption_keys = [f["key"] for f in schema]
            except Exception:
                assumption_keys = []
        query_profile = {
            "sector": sector,
            "project_type": archetype,
            "geography": getattr(profile, "city", None) or getattr(profile, "location", None),
            "capex": getattr(profile, "capex", None) or getattr(profile, "investment", None),
        }
        db = SessionLocal()
        try:
            pack = ks.retrieve_evidence(
                db,
                owner_id=int(user_id),
                query=query,
                study_id=getattr(state, "study_id", None),
                assumption_keys=assumption_keys,
                top_k=6,
                query_profile=query_profile,
            )
            state.knowledge_context = pack
        finally:
            db.close()
    except Exception:
        # Knowledge is assistive — never block the study flow
        if getattr(state, "knowledge_context", None) is None:
            state.knowledge_context = {"query": "", "citations": [], "hit_count": 0}
    return state


def _prepare_assumptions_with_knowledge(state, user_id: str):
    """Attach Evidence Pack then generate assumptions (graph or direct)."""
    return _attach_knowledge_context(state, user_id)


def _finalize_knowledge_influence(state, user_id: str):
    """Post-process assumption refs + persist influence (no engine changes)."""
    if not (getattr(state, "assumptions", None) or []):
        return state
    try:
        from app.db import DB_ENABLED, SessionLocal
        from app.services import knowledge_service as ks
        if not DB_ENABLED:
            return state
        state = ks.enrich_state_assumptions(state)
        db = SessionLocal()
        try:
            ks.record_assumption_influence(
                db,
                owner_id=int(user_id),
                study_id=getattr(state, "study_id", None),
                assumptions=getattr(state, "assumptions", None) or [],
            )
        finally:
            db.close()
    except Exception:
        return state
    return state


def _remember_study_if_ready(state, user_id: str):
    """Persist Study Memory when REPORT_READY (tenant-scoped, idempotent)."""
    if getattr(state, "phase", None) != "REPORT_READY":
        return
    try:
        from app.db import DB_ENABLED, SessionLocal
        from app.services import knowledge_service as ks
        if not DB_ENABLED:
            return
        db = SessionLocal()
        try:
            ks.remember_completed_study(db, owner_id=int(user_id), state=state)
        finally:
            db.close()
    except Exception:
        return

@router.post("")
async def create_study(req: StudyCreateRequest, user=Depends(get_current_user)):
    StudyState, run_study_step = _import_engine()

    study_id = f"study_{uuid.uuid4().hex[:12]}"
    user_id = str(user.id)

    state = StudyState(
        study_id=study_id,
        project_id=req.project_id,
        user_id=user_id,
        language=req.language,
        phase="DRAFT",
    )

    if req.description:
        from langchain_core.messages import HumanMessage
        state.messages.append(HumanMessage(content=req.description))

        try:
            state = await run_study_step(state)
        except Exception as e:
            state.error = _safe_ai_error(e, getattr(state, "language", "en"), "study_engine")

    _save_study(study_id, state.model_dump(), user_id); _remember_study_if_ready(state, user_id)

    last_ai_message = None
    for msg in reversed(state.messages):
        if hasattr(msg, "type") and msg.type == "ai":
            last_ai_message = msg.content
            break

    return _payload_from_state(study_id, state, response=last_ai_message)


@router.get("/{study_id}")
async def get_study(study_id: str, user=Depends(get_current_user)):
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")

    return _study_payload(study_id, record)


@router.post("/{study_id}/message")
async def send_message(study_id: str, req: StudyMessageRequest, user=Depends(get_current_user)):
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")

    _, run_study_step = _import_engine()

    state = _state_from_record(record)
    if req.language:
        state.language = req.language

    from langchain_core.messages import HumanMessage
    state.messages.append(HumanMessage(content=req.message))
    state.error = None

    try:
        state = await run_study_step(state)
    except Exception as e:
        state.error = _safe_ai_error(e, getattr(state, "language", "en"), "study_engine")

    _save_study(study_id, state.model_dump(), user_id); _remember_study_if_ready(state, user_id)

    last_ai_message = None
    for msg in reversed(state.messages):
        if hasattr(msg, "type") and msg.type == "ai":
            last_ai_message = msg.content
            break

    return _payload_from_state(study_id, state, response=last_ai_message, record_meta=record)



@router.post("/{study_id}/continue")
async def continue_study(study_id: str, user=Depends(get_current_user)):
    """Owner-facing advance: one orchestrator step without chat workarounds.

    Allowed when the study is waiting on financial → risk → decision progression.
    """
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")

    _, run_study_step = _import_engine()
    state = _state_from_record(record)

    allowed = {"READY_FOR_ANALYSIS", "ANALYZED", "DECISION_READY"}
    if state.phase not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot continue from phase '{state.phase}'. Expected one of: {sorted(allowed)}.",
        )

    from langchain_core.messages import HumanMessage

    prompts = {
        "READY_FOR_ANALYSIS": "Continue: run financial analysis from approved assumptions.",
        "ANALYZED": "Continue: assess risks for this study.",
        "DECISION_READY": "Continue: issue the final decision and prepare the report.",
    }
    state.messages.append(HumanMessage(content=prompts[state.phase]))
    state.error = None

    try:
        state = await run_study_step(state)
    except Exception as e:
        state.error = _safe_ai_error(e, getattr(state, "language", "en"), "study_engine")

    _save_study(study_id, state.model_dump(), user_id)
    _remember_study_if_ready(state, user_id)

    last_ai_message = None
    for msg in reversed(state.messages):
        if hasattr(msg, "type") and msg.type == "ai":
            last_ai_message = msg.content
            break

    return _payload_from_state(study_id, state, response=last_ai_message, record_meta=record)


@router.post("/{study_id}/approve/{stage}")
async def approve_stage(
    study_id: str,
    stage: str,
    req: StudyApprovalRequest,
    user=Depends(get_current_user),
):
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")

    _, run_study_step = _import_engine()

    state = _state_from_record(record)

    valid_stages = {
        "archetype": (("ARCHETYPE_CLASSIFICATION",), "profile_confirmed"),
        "profile": (("NEEDS_INFORMATION", "ARCHETYPE_CLASSIFICATION", "UNDERSTANDING"), "profile_confirmed"),
        "evidence": (("EVIDENCE_REVIEW",), "evidence_approved"),
        "assumptions": (("ASSUMPTIONS_REVIEW",), "assumptions_approved"),
    }

    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")

    expected_phases, flag_field = valid_stages[stage]
    if isinstance(expected_phases, str):
        expected_phases = (expected_phases,)

    if state.phase not in expected_phases:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve '{stage}' in phase '{state.phase}'. Expected one of: {list(expected_phases)}.",
        )

    if stage == "assumptions" and not state.assumptions:
        raise HTTPException(status_code=400, detail="No assumptions to confirm.")

    if stage == "evidence" and not state.claims:
        raise HTTPException(status_code=400, detail="No evidence to approve.")

    if not req.approved:
        if req.feedback:
            from langchain_core.messages import HumanMessage
            state.messages.append(HumanMessage(content=req.feedback))
        _save_study(study_id, state.model_dump(), user_id); _remember_study_if_ready(state, user_id)
        return _payload_from_state(
            study_id,
            state,
            record_meta=record,
        ) | {"message": "Feedback recorded. Continue the conversation."}

    setattr(state, flag_field, True)
    state.phase_history.append(f"{stage}_approved")

    # Advance phase BEFORE running the next agent. Otherwise the orchestrator
    # re-routes to the same gate agent (e.g. discovery) and Confirm appears stuck,
    # especially when missing_information is still non-empty.
    if stage == "archetype":
        state = _finalize_archetype_confirmation(state, req)
    elif stage == "profile":
        state = _finalize_profile_confirmation(state)
    elif stage == "evidence":
        state.phase = "ASSUMPTIONS_REVIEW"
    elif stage == "assumptions":
        # Study-level gate only (no per-assumption status enum).
        # Rejected rows are already removed from state.assumptions.
        empty = [a for a in (state.assumptions or []) if not str(getattr(a, "value", "") or "").strip()]
        if empty:
            keys = ", ".join(a.key for a in empty[:12])
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve: {len(empty)} assumption(s) have empty values ({keys}). Edit or regenerate them first.",
            )
        state.phase = "READY_FOR_ANALYSIS"

    # Phase 6: knowledge retrieval must precede assumption generation.
    if stage == "evidence" or state.phase == "ASSUMPTIONS_REVIEW":
        state = _prepare_assumptions_with_knowledge(state, user_id)

    try:
        state = await run_study_step(state)
    except Exception as e:
        state.error = _safe_ai_error(e, getattr(state, "language", "en"), "study_engine")

    # State-machine guard: never persist ASSUMPTIONS_REVIEW with zero rows.
    if stage == "evidence" and state.phase == "ASSUMPTIONS_REVIEW" and not (state.assumptions or []):
        try:
            from ai_engine.agents.assumption import run_assumptions
            state = _prepare_assumptions_with_knowledge(state, user_id)
            state = run_assumptions(state)
            state.error = None
        except Exception as e:
            state.error = _safe_ai_error(e, getattr(state, "language", "en"), "assumption_generation")

    if stage == "evidence" or state.phase == "ASSUMPTIONS_REVIEW":
        state = _finalize_knowledge_influence(state, user_id)

    _save_study(study_id, state.model_dump(), user_id); _remember_study_if_ready(state, user_id)

    return _payload_from_state(study_id, state, record_meta=record)



@router.post("/{study_id}/archetype")
async def select_archetype(study_id: str, req: ArchetypeSelectRequest, user=Depends(get_current_user)):
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")
    _, run_study_step = _import_engine()
    state = _state_from_record(record)

    from ai_engine.archetypes import normalize_archetype, questions_for_language, ARCHETYPE_LABELS
    from ai_engine.models.study_state import ProjectProfile
    from langchain_core.messages import AIMessage

    chosen = normalize_archetype(req.archetype)
    if state.profile is None:
        state.profile = ProjectProfile(archetype=chosen)  # type: ignore[arg-type]
    else:
        state.profile.archetype = chosen  # type: ignore[assignment]
    state.profile.archetype_confirmed = bool(req.approved)
    from ai_engine.archetypes import detect_services_variant
    context_bits = []
    for msg in reversed(list(state.messages or [])):
        role = getattr(msg, "type", None) or getattr(msg, "role", None)
        content = getattr(msg, "content", None)
        if isinstance(msg, dict):
            role = msg.get("type") or msg.get("role")
            content = msg.get("content")
        if role in {"human", "user"} and content:
            context_bits.append(str(content))
            if len(context_bits) >= 3:
                break
    context_text = "\n".join(reversed(context_bits))
    services_variant = None
    if chosen == "services":
        prior = getattr(state.profile, "services_variant", None)
        services_variant = detect_services_variant(context_text, explicit=prior)
        state.profile.services_variant = services_variant
    state.discovery_questions = questions_for_language(
        chosen, state.language, context_text=context_text, services_variant=services_variant
    )
    state.phase = "ARCHETYPE_CLASSIFICATION" if not req.approved else "NEEDS_INFORMATION"
    state.next_action = "confirm_archetype" if not req.approved else "answer_structured_questions"
    label = ARCHETYPE_LABELS.get(chosen, ARCHETYPE_LABELS["other"])[state.language if state.language in ("ar", "en") else "en"]
    state.messages.append(AIMessage(content=f"Archetype set to {label} (`{chosen}`)."))
    state.error = None
    if req.approved:
        fake = StudyApprovalRequest(approved=True)
        state = _finalize_archetype_confirmation(state, fake)
        try:
            state = await run_study_step(state)
        except Exception as e:
            state.error = _safe_ai_error(e, getattr(state, "language", "en"), "study_engine")
    _save_study(study_id, state.model_dump(), user_id); _remember_study_if_ready(state, user_id)
    return _payload_from_state(study_id, state, record_meta=record)


@router.post("/{study_id}/structured-answers")
async def submit_structured_answers(study_id: str, req: StructuredAnswersRequest, user=Depends(get_current_user)):
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")
    _, run_study_step = _import_engine()
    state = _state_from_record(record)
    from ai_engine.discovery import unanswered_required, enrich_questions_for_language

    # Ensure interview metadata exists for studies created before Discovery Advisor.
    if state.discovery_questions:
        state.discovery_questions = enrich_questions_for_language(
            state.discovery_questions, language=state.language or "en"
        )

    answers = dict(state.structured_answers or {})
    # Apply explicit user answers only (never write AI-estimate placeholders).
    # Reject poison strings like "confirmed"/"ok" for numeric/currency/percent
    # fields so StudyState maps cleanly into the existing Assumption Engine.
    q_types = {
        str(q.get("id")): str(q.get("answer_type") or q.get("question_type") or "").upper()
        for q in (state.discovery_questions or [])
        if q.get("id")
    }
    _NUMERIC_TYPES = {"NUMBER", "CURRENCY", "PERCENTAGE", "PERCENT"}
    _POISON = {"confirmed", "ok", "yes", "y", "true", "n/a", "na", "none", "null", "-"}
    for key, value in (req.answers or {}).items():
        if value is None or value == "":
            continue
        if isinstance(value, str) and not value.strip():
            continue
        atype = q_types.get(str(key), "")
        if atype in _NUMERIC_TYPES:
            if isinstance(value, str) and value.strip().lower() in _POISON:
                continue
            if isinstance(value, str):
                try:
                    value = float(value.strip().replace(",", ""))
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    continue
        answers[key] = value
    state.structured_answers = answers

    ai_estimate_ids = {str(x) for x in (req.ai_estimates or []) if x}
    if state.discovery_questions:
        for q in state.discovery_questions:
            qid = str(q.get("id") or "")
            if not qid:
                continue
            if qid in answers:
                q["answered"] = True
                q["answer"] = answers[qid]
                q["ai_estimated"] = False
            elif qid in ai_estimate_ids and q.get("allow_ai_estimate", True):
                # Mark satisfied for discovery gating; leave structured_answers
                # empty so the existing Assumption Engine fills the value.
                q["answered"] = True
                q["ai_estimated"] = True
                q["answer"] = None
            elif req.mark_answered and qid in (req.answers or {}):
                # Explicit empty answer ignored — keep unanswered.
                pass

    unanswered = unanswered_required(state.discovery_questions, state.structured_answers)
    if unanswered:
        state.phase = "NEEDS_INFORMATION"
        state.next_action = "answer_structured_questions"
        if state.profile:
            # Soft hint only — primary UX is the AI Discovery Interview.
            state.profile.missing_information = [
                str(q.get("question") or q.get("prompt") or q.get("id")) for q in unanswered
            ]
    else:
        state.profile_confirmed = True
        if state.profile:
            state.profile.missing_information = []
            state.profile.archetype_confirmed = True
        state.phase = "EVIDENCE_REVIEW"
        state.next_action = "review_evidence"
        try:
            state = await run_study_step(state)
        except Exception as e:
            state.error = _safe_ai_error(e, getattr(state, "language", "en"), "study_engine")

    _save_study(study_id, state.model_dump(), user_id); _remember_study_if_ready(state, user_id)
    return _payload_from_state(study_id, state, record_meta=record)


@router.post("/{study_id}/assumptions/edit")
async def edit_assumption(study_id: str, req: AssumptionEditRequest, user=Depends(get_current_user)):
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")
    state = _state_from_record(record)
    from ai_engine.archetypes import assert_no_saas_leakage, normalize_archetype

    arch = normalize_archetype(state.profile.archetype if state.profile else "other")
    leaked = assert_no_saas_leakage(arch, [req.key])
    if leaked:
        raise HTTPException(status_code=400, detail=f"SaaS assumption key not allowed for {arch}: {leaked}")

    updated = False
    for a in state.assumptions or []:
        if a.key == req.key:
            a.value = req.value
            if req.low is not None:
                a.low = req.low
            if req.base is not None:
                a.base = req.base
            if req.high is not None:
                a.high = req.high
            a.source = "user"
            a.origin = "user"
            a.ai_estimated = False
            a.confidence = "confirmed"
            updated = True
            break
    if not updated:
        from ai_engine.models.study_state import Assumption
        state.assumptions = list(state.assumptions or [])
        state.assumptions.append(
            Assumption(
                key=req.key,
                value=req.value,
                source="user",
                confidence="confirmed",
                low=req.low,
                base=req.base or req.value,
                high=req.high,
                origin="user",
                ai_estimated=False,
            )
        )
    state.assumptions_version = int(state.assumptions_version or 0) + 1
    state.assumptions_approved = False
    state.phase = "ASSUMPTIONS_REVIEW"
    state.next_action = "review_assumptions"
    _save_study(study_id, state.model_dump(), user_id); _remember_study_if_ready(state, user_id)
    return _payload_from_state(study_id, state, record_meta=record)


@router.post("/{study_id}/assumptions/action")
async def assumption_action(study_id: str, req: AssumptionActionRequest, user=Depends(get_current_user)):
    """Per-card actions mapped onto the current Assumption model (no status enum).

    - approve: accept AI estimate as user-confirmed (origin=user, ai_estimated=false)
    - reject: remove from active list (not silently bulk-approved later)
    - regenerate: drop key and rebuild via assumption agent
    """
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")
    state = _state_from_record(record)
    action = (req.action or "").strip().lower()
    if action not in {"approve", "reject", "regenerate"}:
        raise HTTPException(status_code=400, detail="action must be approve|reject|regenerate")

    if action == "regenerate":
        _, run_study_step = _import_engine()
        state.assumptions_approved = False
        state.phase = "ASSUMPTIONS_REVIEW"
        state.error = None
        state.assumptions = [a for a in (state.assumptions or []) if a.key != req.key]
        state = _prepare_assumptions_with_knowledge(state, user_id)
        try:
            state = await run_study_step(state)
        except Exception as e:
            state.error = _safe_ai_error(e, getattr(state, "language", "en"), "study_engine")
        if not state.assumptions:
            try:
                from ai_engine.agents.assumption import run_assumptions
                state = _prepare_assumptions_with_knowledge(state, user_id)
                state = run_assumptions(state)
            except Exception as e:
                state.error = _safe_ai_error(e, getattr(state, "language", "en"), "assumption_rebuild")
        state = _finalize_knowledge_influence(state, user_id)
        _save_study(study_id, state.model_dump(), user_id); _remember_study_if_ready(state, user_id)
        return _payload_from_state(study_id, state, record_meta=record)

    if action == "reject":
        before = len(state.assumptions or [])
        state.assumptions = [a for a in (state.assumptions or []) if a.key != req.key]
        if len(state.assumptions) == before:
            raise HTTPException(status_code=404, detail=f"Assumption not found: {req.key}")
        state.assumptions_approved = False
        state.assumptions_version = int(state.assumptions_version or 0) + 1
        state.phase = "ASSUMPTIONS_REVIEW"
        state.next_action = "review_assumptions"
        _save_study(study_id, state.model_dump(), user_id); _remember_study_if_ready(state, user_id)
        return _payload_from_state(study_id, state, record_meta=record)

    # approve (card-level accept → user-confirmed fields)
    found = False
    for a in state.assumptions or []:
        if a.key != req.key:
            continue
        found = True
        if req.value is not None:
            a.value = req.value
            a.base = req.value
        a.source = "user"
        a.origin = "user"
        a.ai_estimated = False
        a.confidence = "confirmed"
        break
    if not found:
        raise HTTPException(status_code=404, detail=f"Assumption not found: {req.key}")
    state.assumptions_approved = False
    state.assumptions_version = int(state.assumptions_version or 0) + 1
    state.phase = "ASSUMPTIONS_REVIEW"
    _save_study(study_id, state.model_dump(), user_id); _remember_study_if_ready(state, user_id)
    return _payload_from_state(study_id, state, record_meta=record)


@router.post("/{study_id}/assumptions/regenerate")
async def regenerate_assumptions(study_id: str, user=Depends(get_current_user)):
    user_id = str(user.id)
    record = _load_study(study_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Study not found")
    _, run_study_step = _import_engine()
    state = _state_from_record(record)
    state.assumptions_approved = False
    state.assumptions = []
    state.phase = "ASSUMPTIONS_REVIEW"
    state.error = None
    state = _prepare_assumptions_with_knowledge(state, user_id)
    try:
        state = await run_study_step(state)
    except Exception as e:
        state.error = _safe_ai_error(e, getattr(state, "language", "en"), "study_engine")
    if not state.assumptions:
        try:
            from ai_engine.agents.assumption import run_assumptions
            state = _prepare_assumptions_with_knowledge(state, user_id)
            state = run_assumptions(state)
        except Exception as e:
            state.error = _safe_ai_error(e, getattr(state, "language", "en"), "assumption_rebuild")
    state = _finalize_knowledge_influence(state, user_id)
    _save_study(study_id, state.model_dump(), user_id); _remember_study_if_ready(state, user_id)
    return _payload_from_state(study_id, state, record_meta=record)


@router.get("")
async def list_studies(user=Depends(get_current_user)):
    return {"studies": _list_user_studies(str(user.id))}
