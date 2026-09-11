"""Ingest uploaded knowledge bytes into structured metadata + chunks."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .chunking import chunk_text
from .embeddings import embed_text
from .extract import extract_structured_metadata, extract_text
from .quality import score_document_quality


def ingest_bytes(
    data: bytes,
    *,
    filename: str,
    content_type: str | None = None,
    title: str | None = None,
    source: str = "upload",
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    text = extract_text(data, filename, content_type)
    meta = extract_structured_metadata(text, filename=filename)
    if overrides:
        for k, v in overrides.items():
            if v is not None and v != "":
                meta[k] = v

    chunks_raw = chunk_text(text)
    chunks: List[Dict[str, Any]] = []
    for ch in chunks_raw:
        content = ch["content"]
        importance = 0.55
        low = content.lower()
        if any(k in low for k in ("assumption", "capex", "opex", "irr", "risk", "افتراض", "مخاطر")):
            importance = 0.8
        chunks.append(
            {
                "id": str(uuid.uuid4()),
                "content": content,
                "embedding": embed_text(content),
                "metadata": {
                    "index": ch["index"],
                    "project_type": meta.get("project_type"),
                    "sector": meta.get("sector"),
                },
                "importance": importance,
            }
        )

    status = "ready" if text.strip() else "partial"
    doc_id = str(uuid.uuid4())
    country = meta.get("country") or "SA"
    quality = score_document_quality(
        text=text,
        metadata=meta,
        source=source,
        country=country,
    )
    return {
        "id": doc_id,
        "title": title or (filename.rsplit(".", 1)[0] if filename else "Untitled"),
        "source": source,
        "sector": meta.get("sector"),
        "country": country,
        "year": meta.get("year"),
        "document_type": (overrides or {}).get("document_type") or "feasibility_study",
        "project_type": meta.get("project_type"),
        "capex": meta.get("capex"),
        "opex": meta.get("opex"),
        "revenue_model": meta.get("revenue_model"),
        "assumptions": meta.get("assumptions") or {},
        "outcome": meta.get("outcome"),
        "confidence": float(meta.get("confidence") or 0.5),
        "extraction_status": status,
        "raw_text_excerpt": (text[:4000] if text else None),
        "chunks": chunks,
        "original_filename": filename,
        "content_type": content_type,
        "quality_score": quality.get("quality_score"),
        "quality_breakdown": quality,
        "reference_count": 0,
        "geography": country,
        "business_model": (meta.get("revenue_model") or {}).get("type")
        if isinstance(meta.get("revenue_model"), dict)
        else None,
    }
