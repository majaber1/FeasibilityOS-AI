"""Phase 6.1 — Knowledge Intelligence quality, similarity, influence, learning."""
from __future__ import annotations

from types import SimpleNamespace

from ai_engine.knowledge.quality import score_document_quality
from ai_engine.knowledge.similarity import build_similar_projects, score_project_similarity
from ai_engine.knowledge.influence import enrich_assumption_influence, influence_records_for_evidence
from ai_engine.knowledge.memory import build_memory_payload
from ai_engine.knowledge.ingest import ingest_bytes
from ai_engine.knowledge.retrieve import build_evidence_pack, retrieve_for_query


def test_quality_scoring_rewards_complete_saudi_docs():
    weak = score_document_quality(text="short note", metadata={}, source="other", country="US")
    strong = score_document_quality(
        text=(
            "Riyadh residential compound feasibility. CAPEX SAR 40,000,000. "
            "IRR 18%. NPV positive. Sensitivity and risk analysis. Outcome: GO with conditions."
        ),
        metadata={
            "year": 2024,
            "project_type": "real_estate",
            "sector": "residential",
            "capex": {"amount": 40_000_000},
            "opex": {"amount": 2_000_000},
            "assumptions": {"occupancy": "75%"},
            "outcome": {"verdict": "GO"},
        },
        source="upload",
        country="SA",
    )
    assert 0 <= weak["quality_score"] <= 100
    assert strong["quality_score"] > weak["quality_score"]
    assert any("Saudi" in r for r in strong["reasons"])
    assert "factors" in strong


def test_similar_projects_prefer_same_sector_and_geography():
    residential_hit = {
        "document_id": "doc-re",
        "score": 0.7,
        "title": "Riyadh Residential Compound",
        "project_type": "real_estate",
        "content": "500 apartment units absorption 8% Riyadh off-plan sale",
        "source": "upload",
    }
    dc_hit = {
        "document_id": "doc-dc",
        "score": 0.7,
        "title": "Jeddah Data Center 20MW",
        "project_type": "data_center",
        "content": "colocation MW PUE rack power",
        "source": "upload",
    }
    docs = {
        "doc-re": SimpleNamespace(
            id="doc-re",
            title="Riyadh Residential Compound",
            project_type="real_estate",
            sector="residential",
            country="SA",
            capex={"amount": 50_000_000},
            quality_score=80,
            raw_text_excerpt="Riyadh apartments",
            source="upload",
        ),
        "doc-dc": SimpleNamespace(
            id="doc-dc",
            title="Jeddah Data Center 20MW",
            project_type="data_center",
            sector="technology",
            country="SA",
            capex={"amount": 180_000_000},
            quality_score=75,
            raw_text_excerpt="Jeddah data center",
            source="upload",
        ),
    }
    cards = build_similar_projects(
        query="residential compound Riyadh 400 units sale",
        hits=[residential_hit, dc_hit],
        document_by_id=docs,
        query_profile={"sector": "real_estate", "project_type": "real_estate", "geography": "Riyadh"},
        top_k=5,
    )
    assert cards
    assert cards[0]["document_id"] == "doc-re"
    assert cards[0]["similarity_score"] >= cards[-1]["similarity_score"]
    assert any("Sector" in r or "Geography" in r for r in cards[0]["reasons"])


def test_influence_enrichment_adds_reason_without_inventing_ids():
    assumptions = [
        {
            "key": "occupancy",
            "value": "72%",
            "origin": "knowledge_reference",
            "knowledge_refs": [
                {
                    "document_id": "doc-1",
                    "chunk_id": "chunk-1",
                    "title": "Riyadh Compound Study",
                    "similarity": 0.81,
                }
            ],
            "knowledge_confidence": 0.7,
        },
        {"key": "pue", "value": "1.4", "knowledge_refs": []},
    ]
    kc = {
        "assumption_hints": [
            {
                "key": "occupancy",
                "rationale": "Similar project evidence from Riyadh Compound Study",
                "confidence": 0.81,
            }
        ],
        "similar_projects": [
            {
                "document_id": "doc-1",
                "title": "Riyadh Compound Study",
                "similarity_pct": 81,
                "reasons": ["Sector match", "Geography match"],
            }
        ],
    }
    enriched = enrich_assumption_influence(assumptions, kc)
    occ = enriched[0]
    assert "Similar project" in occ["knowledge_influence"]["reason"]
    assert occ["knowledge_refs"][0]["document_id"] == "doc-1"
    assert occ["knowledge_refs"][0]["source_document"] == "Riyadh Compound Study"
    assert occ["knowledge_refs"][0]["reason"]
    rows = influence_records_for_evidence(enriched, study_id="study_1")
    assert len(rows) == 1
    assert rows[0]["source_document_id"] == "doc-1"
    assert rows[0]["assumption_key"] == "occupancy"


