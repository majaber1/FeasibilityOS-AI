# V4 Phase 7C.1 — Saudi Sources Validation (Monsha'at + MISA)

**Status:** NOT PASS  
**Branch:** `cursor/v4-phase7c1-saudi-sources-1831`  
**Commit:** `7ba3530f54fe2647641a1a9c89efdba317ca30a8`  
**Baseline V3 frozen:** `v3.0.0` @ `33e216e2ed939b065bca0357c3855184e219a68d`  
**Phase 7A:** `dc2117bf1a001f85f859d685100fb528b2933d70`  
**Phase 7B merge SHA:** `af8c2d65ec165e3b5cc42c9a6a30085aab2f193f`  
**Architecture baseline:** `docs/architecture/V4_OPEN_SOURCE_REUSE_BASELINE.md` (unchanged)

## Goal

Add two official Saudi sources through the existing governed pipeline:

`Official Saudi Source → SourceConnector → SourceDocument → Validation + Provenance → Knowledge Layer → Evidence Pack → Study retrieval`

No agents. No second RAG pipeline. Financial / Risk / Decision / Archetype / Study Workflow unchanged.

Monsha'at retrieval priority (Phase 7C.1 remediation):

1. Official Real-Time Open Data API (`pservices.monshaat.gov.sa`)
2. Official Monsha'at report / document URL
3. Official public HTML page (best-effort)

## Delivered

| Area | Location | Result |
|------|----------|--------|
| Monsha'at official API path | `backend/app/integrations/sources/monshaat.py` | PASS (contract + mocked); live TLS blocked |
| Monsha'at domain allowlist | `monshaat.gov.sa`, `www.monshaat.gov.sa`, `pservices.monshaat.gov.sa` | PASS |
| Health semantics (healthy / degraded / unavailable) | `MonshaatConnector.health` | PASS (tests) |
| MISA connector | `backend/app/integrations/sources/misa.py` | PASS |
| Registry seeds | `backend/app/services/source_registry_service.py` | PASS |
| Domain / SSRF reuse | Phase 7B `SafePageReader` / research security | PASS |
| Knowledge adapter | existing knowledge adapter | PASS |
| MCP boundary | `source_status`, `source_fetch` | PASS |
| Tests A–K + API | `tests/test_phase7c1_saudi_sources.py` | PASS (22/22) |

## Live acceptance

**Capture timestamp (UTC):** `2026-09-12T21:14:05.633631+00:00`  
**Artifacts:** `docs/evidence/V4_PHASE7C1_live_acceptance.json`, `/opt/cursor/artifacts/phase7c1_live_probe.json`

### MISA — PASS (2 live official pages)

| # | Title | Official URL | content_hash | knowledge_document_id | chunk_ids | retrieved_at |
|---|-------|--------------|--------------|-----------------------|-----------|--------------|
| 1 | National Investment Strategy - MISA | `https://misa.gov.sa/activities/national-investment-strategy/` | `ebfa7fb06f1c29e42e73033eb05244be73fdef9c363da7a147e8766e3812c194` | `69f33f94-38b8-4571-9729-88f6eeff5c81` | `3e47e93e-3458-44a9-ae38-f7ac425a19e0`, `cda602ce-5164-4525-ab02-3d7112b01c15` | `2026-09-12T20:17:34.928704+00:00` |
| 2 | Investment Development - MISA | `https://misa.gov.sa/activities/investment-development/` | `7b4e6eac702f8bb1c8e09c87e9f0f63aea09950566706f6ef5bd6758fdbd020f` | `4e55f605-a98f-4158-8a60-74eda68ee0ad` | `be5dd051-0dea-4060-9bb9-802f1abcd334`, `cdd116a9-c7ff-454c-9bbf-01850728fff3` | `2026-09-12T20:17:36.286795+00:00` |

**MISA health (recheck):** `healthy` — `MISA home reachable` @ `2026-09-12T21:15:54.226119+00:00`  
**MISA live recheck retrieve_count:** `2` (same official URLs / content hashes)

Provenance preserved: `provenance.connector_id=live.misa`, `provenance.registry_key=misa`, `provenance.original_url`, `content_hash`, `retrieved_at`.

### Monsha'at — FAIL (live E2E; official API path implemented)

