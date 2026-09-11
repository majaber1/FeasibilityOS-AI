# Phase 6.1 — Knowledge Intelligence & Learning Loop Validation

**Branch:** `cursor/knowledge-intelligence-learning-1831`  
**Scope:** Quality scoring, similar-project cards, assumption influence tracking, REPORT_READY learning fields, Knowledge Dashboard MVP.  
**Constraint:** Frozen engines (Archetype / Discovery / Assumption / Financial / Risk / Decision) were not modified.

## Gates

| Gate | Status | Evidence |
|------|--------|----------|
| Quality scoring | PASS | `ai_engine/knowledge/quality.py`; ingest attaches `quality_score` + breakdown; KnowledgePanel shows % + reasons |
| Similar-project intelligence | PASS | `ai_engine/knowledge/similarity.py`; evidence pack includes `similar_projects`; study API exposes them |
| Influence tracking | PASS | `ai_engine/knowledge/influence.py`; post-process glue in `study_engine` + `knowledge_service.record_assumption_influence` |
| Learning loop | PASS | `memory.build_memory_payload` writes `conditions` + `influence_summary` on REPORT_READY |
| Knowledge Dashboard MVP | PASS | `GET /api/v2/knowledge/dashboard` + `/tools/knowledge` page |
| Residential vs DC comparison | PASS | `tests/test_knowledge_intelligence_learning.py` |

## Test results

```text
12 passed (knowledge MVP + Phase 6.1 + alembic head allowlist)
Artifact: /opt/cursor/artifacts/phase61_knowledge_tests.log
```

## Files changed (primary)

- `ai_engine/knowledge/{quality,similarity,influence}.py`
- `ai_engine/knowledge/{ingest,retrieve,memory,__init__}.py`
- `backend/app/models.py` + Alembic `0029_knowledge_intel_learning`
- `backend/app/services/knowledge_service.py`
- `backend/app/api/v2/{knowledge,study_engine}.py`
- `apps/web/components/study/{KnowledgePanel,AssumptionReviewPanel}.tsx`
- `apps/web/app/tools/knowledge/page.tsx`
- `tests/test_knowledge_intelligence_learning.py`

## DB / API

- Columns: `knowledge_documents.quality_score|quality_breakdown|reference_count|geography|business_model`
- Columns: `knowledge_evidence.assumption_key|reason`
- Columns: `study_memories.conditions|influence_summary`
- API: `GET /api/v2/knowledge/dashboard`, retrieve `query_profile`, memories learning fields

## Safeguards

- No invented citations — refs keep real document/chunk/memory ids
- Embeddings never returned in public serializers
- Influence enrichment runs only in study glue after assumption generation
