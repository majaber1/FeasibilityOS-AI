# V4 Phase 8A Release Acceptance — Research Intelligence MVP

**Status:** MERGED  
**Date (UTC):** 2026-09-12  
**PR:** https://github.com/majaber1/saudi-business/pull/44  
**PR tip SHA:** `1435bb90f3d95316a26589c695f666fe63f9e3fa`  
**Merge SHA / Main SHA:** `6c8120fb65943ebb0df0c142f9de5aea6b31d7e0`  
**STOP:** Do **not** start Phase 8B.

## Objective

Ship Research Intelligence MVP so evidence gaps are researched **before** AI estimation, using official Saudi sources (GASTAT + MISA) through the existing study graph — without a second agent runtime, second RAG pipeline, or Financial/Risk/Decision changes.

## Architecture flow

```
Existing LangGraph
        |
Research Node
        |
MCP Boundary (source_status / source_fetch only)
        |
Source Connector
        |
Knowledge Layer (prefer knowledge hits; live fetch on miss)
        |
Evidence Pack → Evidence Agent (official beats ai_assumption)
```

Research is a LangGraph node on the existing orchestrator (`EVIDENCE_REVIEW → research → evidence`). MCP never routes into Financial, Risk, or Decision.

## PR / SHA

| Item | Value |
|------|-------|
| PR | #44 |
| Branch | `cursor/v4-phase8a-research-intelligence-1831` |
| Tip commit | `1435bb90f3d95316a26589c695f666fe63f9e3fa` |
| Merge commit | `6c8120fb65943ebb0df0c142f9de5aea6b31d7e0` |
| Main after merge | `6c8120fb65943ebb0df0c142f9de5aea6b31d7e0` |

### Scope (merged)

- `ai_engine/research/*` — planner, service, schemas, LangGraph nodes
- `ai_engine/orchestrator.py` — evidence-path research node only
- `ai_engine/agents/evidence.py` — trust gate
- `ai_engine/models/study_state.py` — research + claim provenance fields
- `backend/app/api/v2/study_engine.py` — public payload + snapshot restore
- Workspace UI claim provenance (`source_type`, `origin`, `source_url`, research status)
- Phase 8A tests + CI alignment (claim-count e2e; dual-import SQLite index fix)

### Explicitly unchanged

- Financial Engine
- Risk Engine
- Decision Engine
- Report generation
- Owner workflow (beyond evidence visibility)
- No CrewAI / AutoGen / second RAG / framework replacement

## Sources used

| Source | Phase 8A role | Live smoke |
|--------|---------------|------------|
| **GASTAT** | Saudi market / economic evidence | PASS — official claims + `stats.gov.sa` URLs |
| **MISA** | Investment climate evidence | PASS — official claims + `misa.gov.sa` URLs |
| Monsha'at | Catalogued as blocked | Not required for PASS |

Live-only sources for Phase 8A: `gastat`, `misa`.

## Trust gate result

| Gate | Result |
|------|--------|
| Research before assumption | **PASS** |
| Official evidence preferred over `ai_assumption` | **PASS** |
| No silent AI estimation when official evidence exists | **PASS** |
| Claim provenance (`source_type`, `source_url`, `origin`, `source_key`) | **PASS** |
| User-visible API + workspace UI | **PASS** |
| Orchestrator safety (Financial/Risk/Decision untouched) | **PASS** |

Evidence refs:

- `docs/evidence/V4_PHASE8A_FINAL_ACCEPTANCE.md`
- `docs/evidence/V4_PHASE8A_FINAL_GATE.json`
- `docs/evidence/V4_PHASE8A_LIVE_ACCEPTANCE.json`
- Live post-merge smoke log: `/opt/cursor/artifacts/phase8a_live_trust_smoke.log`

### Live production smoke (post-merge on main)

**Scenario A — Saudi economic evidence**

- GASTAT selected (`source_key=gastat`)
- Official claims returned (e.g. CPI inflation 1.8% Mar 2026)
- Linked to official URL (`https://www.stats.gov.sa/en/w/news/180`, …)
- Competing `ai_assumption` suppressed on merge

**Scenario B — Investment climate evidence**

- MISA selected (`source_key=misa`)
- Official claims returned (National Investment Strategy / Investment Development)
- Linked to official URL (`https://misa.gov.sa/activities/...`)
- Competing `ai_assumption` suppressed on merge

**User visibility**

- API payload exposes `research_status`, `research_context`, claim `source_type` / `source_url` / `origin` / `source_key`
- Workspace UI renders research status, official vs AI styling, clickable `source_url`

## Regression results (from main @ `6c8120f`)

| Suite | Result |
|-------|--------|
| Phase 8A research intelligence | PASS |
| Phase 8A final trust gate | PASS |
| Phase 7A Source Foundation | PASS |
| Phase 7B GASTAT live | PASS |
| Phase 7C.1 MISA | PASS |
| Knowledge Layer | PASS |
| Financial Trust hardening | PASS |
| Tenant isolation (GASTAT / MISA / Knowledge) | PASS (3) |
| Prior CI failures (e2e claims + SQLite create_all) | PASS |

Aggregate post-merge run: **95 passed** (`phase8a_postmerge_regressions.log`).

### CI on PR #44 (tip `1435bb9`)

| Check | Result |
|-------|--------|
| Backend tests & smoke import | PASS |
| Frontend build (Next.js) | PASS |
| Alembic migrations on Postgres | PASS |
| Basic secret scan | PASS |
| Docker Compose validation | PASS |
| Vercel – saudi-business-web | PASS |
| Vercel – feasibilityos-ai | FAIL (unrelated project; non-blocking) |

Workflow `CI` conclusion: **success**.

## Known limitations

1. **Monsha'at blocked external reachability** — appears only as unavailable/blocked; must not block the study; not a Phase 8A PASS dependency.
2. **Research snapshot persistence model** — `research_*` fields restore primarily via study version snapshot (row columns predate Phase 8A); claims also persist in `claims_json`.
3. **Chunk-level references stronger for Knowledge hits** — `chunk_id` is reliably set for Knowledge retrieval; live MCP docs set `document_id` when connector ids exist.
4. **Generic web research** — Phase 8B; out of scope.

## Scorecard

| Item | Result |
|------|--------|
| PHASE 8A STATUS | **MERGED** |
| Merge SHA | `6c8120fb65943ebb0df0c142f9de5aea6b31d7e0` |
| Main SHA | `6c8120fb65943ebb0df0c142f9de5aea6b31d7e0` |
| CI | **PASS** |
| Research Before Assumption | **PASS** |
| User Visible Evidence | **PASS** |
| Regression | **PASS** |
| Production Smoke | **PASS** |

## STOP

Phase 8A release closure complete. **Do not start Phase 8B automatically.**