| Check | Result |
|-------|--------|
| Official domains allowlisted | PASS (`monshaat.gov.sa`, `www.monshaat.gov.sa`, `pservices.monshaat.gov.sa`) |
| Official API URL builder | PASS (`EnterprisesStatistics/{Year}/{Quarter}?paginationIndex=&recordsPerPage=`) |
| API → SourceDocument normalization (mocked) | PASS (`retrieval_method=official_api`, year/quarter/query preserved; no invented fields) |
| Health: API-only → DEGRADED | PASS (tests) |
| Health: HTML-only → DEGRADED | PASS (tests) |
| Health: both fail → UNAVAILABLE | PASS (tests + live) |
| Live health | `unavailable` — API TLS handshake timeout + HTML timeout @ `2026-09-12T21:14:33.705207+00:00` |
| Live official API artifacts (minimum 2) | **0** |
| Knowledge document / chunk / Evidence IDs (Monsha'at) | **none** (no live fetch succeeded) |

Exact official API URLs tested (live):

1. `https://pservices.monshaat.gov.sa/BI/TaskService/OpenData/EnterprisesStatistics/2023/4?paginationIndex=1&recordsPerPage=5`  
   — failed: `_ssl.c:983: The handshake operation timed out`
2. `https://pservices.monshaat.gov.sa/BI/TaskService/OpenData/EnterprisesStatistics/2024/1?paginationIndex=1&recordsPerPage=5`  
   — failed: `_ssl.c:983: The handshake operation timed out`

Network notes from agent VM:

- DNS resolves `pservices.monshaat.gov.sa` → `185.118.120.212`
- TCP connect to `:443` succeeds
- TLS ClientHello receives no ServerHello (SSL connection timeout)
- Same class of failure for `www.monshaat.gov.sa` HTML

Default official HTML URLs (not fetched live):

- `https://www.monshaat.gov.sa/en/monshaat-reports`
- `https://www.monshaat.gov.sa/en/node/274250`

**Policy respected:** no mirrors, no search-engine caches, no hardcoded statistics, no invented dates/sector/authority; connector returns empty retrieve on outage.

## Business scenario validation

| Scenario | Expected | Result |
|----------|----------|--------|
| A — Startup feasibility study | Monsha'at evidence can support SME / market context | PASS via stubbed official API + HTML fixtures + Knowledge retrieve (live Monsha'at blocked) |
| B — Foreign investment project | MISA evidence can support investment context | PASS live |

Financial calculations were **not** modified; only evidence availability was verified.

## Failure tests

| Probe | Result |
|-------|--------|
| Non-allowlisted domain | `UrlSecurityError: host not in allowlist: example.com` |
| SSRF localhost | `UrlSecurityError: host not in allowlist: 127.0.0.1` |
| Monsha'at live API+HTML outage | `unavailable` + empty retrieve |
| HTML timeout while API healthy | connector `degraded` (tests; not live) |
| Duplicate ingest by content_hash | idempotent reuse (tests) |
| Tenant isolation | other owner cannot see ingested docs (tests) |

## Regression

```text
tests/test_phase7a_source_foundation.py
tests/test_phase7b_gastat_live_source.py
tests/test_phase7c1_saudi_sources.py
50 passed
```

Phase 7C.1 suite alone: **22 passed**.  
GASTAT live smoke (post–Phase 7B merge / on this branch): **SMOKE_OK** (`healthy`, 3 docs).

## Acceptance scorecard

| Criterion | Result |
|-----------|--------|
| Monsha'at Official API (contract) | PASS |
| Monsha'at Official API (live) | FAIL (TLS handshake timeout) |
| Monsha'at Live E2E (2 sources) | FAIL |
| MISA Connector | PASS |
| MISA Live E2E (2 sources) | PASS |
| Security / SSRF | PASS |
| Knowledge Integration | PASS |
| Evidence citations | PASS (MISA live; Monsha'at mocked only) |
| Business Scenario Validation | PASS (with Monsha'at live caveat) |
| V3 / Phase 7A / Phase 7B Regression | PASS |
| **PHASE 7C.1 STATUS** | **NOT PASS** |

## Architecture deviations

None material. Official Monsha'at API is a retrieval path inside `MonshaatConnector` → existing `SourceDocument` / Knowledge / Evidence pipeline. No separate API ingestion system. No Unstructured dependency.

## Known limitations

- Monsha'at official hosts accept TCP but do not complete TLS from this Cloud Agent egress path; live Monsha'at acceptance cannot PASS here without reachability.
- Sector / publication date left null unless explicitly present (never invented).
- HTML cleanup remains heuristic; no summarization during ingest.
- MCP `source_fetch` does not write Knowledge/assumptions.
- Other ministry connectors and Research Agent remain out of scope.
- Phase 8 not started. PR #41 not merged.

## STOP

Do not start Phase 8 automatically.
Do not merge PR #41 until Monsha'at live E2E is PASS.
