# V4 Phase 7A — Source Foundation Validation

**Status:** PASS  
**Branch:** `cursor/v4-phase7a-source-foundation-1831`  
**Baseline:** V3 frozen `v3.0.0` @ `33e216e2ed939b065bca0357c3855184e219a68d`  
**Architecture baseline (PR #38 merge):** `f9fb3ae1815b79bc0601baeaac630336b6ed2240`  
**Reuse baseline:** `docs/architecture/V4_OPEN_SOURCE_REUSE_BASELINE.md` (unchanged)

## Goal

Governed foundation so every future external source enters via:

`External Source → SourceConnector → SourceDocument → Validation/Provenance → Existing Knowledge Layer → Evidence Pack → Study Engine`

Phase 7A does **not** perform live web research.

## Delivered

| Area | Location | Result |
|------|----------|--------|
| SourceConnector contract | `backend/app/integrations/sources/base.py` | PASS |
| Canonical SourceDocument + Provenance | `backend/app/integrations/sources/schemas.py` | PASS |
| Validation / UNKNOWN rules | `backend/app/integrations/sources/validation.py` | PASS |
| Fixture connector | `backend/app/integrations/sources/fixture_connector.py` | PASS |
| Knowledge adapter (no second RAG) | `backend/app/integrations/sources/knowledge_adapter.py` | PASS |
| Source Registry service | `backend/app/services/source_registry_service.py` | PASS |
| ORM + migration | `KnowledgeSource` / `0030_knowledge_sources` | PASS |
| Admin API | `backend/app/api/v2/sources.py` | PASS |
| MCP boundary | `backend/app/integrations/mcp/` + `mcp>=1.28,<2` | PASS |
| Tests | `tests/test_phase7a_source_foundation.py` | PASS (9/9) |

## Seed registry definitions (registry-only; not live connectors)

- `gastat` — GASTAT  
- `monshaat` — Monsha'at  
- `misa` — MISA  
- `sama` — SAMA  
- `nca` — NCA  
- `zatca` — ZATCA  
- `saudi_open_data` — Saudi Open Data (**fixture connector only**)

Secrets are scrubbed from `connector_config` on write/read.

## Acceptance checklist

| Criterion | Result |
|-----------|--------|
| Source Registry persists | PASS |
| SourceConnector contract exists | PASS |
| Canonical SourceDocument exists | PASS |
| Provenance survives end-to-end into Knowledge Layer | PASS |
| One fixture connector enters existing Knowledge Layer | PASS |
| No duplicate RAG pipeline | PASS (adapter → `knowledge_service.save_ingested_document`) |
| MCP boundary works | PASS (`source_connector_health`, `source_connector_metadata`) |
| Financial / Risk / Decision behavior unchanged | PASS (no engine files touched) |
| V3 regressions green | PASS (see below) |
| Refresh/persistence works | PASS (`record_sync_result` + registry CRUD) |

## Test evidence

```text
tests/test_phase7a_source_foundation.py .............. 9 passed
tests/test_alembic_{validation,launch,growth}_migration.py
  + test_financial_trust_hardening.py
  + test_knowledge_intelligence.py
  + test_knowledge_intelligence_learning.py ......... 33 passed
tests/test_financial_trust_hardening.py
  + test_auto_migrate_gate.py
  + test_router_authz.py ............................ 31 passed
Alembic heads: ['0030_knowledge_sources']
```

Covered behaviors:

- A Registry seed/list/update + secret scrubbing  
- B Admin-only mutations; authenticated reads; 401 unauthenticated  
- C/E Schema validation; UNKNOWN stays null/UNKNOWN; no invented OFFICIAL_PRIMARY  
- D/F Incomplete / AI inference provenance cannot become `verified`  
- G Fixture connector contract (`published_at` stays null)  
- H Knowledge adapter provenance on document assumptions + chunk metadata  
- I MCP boundary smoke  

## Architecture deviations

None relative to Phase 7A scope and the V4 open-source reuse baseline.

- MCP: `modelcontextprotocol/python-sdk` (`mcp`) foundation only  
- Not added: pgvector, unstructured, LlamaIndex, CrewAI, AutoGen, Haystack, Mem0, Zep  
- Not copied: Node `ai-business-planner` search/read/cache patterns (reserved for 7B)

## Known limitations

1. No live Saudi API connectors — fixture only.  
2. Phase 7A never auto-marks `VERIFIED_EXTERNAL_FACT` / `verified`.  
3. No frontend Source Admin UI.  
4. MCP tools expose health/metadata only — no research agent runtime.  
5. Existing domain→authority classifier (`source_registry.py`) is unchanged and separate from the DB registry.

## STOP

Phase 7A complete for review. Do **not** proceed to Phase 7B automatically.
