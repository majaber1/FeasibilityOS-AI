"""Study Memory write-back after REPORT_READY."""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

from .embeddings import embed_text


def build_memory_payload(state: Any, *, owner_id: int, organization_id: Optional[int] = None) -> Dict[str, Any]:
    profile = getattr(state, "profile", None)
    archetype = getattr(profile, "archetype", None) if profile else None
    sector = getattr(profile, "sector", None) if profile else None
    assumptions = []
    for a in getattr(state, "assumptions", None) or []:
        if hasattr(a, "model_dump"):
            assumptions.append(a.model_dump())
        elif isinstance(a, dict):
            assumptions.append(a)
        else:
            assumptions.append(
                {
                    "key": getattr(a, "key", None),
                    "value": getattr(a, "value", None),
                    "source": getattr(a, "source", None),
                    "origin": getattr(a, "origin", None),
                    "confidence": getattr(a, "confidence", None),
                }
            )
    financial = getattr(state, "financial_results", None) or {}
    decision = {
        "verdict": getattr(state, "verdict", None),
        "rationale": getattr(state, "decision_rationale", None),
        "conditions": list(getattr(state, "decision_conditions", None) or []),
    }
    risks = list(getattr(state, "decision_risks", None) or [])
    summary = (
        f"Archetype={archetype}; sector={sector}; verdict={decision.get('verdict')}; "
        f"assumptions={len(assumptions)}; "
        f"NPV={financial.get('npv') if isinstance(financial, dict) else None}; "
        f"IRR={financial.get('irr') if isinstance(financial, dict) else None}"
    )
    lessons = decision.get("rationale") or summary
    return {
        "id": str(uuid.uuid4()),
        "owner_id": owner_id,
        "organization_id": organization_id,
        "source_study_id": getattr(state, "study_id", None),
        "archetype": archetype,
        "project_type": archetype,
        "sector": sector,
        "country": "SA",
        "assumptions": assumptions,
        "financial_outcome": financial if isinstance(financial, dict) else {},
        "decision": decision,
        "risks": risks,
        "lessons_learned": lessons,
        "summary_text": summary,
        "embedding": embed_text(summary + "\n" + json.dumps(assumptions[:12], ensure_ascii=False)[:1500]),
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
    if existing:
        for key in (
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
        ):
            setattr(existing, key, payload.get(key))
        db.add(existing)
        return existing
    row = StudyMemory(**payload)
    db.add(row)
    return row
