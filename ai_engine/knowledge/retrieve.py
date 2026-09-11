"""Tenant-scoped knowledge retrieval + evidence pack builder."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .embeddings import cosine_similarity, embed_text
from .similarity import build_similar_projects


def retrieve_for_query(
    *,
    query: str,
    chunk_rows: Sequence[Any],
    document_by_id: Dict[str, Any],
    memory_rows: Sequence[Any] | None = None,
    top_k: int = 6,
    min_score: float = 0.12,
) -> List[Dict[str, Any]]:
    """Rank owner-scoped chunks (and optional study memories) for a query."""
    q_emb = embed_text(query)
    scored: List[Dict[str, Any]] = []

    for row in chunk_rows or []:
        emb = _get(row, "embedding") or []
        score = cosine_similarity(q_emb, emb)
        importance = float(_get(row, "importance") or 0.5)
        doc_id = _get(row, "document_id")
        doc = document_by_id.get(str(doc_id)) if doc_id else None
        boost = 0.0
        pt = _get(doc, "project_type") if doc is not None else None
        if pt and str(pt).lower() in query.lower():
            boost += 0.08
        # Phase 6.1 — mild quality-weighted ranking (never blocks retrieval)
        qscore = _get(doc, "quality_score") if doc is not None else None
        try:
            if qscore is not None:
                boost += 0.05 * (float(qscore) / 100.0)
        except (TypeError, ValueError):
            pass
        final = score * (0.7 + 0.3 * importance) + boost
        if final < min_score:
            continue
        scored.append(
            {
                "kind": "chunk",
                "score": round(final, 4),
                "chunk_id": str(_get(row, "id")),
                "document_id": str(doc_id) if doc_id else None,
                "study_memory_id": None,
                "content": _get(row, "content") or "",
                "title": _get(doc, "title") if doc is not None else None,
                "project_type": pt,
                "source": _get(doc, "source") if doc is not None else "upload",
                "document_confidence": (
                    float(_get(doc, "confidence") or 0.5) if doc is not None else 0.5
                ),
                "doc_assumptions": (
                    _get(doc, "assumptions") if doc is not None else None
                )
                or {},
            }
        )

    for mem in memory_rows or []:
        emb = _get(mem, "embedding") or []
        score = cosine_similarity(q_emb, emb)
        if score < min_score:
            continue
        scored.append(
            {
                "kind": "study_memory",
                "score": round(score, 4),
                "chunk_id": None,
                "document_id": None,
                "study_memory_id": str(_get(mem, "id")),
                "content": _get(mem, "summary_text") or _get(mem, "lessons_learned") or "",
                "title": f"Prior study {_get(mem, 'source_study_id')}",
                "project_type": _get(mem, "archetype") or _get(mem, "project_type"),
                "source": "study_memory",
                "document_confidence": 0.7,
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    seen_docs: set[str] = set()
    out: List[Dict[str, Any]] = []
    for item in scored:
        doc_id = item.get("document_id")
        if doc_id:
            if doc_id in seen_docs:
                continue
            seen_docs.add(doc_id)
        out.append(item)
        if len(out) >= top_k:
            break
    return out


def build_evidence_pack(
    *,
    query: str,
    hits: List[Dict[str, Any]],
    assumption_keys: Optional[List[str]] = None,
    document_by_id: Optional[Dict[str, Any]] = None,
    query_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build citation-safe Evidence Pack. Never invent document ids."""
    comparable: List[Dict[str, Any]] = []
    citations: List[Dict[str, Any]] = []
    assumption_hints: List[Dict[str, Any]] = []
    risk_hints: List[Dict[str, Any]] = []
    financial_patterns: List[Dict[str, Any]] = []
    similar_projects = build_similar_projects(
        query=query,
        hits=hits,
        document_by_id=document_by_id or {},
        query_profile=query_profile,
        top_k=5,
    )

    for h in hits:
        if not h.get("content"):
            continue
        has_source = h.get("document_id") or h.get("study_memory_id")
        if not has_source:
            continue
        claim = _first_sentence(h["content"])
        conf = round(
            float(h.get("score") or 0) * float(h.get("document_confidence") or 0.5), 3
        )
        comparable.append(
            {
                "document_id": h.get("document_id"),
                "study_memory_id": h.get("study_memory_id"),
                "title": h.get("title") or "Untitled",
                "project_type": h.get("project_type"),
                "similarity": h.get("score"),
                "source": h.get("source") or "upload",
            }
        )
        citations.append(
            {
                "claim": claim,
                "source_title": h.get("title") or "Untitled",
                "document_id": h.get("document_id"),
                "chunk_id": h.get("chunk_id"),
                "study_memory_id": h.get("study_memory_id"),
                "confidence": conf,
            }
        )
        low = h["content"].lower()
        if any(k in low for k in ("risk", "delay", "overrun", "مخاطر", "تأخير")):
            risk_hints.append(
                {
                    "text": claim,
                    "document_id": h.get("document_id"),
                    "study_memory_id": h.get("study_memory_id"),
                    "confidence": conf,
                }
            )
        if any(k in low for k in ("capex", "opex", "irr", "npv", "payback", "revenue")):
            financial_patterns.append(
                {
                    "text": claim,
                    "document_id": h.get("document_id"),
                    "confidence": conf,
                }
            )

    keys = list(assumption_keys or [])
    if not keys:
        # Derive common feasibility keys from retrieved content for MVP grounding
        blob = " ".join((h.get("content") or "").lower() for h in hits)
        catalog = [
            "occupancy", "absorption", "pue", "capex", "opex", "utilization",
            "churn", "mw_capacity", "pricing_per_kw", "rack_count", "power_cost",
        ]
        keys = [k for k in catalog if k.replace("_", " ") in blob or k in blob]

    # Synonym / stem bridges so schema keys match feasibility prose.
    aliases = {
        "capex_total": ["capex", "capital expenditure", "capital cost"],
        "opex_annual": ["opex", "operating cost", "operating expense"],
        "occupancy": ["occupancy", "occupancy rate", "lease-up"],
        "absorption": ["absorption", "absorption rate", "sell-through"],
        "utilization_rate": ["utilization", "utilisation", "billable utilization"],
        "mw_capacity": ["mw", "megawatt", "it load", "capacity"],
        "pricing_per_kw": ["kw", "pricing", "colocation", "per kw"],
        "pue": ["pue", "power usage effectiveness"],
        "churn": ["churn", "attrition", "retention"],
        "monthly_recurring_revenue": ["mrr", "recurring revenue", "subscription"],
        "active_contracts": ["contracts", "clients", "customers", "active_contracts"],
        "consultants_headcount": ["consultants", "headcount", "staff", "fte"],
        "monthly_recurring_contracts": ["recurring", "contracts", "mrr", "monthly"],
        "delivery_cost_monthly": ["delivery", "cost", "opex", "operating"],
        "gross_margin": ["margin", "gross margin", "profitability"],
        "initial_investment": ["capex", "investment", "capital", "initial"],
        "units": ["units", "apartments", "villas"],
        "avg_unit_price": ["unit price", "selling price", "sale price"],
    }

    for key in keys:
        key_l = key.lower().replace("_", " ")
        tokens = [t for t in key_l.split() if len(t) >= 3]
        needles = list(dict.fromkeys(tokens + [key.lower()] + aliases.get(key, [])))
        matched = []
        for h in hits:
            content_l = (h.get("content") or "").lower()
            meta_l = " ".join(
                f"{k} {v}" for k, v in ((h.get("doc_assumptions") or {}) or {}).items()
            ).lower()
            blob = f"{content_l} {meta_l} {str(h.get('project_type') or '').lower()}"
            if needles and any(tok in blob for tok in needles):
                if h.get("document_id") or h.get("study_memory_id"):
                    matched.append(h)
        if not matched and hits:
            # Soft fallback: same project_type comparable still supports AI estimates
            # with real document ids (never invents sources).
            for h in hits:
                if h.get("document_id") or h.get("study_memory_id"):
                    matched.append(h)
                    if len(matched) >= 2:
                        break
        if not matched:
            continue
        top = matched[0]
        titles = [x.get("title") for x in matched[:2] if x.get("title")]
        rationale = (
            f"Similar project evidence from {', '.join(titles)}"
            if titles
            else f"Grounded in {len(matched)} similar knowledge hit(s)"
        )
        assumption_hints.append(
            {
                "key": key,
                "suggested_value": None,
                "confidence": round(float(top.get("score") or 0.5), 3),
                "evidence_ids": [
                    x.get("document_id") or x.get("study_memory_id") for x in matched[:3]
                ],
                "rationale": rationale,
                "refs": [
                    {
                        "document_id": x.get("document_id"),
                        "chunk_id": x.get("chunk_id"),
                        "study_memory_id": x.get("study_memory_id"),
                        "title": x.get("title"),
                        "similarity": x.get("score"),
                        "reason": rationale,
                        "confidence": round(float(x.get("score") or 0.5), 3),
                        "source_document": x.get("title"),
                    }
                    for x in matched[:3]
                ],
            }
        )

    return {
        "query": query,
        "comparable_projects": comparable,
        "similar_projects": similar_projects,
        "assumption_hints": assumption_hints,
        "risk_hints": risk_hints,
        "financial_patterns": financial_patterns,
        "citations": citations,
        "hit_count": len(hits),
    }


def _get(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _first_sentence(text: str, limit: int = 220) -> str:
    t = " ".join((text or "").split())
    if not t:
        return ""
    for sep in (". ", "。", "!\n", "?\n"):
        if sep in t:
            t = t.split(sep)[0] + ("." if sep.startswith(".") else "")
            break
    return t[:limit]
