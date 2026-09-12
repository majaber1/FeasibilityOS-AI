# V4 Phase 7C.1 — Saudi Sources Validation (Monsha'at + MISA)

**Status:** NOT PASS  
**Branch:** `cursor/v4-phase7c1-saudi-sources-1831`  
**Commit:** `c1134190095bce3e8f78452ec0c62aa0c0c32dc2`  
**Baseline V3 frozen:** `v3.0.0` @ `33e216e2ed939b065bca0357c3855184e219a68d`  
**Phase 7A:** `dc2117bf1a001f85f859d685100fb528b2933d70`  
**Phase 7B:** `64cfd189fe7046ea93efd03def9068b498e21166`  
**Architecture baseline:** `docs/architecture/V4_OPEN_SOURCE_REUSE_BASELINE.md` (unchanged)

## Goal

Add two official Saudi sources through the existing governed pipeline:

`Official Saudi Source → SourceConnector → SourceDocument → Validation + Provenance → Knowledge Layer → Evidence Pack → Study retrieval`

No agents. No second RAG pipeline. Financial / Risk / Decision / Archetype / Study Workflow unchanged.

## Delivered

| Area | Location | Result |
|------|----------|--------|
| Monsha'at connector | `backend/app/integrations/sources/monshaat.py` | PASS (contract); live E2E blocked |
| MISA connector | `backend/app/integrations/sources/misa.py` | PASS |
| Registry seeds | `backend/app/services/source_registry_service.py` | PASS |
| Domain / SSRF reuse | Phase 7B `SafePageReader` / research security | PASS |
| Knowledge adapter | existing knowledge adapter | PASS |
| API sync/documents | existing `/api/v2/sources/{id}/sync\|documents` | PASS |
| MCP boundary | `source_status`, `source_fetch` | PASS |
| Tests A–K | `tests/test_phase7c1_saudi_sources.py` | PASS (20/20) |

## Live acceptance

**Capture timestamp (UTC):** `2026-09-12T20:17:16.314466+00:00`  
**Artifact:** `docs/evidence/V4_PHASE7C1_live_acceptance.json`

### MISA — PASS (2 live official pages)

| # | Title | Official URL | content_hash | knowledge_document_id | chunk_ids | retrieved_at |
|---|-------|--------------|--------------|-----------------------|-----------|--------------|
| 1 | National Investment Strategy - MISA | `https://misa.gov.sa/activities/national-investment-strategy/` | `ebfa7fb06f1c29e42e73033eb05244be73fdef9c363da7a147e8766e3812c194` | `69f33f94-38b8-4571-9729-88f6eeff5c81` | `3e47e93e-3458-44a9-ae38-f7ac425a19e0`, `cda602ce-5164-4525-ab02-3d7112b01c15` | `2026-09-12T20:17:34.928704+00:00` |
| 2 | Investment Development - MISA | `https://misa.gov.sa/activities/investment-development/` | `7b4e6eac702f8bb1c8e09c87e9f0f63aea09950566706f6ef5bd6758fdbd020f` | `4e55f605-a98f-4158-8a60-74eda68ee0ad` | `be5dd051-0dea-4060-9bb9-802f1abcd334`, `cdd116a9-c7ff-454c-9bbf-01850728fff3` | `2026-09-12T20:17:36.286795+00:00` |

**MISA health:** `healthy` — `MISA home reachable` @ `2026-09-12T20:17:33.684216+00:00`

**Retrieval question (no hardcoded answers):**  
`What does MISA say about National Investment Strategy and investment development?`

Citations returned (ingested MISA knowledge IDs):

- `document_id=4e55f605-a98f-4158-8a60-74eda68ee0ad` — ion and development of investment opportunities published on Invest Saudi In enhancing and improving policy & regulation With enablement and entailments to fost
- `document_id=69f33f94-38b8-4571-9729-88f6eeff5c81` — 30% in 2030 (*as measured by Gross Fixed Capital Formation) Catalyze new investment across existing and emerging sectors Target Initiatives 01 Investment Opport

Provenance preserved on Knowledge assumptions/`external_source`: `source_id`, `url`, `content_hash`, `retrieved_at`, `provenance.connector_id=live.misa`, `provenance.registry_key=misa`, `provenance.original_url`.

### Monsha'at — FAIL (live E2E)

| Check | Result |
|-------|--------|
| Official domains allowlisted | PASS (`monshaat.gov.sa`, `www.monshaat.gov.sa`) |
| Connector contract (stubbed official pages) | PASS |
| Live health | `unavailable` — `timeout fetching https://www.monshaat.gov.sa/en` @ `2026-09-12T20:17:32.342079+00:00` |
| Live documents (minimum 2) | **0** (TLS handshake times out from this agent network) |

Default official URLs attempted (not fetched live):

- `https://www.monshaat.gov.sa/en/monshaat-reports`
- `https://www.monshaat.gov.sa/en/node/274250`

**Policy respected:** no mirrors, no invented dates/statistics/sector/authority, unknown remains UNKNOWN, connector returns empty retrieve on outage.

## Business scenario validation

| Scenario | Expected | Result |
|----------|----------|--------|
| A — Startup feasibility study | Monsha'at evidence can support SME / market context | PASS via stubbed official-domain pages + Knowledge retrieve (live Monsha'at blocked) |
| B — Foreign investment project | MISA evidence can support investment context | PASS live (citations from ingested MISA docs) |

Financial calculations were **not** modified; only evidence availability was verified.

## Failure tests

| Probe | Result |
|-------|--------|
| Non-allowlisted domain | `UrlSecurityError: host not in allowlist: example.com` |
| SSRF localhost | `UrlSecurityError: host not in allowlist: 127.0.0.1` |
| Monsha'at live timeout | `unavailable` + empty retrieve |
| Duplicate ingest by content_hash | idempotent reuse (tests) |
| Tenant isolation | other owner cannot see ingested docs (tests) |

## Regression

```text
tests/test_phase7a_source_foundation.py
tests/test_phase7b_gastat_live_source.py
tests/test_phase7c1_saudi_sources.py
64 passed
```

Phase 7C.1 suite alone: **20 passed**.

## Acceptance scorecard

| Criterion | Result |
|-----------|--------|
| Monsha'at Connector (contract) | PASS |
| Monsha'at Live E2E (2 sources) | FAIL (TLS timeout) |
| MISA Connector | PASS |
| MISA Live E2E (2 sources) | PASS |
| Security / SSRF | PASS |
| Knowledge Integration | PASS |
| Evidence citations | PASS (MISA live; Monsha'at stubbed) |
| Business Scenario Validation | PASS (with Monsha'at live caveat) |
| V3 Regression | PASS |
| Phase 7B Regression | PASS |
| **PHASE 7C.1 STATUS** | **NOT PASS** |

## Architecture deviations

None material. Reused existing Source Registry, SourceConnector, SafePageReader, content cleaner, knowledge adapter, Evidence Pack, and MCP connector-only boundary.

## Known limitations

- Monsha'at official site TLS handshake fails from this Cloud Agent egress path; live Monsha'at acceptance cannot be completed here without network reachability.
- Sector left null unless explicitly present (never invented).
- HTML cleanup remains heuristic; no summarization during ingest.
- MCP `source_fetch` does not write Knowledge/assumptions.
- Other ministry connectors and Research Agent remain out of scope.

## STOP

Do not start Phase 8 automatically.
