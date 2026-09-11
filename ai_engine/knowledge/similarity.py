"""Similar-project intelligence scoring (Phase 6.1).

Builds structured comparable-project cards on top of vector retrieval hits.
Does not replace frozen engines.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence


_SECTOR_ALIASES = {
    "real_estate": {"real_estate", "residential", "housing", "compound", "apartment", "عقار", "سكني"},
    "data_center": {"data_center", "datacenter", "colocation", "pue", "mw", "rack", "مركز بيانات"},
    "cybersecurity": {"cyber", "security", "mssp", "soc", "أمن", "سيبر"},
    "saas_digital": {"saas", "software", "subscription", "arr", "mrr"},
    "services": {"services", "consulting", "professional"},
}


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _sector_bucket(value: Any) -> Optional[str]:
    t = _norm(value)
    if not t:
        return None
    for bucket, aliases in _SECTOR_ALIASES.items():
        if t == bucket or any(a in t for a in aliases):
            return bucket
    return t.split()[0] if t else None


def _capex_amount(capex: Any) -> Optional[float]:
    if capex is None:
        return None
    if isinstance(capex, (int, float)):
        return float(capex)
    if isinstance(capex, dict):
        for k in ("amount", "value", "total", "sar"):
            if capex.get(k) is not None:
                try:
                    return float(capex[k])
                except (TypeError, ValueError):
                    pass
    try:
        return float(str(capex).replace(",", "").split()[0])
    except (TypeError, ValueError, IndexError):
        return None


def _geography_tokens(text: str) -> set[str]:
    cities = {
        "riyadh", "jeddah", "dammam", "khobar", "neom", "makkah", "madinah",
        "الرياض", "جدة", "الدمام", "saudi", "ksa", "sa",
    }
    t = _norm(text)
    return {c for c in cities if c in t}


def score_project_similarity(
    *,
    query: str,
    hit: Dict[str, Any],
    document: Any = None,
    query_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compute multi-factor similarity for one retrieved hit/document."""
    profile = dict(query_profile or {})
    q = _norm(query)
    title = _norm(_get(document, "title") or hit.get("title") or "")
    project_type = _get(document, "project_type") or hit.get("project_type")
    sector = _get(document, "sector") or profile.get("sector")
    country = _get(document, "country") or "SA"
    capex = _get(document, "capex")
    quality = _get(document, "quality_score")
    content = _norm(hit.get("content") or "")

    # vector / retrieval base
    base = float(hit.get("score") or 0.0)

    # sector match
    q_sector = _sector_bucket(profile.get("sector") or profile.get("project_type") or q)
    d_sector = _sector_bucket(sector or project_type or title or content)
    if q_sector and d_sector and q_sector == d_sector:
        sector_match = 1.0
    elif q_sector and d_sector and (q_sector in d_sector or d_sector in q_sector):
        sector_match = 0.7
    else:
        sector_match = 0.25 if not q_sector else 0.1

    # geography match
    q_geo = _geography_tokens(q + " " + str(profile.get("geography") or profile.get("city") or ""))
    d_geo = _geography_tokens(
        " ".join(
            [
                title,
                content,
                str(country or ""),
                str(_get(document, "raw_text_excerpt") or ""),
            ]
        )
    )
    if q_geo and d_geo and (q_geo & d_geo):
        geography_match = 1.0
    elif (country or "").upper() in {"SA", "KSA"} and (
        "saudi" in q or "riyadh" in q or "الرياض" in q or not q_geo
    ):
        geography_match = 0.75
    else:
        geography_match = 0.3

    # business model match (heuristic keywords)
    model_tokens = {
        "sale", "lease", "rent", "colocation", "subscription", "retainer",
        "off-plan", " بيع", "تأجير",
    }
    q_models = {t for t in model_tokens if t in q}
    d_models = {t for t in model_tokens if t in content or t in title}
    if q_models and d_models and (q_models & d_models):
        business_model_match = 1.0
    elif not q_models:
        business_model_match = 0.55
    else:
        business_model_match = 0.2

    # CAPEX similarity
    q_capex = _capex_amount(profile.get("capex"))
    d_capex = _capex_amount(capex)
    if q_capex and d_capex and q_capex > 0 and d_capex > 0:
        ratio = min(q_capex, d_capex) / max(q_capex, d_capex)
        capex_similarity = float(ratio)
    else:
        # soft signal from units / MW mentions
        q_units = re.search(r"(\d+)\s*(apartment|unit|mw|ラック)", q)
        d_units = re.search(r"(\d+)\s*(apartment|unit|mw|rack)", content + " " + title)
        if q_units and d_units:
            a, b = float(q_units.group(1)), float(d_units.group(1))
            capex_similarity = min(a, b) / max(a, b) if a and b else 0.4
        else:
            capex_similarity = 0.4

    quality_factor = 0.5
    if quality is not None:
        try:
            quality_factor = max(0.3, min(1.0, float(quality) / 100.0))
        except (TypeError, ValueError):
            quality_factor = 0.5

    similarity = (
        0.40 * base
        + 0.20 * sector_match
        + 0.15 * geography_match
        + 0.10 * business_model_match
        + 0.10 * capex_similarity
        + 0.05 * quality_factor
    )
    similarity = max(0.0, min(1.0, similarity))

    reasons: List[str] = []
    if sector_match >= 0.7:
        reasons.append(f"Sector match ({d_sector})")
    if geography_match >= 0.7:
        reasons.append("Geography match")
    if business_model_match >= 0.7:
        reasons.append("Business model overlap")
    if capex_similarity >= 0.6:
        reasons.append("CAPEX / scale similarity")
    if quality is not None:
        reasons.append(f"Quality {int(quality)}%")

    return {
        "document_id": hit.get("document_id") or _get(document, "id"),
        "study_memory_id": hit.get("study_memory_id"),
        "title": hit.get("title") or _get(document, "title") or "Untitled",
        "project_type": project_type,
        "sector": sector or d_sector,
        "country": country,
        "similarity_score": round(similarity, 4),
        "similarity_pct": int(round(similarity * 100)),
        "sector_match": round(sector_match, 3),
        "geography_match": round(geography_match, 3),
        "business_model_match": round(business_model_match, 3),
        "capex_similarity": round(capex_similarity, 3),
        "quality_score": int(quality) if quality is not None else None,
        "retrieval_score": round(base, 4),
        "source": hit.get("source") or _get(document, "source") or "upload",
        "reasons": reasons[:6],
    }


def build_similar_projects(
    *,
    query: str,
    hits: Sequence[Dict[str, Any]],
    document_by_id: Optional[Dict[str, Any]] = None,
    query_profile: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    docs = document_by_id or {}
    cards: List[Dict[str, Any]] = []
    seen = set()
    for hit in hits:
        doc_id = hit.get("document_id")
        mem_id = hit.get("study_memory_id")
        key = doc_id or mem_id
        if not key or key in seen:
            continue
        seen.add(key)
        doc = docs.get(str(doc_id)) if doc_id else None
        cards.append(
            score_project_similarity(
                query=query,
                hit=dict(hit),
                document=doc,
                query_profile=query_profile,
            )
        )
    cards.sort(key=lambda c: c.get("similarity_score") or 0, reverse=True)
    return cards[:top_k]


def _get(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)
