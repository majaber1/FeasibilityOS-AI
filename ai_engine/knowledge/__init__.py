"""Knowledge Intelligence Layer (Phase 6) — retrieval + evidence, not a chatbot."""

from .embeddings import embed_text, cosine_similarity
from .extract import extract_text, extract_structured_metadata
from .chunking import chunk_text
from .retrieve import build_evidence_pack, retrieve_for_query
from .ingest import ingest_bytes
from .memory import build_memory_payload, upsert_study_memory

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
]
