"""Knowledge Intelligence Layer (Phase 6 / 6.1) — retrieval + evidence, not a chatbot."""

from .embeddings import embed_text, cosine_similarity
from .extract import extract_text, extract_structured_metadata
from .chunking import chunk_text
from .retrieve import build_evidence_pack, retrieve_for_query
from .ingest import ingest_bytes
from .memory import build_memory_payload, upsert_study_memory
from .quality import score_document_quality
from .similarity import build_similar_projects, score_project_similarity
from .influence import enrich_assumption_influence, influence_records_for_evidence

__all__ = [
    "embed_text",
    "cosine_similarity",
    "extract_text",
    "extract_structured_metadata",
    "chunk_text",
    "build_evidence_pack",
    "retrieve_for_query",
    "ingest_bytes",
    "build_memory_payload",
    "upsert_study_memory",
    "score_document_quality",
    "build_similar_projects",
    "score_project_similarity",
    "enrich_assumption_influence",
    "influence_records_for_evidence",
]
