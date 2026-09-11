"""Knowledge influence enrichment (Phase 6.1).

Post-processes assumption knowledge_refs WITHOUT changing assumption generation
logic in the frozen Assumption Engine. Call from study orchestration glue only.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def enrich_assumption_influence(
    assumptions: List[Any],
    knowledge_context: Optional[Dict[str, Any]],
) -> List[Any]:
    """Attach reason / confidence / source document detail onto knowledge_refs."""
    if not assumptions or not knowledge_context:
        return assumptions

    hints = {
        h.get("key"): h
        for h in (knowledge_context.get("assumption_hints") or [])
        if h.get("key")
    }
    similar = {
        str(p.get("document_id") or p.get("study_memory_id")): p
        for p in (knowledge_context.get("similar_projects") or [])
        if p.get("document_id") or p.get("study_memory_id")
    }

    out = []
    for a in assumptions:
        refs = list(getattr(a, "knowledge_refs", None) or (a.get("knowledge_refs") if isinstance(a, dict) else None) or [])
        if not refs:
            out.append(a)
            continue
        key = getattr(a, "key", None) if not isinstance(a, dict) else a.get("key")
        hint = hints.get(key) or {}
        reason = hint.get("rationale") or "Similar project evidence"
        conf = hint.get("confidence")
        if conf is None:
            conf = getattr(a, "knowledge_confidence", None) if not isinstance(a, dict) else a.get("knowledge_confidence")

        enriched = []
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            rid = str(ref.get("document_id") or ref.get("study_memory_id") or "")
            sim = similar.get(rid) or {}
            item = dict(ref)
            item.setdefault("reason", reason)
            if conf is not None:
                item.setdefault("confidence", float(conf))
            if sim.get("title"):
                item.setdefault("source_document", sim.get("title"))
            elif ref.get("title"):
                item.setdefault("source_document", ref.get("title"))
            if sim.get("similarity_pct") is not None and item.get("similarity") is None:
                item["similarity"] = (sim["similarity_pct"] or 0) / 100.0
            if sim.get("reasons"):
                item.setdefault("match_reasons", list(sim.get("reasons") or [])[:4])
            enriched.append(item)

        if isinstance(a, dict):
            a = dict(a)
            a["knowledge_refs"] = enriched
            if conf is not None:
                a["knowledge_confidence"] = float(conf)
            a["knowledge_influence"] = {
                "reason": reason,
                "confidence": float(conf) if conf is not None else None,
                "source_count": len(enriched),
            }
        else:
            a.knowledge_refs = enriched
            if conf is not None:
                a.knowledge_confidence = float(conf)
            # optional dynamic attr for serialization via model_dump if present
            try:
                setattr(
                    a,
                    "knowledge_influence",
                    {
                        "reason": reason,
                        "confidence": float(conf) if conf is not None else None,
                        "source_count": len(enriched),
                    },
                )
            except Exception:
                pass
        out.append(a)
    return out


def influence_records_for_evidence(
    assumptions: List[Any],
    *,
    study_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Flatten assumption influences into evidence-like records for persistence."""
    rows: List[Dict[str, Any]] = []
    for a in assumptions or []:
        key = getattr(a, "key", None) if not isinstance(a, dict) else a.get("key")
        refs = getattr(a, "knowledge_refs", None) if not isinstance(a, dict) else a.get("knowledge_refs")
        value = getattr(a, "value", None) if not isinstance(a, dict) else a.get("value")
        for ref in refs or []:
            if not isinstance(ref, dict):
                continue
            if not (ref.get("document_id") or ref.get("study_memory_id")):
                continue
            rows.append(
                {
                    "study_id": study_id,
                    "assumption_key": key,
                    "claim": f"{key}={value}",
                    "reason": ref.get("reason") or "Similar project evidence",
                    "source_document_id": ref.get("document_id"),
                    "source_chunk_id": ref.get("chunk_id"),
                    "source_study_memory_id": ref.get("study_memory_id"),
                    "confidence": float(ref.get("confidence") or ref.get("similarity") or 0.5),
                    "related_project": ref.get("source_document") or ref.get("title"),
                }
            )
    return rows
