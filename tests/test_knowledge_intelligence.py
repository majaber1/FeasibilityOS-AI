"""Unit tests for Knowledge Intelligence Layer (Phase 6 MVP)."""
from __future__ import annotations

from ai_engine.knowledge.embeddings import cosine_similarity, embed_text
from ai_engine.knowledge.ingest import ingest_bytes
from ai_engine.knowledge.retrieve import build_evidence_pack, retrieve_for_query
from ai_engine.knowledge.extract import extract_structured_metadata


def test_embeddings_similar_for_related_text():
    a = embed_text("20MW data center Riyadh colocation PUE occupancy")
    b = embed_text("Build a data center in Riyadh with 20 MW IT load and occupancy ramp")
    c = embed_text("Residential compound villas absorption rate Riyadh")
    assert cosine_similarity(a, b) > cosine_similarity(a, c)
    assert abs(sum(x * x for x in a) - 1.0) < 1e-6


def test_extract_data_center_metadata():
    text = """
    Feasibility Study — Jeddah Data Center 20MW (2024)
    CAPEX SAR 180,000,000. OPEX SAR 12,000,000.
    Initial occupancy 35%. PUE target 1.4. Rack leasing revenue model.
    Key risks: power delay, cooling redundancy.
    Outcome: GO with conditions.
    """
    meta = extract_structured_metadata(text, filename="dc_study.txt")
    assert meta["project_type"] == "data_center"
    assert meta["assumptions"].get("occupancy") == "35%"
    assert meta["capex"] and meta["capex"]["amount"] > 0


def test_ingest_txt_produces_chunks():
    data = b"""Cybersecurity MSSP Feasibility Saudi Arabia
    Retainer revenue, billable consultants, SOC coverage.
    Assumptions: utilization 70%, monthly retainer SAR 25000.
    Risks: talent shortage, certification delays.
    """
    ingested = ingest_bytes(
        data, filename="cyber.txt", content_type="text/plain", title="Cyber MSSP"
    )
    assert ingested["chunks"]
    assert all("embedding" in ch for ch in ingested["chunks"])
    assert ingested["extraction_status"] in {"ready", "partial"}
    # Public API serializers must never include embeddings (checked in service).
    from app.services.knowledge_service import document_public_dict
    from types import SimpleNamespace

    fake = SimpleNamespace(
        id=ingested["id"],
        title=ingested["title"],
        source="upload",
        sector=ingested.get("sector"),
        country="SA",
        year=None,
        document_type="feasibility_study",
        project_type=ingested.get("project_type"),
        capex=None,
        opex=None,
        revenue_model=None,
        assumptions={},
        outcome=None,
        confidence=0.5,
        visibility="private",
        extraction_status="ready",
        original_filename="cyber.txt",
        content_type="text/plain",
        created_at=None,
        chunks=[],
    )
    pub = document_public_dict(fake)
    assert "embedding" not in pub
    assert "embeddings" not in pub


def test_retrieve_and_evidence_pack_requires_real_ids():
    ingested = ingest_bytes(
        b"Residential compound Riyadh 500 units. Absorption 8% per quarter. Land CAPEX SAR 25000000.",
        filename="re.txt",
        content_type="text/plain",
        title="Riyadh Compound",
    )
    chunks = []
    docs = {}
    for ch in ingested["chunks"]:
        chunks.append(
            type(
                "C",
                (),
                {
                    "id": ch["id"],
                    "document_id": ingested["id"],
                    "content": ch["content"],
                    "embedding": ch["embedding"],
                    "importance": ch["importance"],
                },
            )()
        )
    docs[ingested["id"]] = type(
        "D",
        (),
        {
            "id": ingested["id"],
            "title": ingested["title"],
            "project_type": ingested.get("project_type"),
            "source": "upload",
            "confidence": ingested.get("confidence", 0.5),
        },
    )()
    hits = retrieve_for_query(
        query="residential compound Riyadh absorption units",
        chunk_rows=chunks,
        document_by_id=docs,
        top_k=3,
    )
    assert hits
    pack = build_evidence_pack(
        query="residential compound",
        hits=hits,
        assumption_keys=["absorption_rate", "unit_count"],
    )
    assert pack["hit_count"] >= 1
    for cite in pack["citations"]:
        assert cite.get("document_id") or cite.get("study_memory_id")
        assert cite.get("claim")


def test_tenant_isolation_empty_corpus():
    from app.services import knowledge_service as ks

    class FakeQuery:
        def __init__(self, rows):
            self.rows = rows

        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return self.rows

        def order_by(self, *a, **k):
            return self

        def first(self):
            return self.rows[0] if self.rows else None

    class FakeDB:
        def query(self, model):
            return FakeQuery([])

        def add(self, obj):
            return None

        def commit(self):
            return None

    pack = ks.retrieve_evidence(FakeDB(), owner_id=101, query="data center Riyadh", top_k=3)
    assert pack["hit_count"] == 0
    assert pack["citations"] == []
