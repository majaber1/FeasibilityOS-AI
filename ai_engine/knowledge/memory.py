"""Study Memory write-back after REPORT_READY (Phase 6 / 6.1 learning loop)."""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

from .embeddings import embed_text


def build_memory_payload(
    state: Any, *, owner_id: int, organization_id: Optional[int] = None
) -> Dict[str, Any]:
    profile = getattr(state, "profile", None)
    archetype = getattr(profile, "archetype", None) if profile else None
    sector = getattr(profile, "sector", None) if profile else None
    assumptions = []
    influence_count = 0
    for a in getattr(state, "assumptions", None) or []:
        if hasattr(a, "model_dump"):
            row = a.model_dump()
        elif isinstance(a, dict):
            row = dict(a)
        else:
            row = {
                "key": getattr(a, "key", None),
                "value": getattr(a, "value", None),
                "source": getattr(a, "source", None),
                "origin": getattr(a, "origin", None),
                "confidence": getattr(a, "confidence", None),
                "knowledge_refs": getattr(a, "knowledge_refs", None) or [],
                "knowledge_confidence": getattr(a, "knowledge_confidence", None),
            }
        refs = row.get("knowledge_refs") or []
        if refs or row.get("origin") == "knowledge_reference":
            influence_count += 1
        assumptions.append(row)

    financial = (
        getattr(state, "financial_results", None)
        or getattr(state, "financial_outcome", None)
        or {}
    )
    conditions = list(
        getattr(state, "decision_conditions", None)
        or getattr(state, "conditions", None)
        or []
    )
    decision = {
        "verdict": getattr(state, "verdict", None),
        "rationale": getattr(state, "decision_rationale", None),
        "conditions": conditions,
    }
    risks = list(getattr(state, "decision_risks", None) or getattr(state, "risks", None) or [])
    summary = (
        f"Archetype={archetype}; sector={sector}; verdict={decision.get('verdict')}; "
        f"assumptions={len(assumptions)}; knowledge_influenced={influence_count}; "
        f"NPV={financial.get('npv') if isinstance(financial, dict) else None}; "
        f"IRR={financial.get('irr') if isinstance(financial, dict) else None}"
    )
    lessons = decision.get("rationale") or summary
    influence_summary = {
        "knowledge_influenced_assumptions": influence_count,
        "total_assumptions": len(assumptions),
        "similar_projects": (getattr(state, "knowledge_context", None) or {}).get(
            "similar_projects"
        )
        or [],
    }
    def _clip(value: Any, n: int = 120) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text[:n] if text else None

    return {
        "id": str(uuid.uuid4()),
        "owner_id": owner_id,
        "organization_id": organization_id,
        "source_study_id": getattr(state, "study_id", None),
        # StudyMemory.sector/archetype/project_type are VARCHAR(120).
        "archetype": _clip(archetype),
        "project_type": _clip(archetype),
        "sector": _clip(sector),
        "country": _clip("SA", 8) or "SA",
        "assumptions": assumptions,
        "financial_outcome": financial if isinstance(financial, dict) else {},
        "decision": decision,
        "risks": risks,
        "lessons_learned": lessons,
        "summary_text": summary,
        "conditions": conditions,
        "influence_summary": influence_summary,
        "embedding": embed_text(
            summary + "\n" + json.dumps(assumptions[:12], ensure_ascii=False)[:1500]
        ),
        "visibility": "private",
    }


def upsert_study_memory(db, models, payload: Dict[str, Any]):
    """Insert or update StudyMemory for (owner_id, source_study_id)."""
    StudyMemory = models.StudyMemory
    existing = (
        db.query(StudyMemory)
        .filter_by(owner_id=payload["owner_id"], source_study_id=payload["source_study_id"])
        .first()
    )
    fields = (
        "archetype",
        "project_type",
        "sector",
        "country",
        "assumptions",
        "financial_outcome",
        "decision",
        "risks",
        "lessons_learned",
        "summary_text",
        "embedding",
        "visibility",
        "organization_id",
        "conditions",
        "influence_summary",
    )
    if existing:
        for key in fields:
            if key in payload:
                setattr(existing, key, payload.get(key))
        db.add(existing)
        return existing
    row = StudyMemory(**{k: v for k, v in payload.items() if k != "id" or True})
    # Keep explicit id when provided
    if payload.get("id"):
        row.id = payload["id"]
    db.add(row)
    return row