def test_memory_payload_includes_conditions_and_influence_summary():
    state = SimpleNamespace(
        study_id="study_abc",
        profile=SimpleNamespace(archetype="real_estate", sector="residential"),
        assumptions=[
            {
                "key": "occupancy",
                "value": "70%",
                "origin": "knowledge_reference",
                "knowledge_refs": [{"document_id": "d1"}],
                "knowledge_confidence": 0.6,
            }
        ],
        financial_results={"npv": 1_000_000, "irr": 0.18},
        decision_conditions=["Secure land title"],
        verdict="GO",
        decision_rationale="Strong absorption",
        decision_risks=["Construction delay"],
        knowledge_context={"similar_projects": [{"document_id": "d1", "title": "Prior"}]},
    )
    payload = build_memory_payload(state, owner_id=7)
    assert payload["conditions"] == ["Secure land title"]
    assert payload["influence_summary"]["knowledge_influenced_assumptions"] >= 1
    assert "knowledge_influenced" in payload["summary_text"]


def test_residential_vs_datacenter_retrieval_separation():
    re_doc = ingest_bytes(
        b"Residential compound Riyadh 500 apartments. Absorption 8% per quarter. "
        b"Land CAPEX SAR 25000000. Off-plan sale model. Occupancy ramp to 85%.",
        filename="riyadh_residential.txt",
        content_type="text/plain",
        title="Riyadh Residential",
        overrides={"project_type": "real_estate", "sector": "residential", "year": 2024},
    )
    dc_doc = ingest_bytes(
        b"Jeddah Data Center 20MW colocation. PUE 1.35. Rack power pricing. "
        b"CAPEX SAR 180000000. Initial occupancy 35%. Cooling redundancy risks.",
        filename="jeddah_dc.txt",
        content_type="text/plain",
        title="Jeddah Data Center",
        overrides={"project_type": "data_center", "sector": "technology", "year": 2024},
    )
    assert re_doc["quality_score"] is not None
    assert dc_doc["quality_score"] is not None

    chunks = []
    docs = {}
    for ingested in (re_doc, dc_doc):
        docs[ingested["id"]] = SimpleNamespace(
            id=ingested["id"],
            title=ingested["title"],
            project_type=ingested.get("project_type"),
            sector=ingested.get("sector"),
            country="SA",
            capex=ingested.get("capex"),
            quality_score=ingested.get("quality_score"),
            confidence=ingested.get("confidence", 0.5),
            source="upload",
            assumptions=ingested.get("assumptions") or {},
            raw_text_excerpt=ingested.get("raw_text_excerpt"),
        )
        for ch in ingested["chunks"]:
            chunks.append(
                SimpleNamespace(
                    id=ch["id"],
                    document_id=ingested["id"],
                    content=ch["content"],
                    embedding=ch["embedding"],
                    importance=ch["importance"],
                )
            )

    re_hits = retrieve_for_query(
        query="residential compound Riyadh absorption apartments",
        chunk_rows=chunks,
        document_by_id=docs,
        top_k=3,
    )
    dc_hits = retrieve_for_query(
        query="data center Jeddah MW colocation PUE racks",
        chunk_rows=chunks,
        document_by_id=docs,
        top_k=3,
    )
    assert re_hits and dc_hits
    assert re_hits[0]["document_id"] == re_doc["id"]
    assert dc_hits[0]["document_id"] == dc_doc["id"]

    re_pack = build_evidence_pack(
        query="residential compound Riyadh",
        hits=re_hits,
        assumption_keys=["occupancy", "absorption"],
        document_by_id=docs,
        query_profile={"sector": "real_estate", "project_type": "real_estate", "geography": "Riyadh"},
    )
    dc_pack = build_evidence_pack(
        query="data center Jeddah",
        hits=dc_hits,
        assumption_keys=["pue", "mw_capacity"],
        document_by_id=docs,
        query_profile={"sector": "data_center", "project_type": "data_center", "geography": "Jeddah"},
    )
    assert re_pack["similar_projects"]
    assert dc_pack["similar_projects"]
    assert re_pack["similar_projects"][0]["document_id"] == re_doc["id"]
    assert dc_pack["similar_projects"][0]["document_id"] == dc_doc["id"]
    for cite in re_pack["citations"] + dc_pack["citations"]:
        assert cite.get("document_id") or cite.get("study_memory_id")
    assert any(h["key"] in {"occupancy", "absorption"} for h in re_pack["assumption_hints"])
    assert any(h["key"] in {"pue", "mw_capacity"} for h in dc_pack["assumption_hints"])


def test_score_project_similarity_capex_signal():
    hit = {
        "document_id": "d1",
        "score": 0.5,
        "title": "DC 10MW",
        "content": "10 MW data center colocation",
        "project_type": "data_center",
    }
    doc = SimpleNamespace(
        id="d1",
        title="DC 10MW",
        project_type="data_center",
        sector="technology",
        country="SA",
        capex={"amount": 100_000_000},
        quality_score=70,
        raw_text_excerpt="",
        source="upload",
    )
    close = score_project_similarity(
        query="data center",
        hit=hit,
        document=doc,
        query_profile={"sector": "data_center", "capex": 95_000_000},
    )
    far = score_project_similarity(
        query="data center",
        hit=hit,
        document=doc,
        query_profile={"sector": "data_center", "capex": 5_000_000},
    )
    assert close["capex_similarity"] > far["capex_similarity"]
