# V4 Phase 8A — Final Acceptance Gate

**Status:** PASS (merge-ready with known limitations noted)  
**PR:** https://github.com/majaber1/saudi-business/pull/44  
**Branch:** `cursor/v4-phase8a-research-intelligence-1831`  
**Base:** `main`  
**STOP:** Do **not** start Phase 8B.

## 1. Orchestrator safety — PASS

### Files changed (Phase 8A scope)

| Path | Role |
|------|------|
| `ai_engine/research/*` | New research package (planner/service/schemas/nodes) |
| `ai_engine/orchestrator.py` | `EVIDENCE_REVIEW → research → evidence` |
| `ai_engine/agents/evidence.py` | Trust gate: official wins over `ai_assumption` |
| `ai_engine/models/study_state.py` | `research_*` fields + claim provenance |
| `backend/app/api/v2/study_engine.py` | Public payload + snapshot restore for research |
| `apps/web/.../workspace/page.tsx` | Show source_type / origin / url / research_status |
| `tests/test_phase8a_*.py`, `tests/test_v2_study_engine.py` | Coverage + regression update |
| `docs/evidence/V4_PHASE8A_*.md` | Evidence |

### Unchanged (verified by diff vs `main`)

- `ai_engine/agents/financial_analyst.py` — **not modified**
- `ai_engine/agents/risk.py` — **not modified**
- `ai_engine/agents/decision.py` — **not modified**
- Report generation paths — **not modified**

### Routing

| Phase | Node |
|-------|------|
| `EVIDENCE_REVIEW` | `research` → `evidence` |
| `READY_FOR_ANALYSIS` | `financial` |
| `ANALYZED` | `risk` |
| `DECISION_READY` | `decision` |

Research enhances the evidence stage only.

## 2. Evidence trust — PASS

Case: official GASTAT/MISA evidence + competing generic AI estimate.

| Check | Result |
|-------|--------|
| Official claims selected | PASS |
| `ai_assumption` suppressed when official present | PASS |
| `source_type=official` | PASS |
| `origin=research` (or `knowledge`) | PASS |
| `source_url` present on live official claims | PASS |
| `document_id` populated when available | PASS |
| `chunk_id` populated for knowledge hits when available | PASS |

Live merge sample: prior AI inflation estimate removed; official GASTAT/MISA claims remain.

Tests: `tests/test_phase8a_final_trust_gate.py::TestEvidenceTrust`

## 3. Persistence — PASS

Flow validated:

1. Research executed → claims + `research_context` / `research_status` / `research_attempts` saved  
2. Reload study (simulates refresh / logout / login / reopen via `_save_study` → `_load_study`)  
3. Restored from version snapshot for research fields (row columns predate Phase 8A)

Verified after reload:

- `research_status` / `research_context` / `research_attempts`
- claims with `source_type`, `source_url`, `origin`, `document_id`, `chunk_id`

Tests: `tests/test_phase8a_final_trust_gate.py::TestPersistence`

## 4. API / UI visibility — PASS

API public payload exposes:

- `research_status`, `research_context`, `research_attempts`
- claims with `source_type`, `confidence`, `source_url`, `origin`, `document_id`, `chunk_id`, `source_key`

Workspace UI (`workspace/page.tsx`) shows:

- research status line
- claim `source_type` (official vs ai_assumption styled)
- origin, confidence, source_key
- clickable `source_url`
- document/chunk ids when present

No hidden research: status and provenance are user-visible.

## 5. Regression — PASS

| Suite | Result |
|-------|--------|
| Phase 8A research + final trust gate | PASS (22) |
| Financial Trust hardening | PASS (included in 90) |
| Phase 7A source foundation | PASS |
| Phase 7B GASTAT live | PASS |
| Phase 7C.1 MISA | PASS |
| V2 study engine (updated approve-profile expectation) | PASS |
| Projects auth + CRUD (owner-relevant) | PASS |

V2 note: `test_approve_profile_fills_claims_when_groq_missing` updated for Phase 8A — when research succeeds, official claims are expected instead of an all-`ai_assumption` pack.

## Scorecard

| Gate | Result |
|------|--------|
| Research Before Assumption | **PASS** |
| Evidence Trust | **PASS** |
| Persistence | **PASS** |
| API / UI Visibility | **PASS** |
| Regression | **PASS** |
| Orchestrator Safety | **PASS** |

## Architecture deviation

None material. Research is a LangGraph node on the existing orchestrator; no second agent runtime; MCP remains connector-only (`source_status` / `source_fetch`).

## Known limitations

1. `research_*` fields restore primarily via **version snapshot**, not dedicated ORM columns (acceptable; claims also live in `claims_json`).
2. Monsha'at remains **blocked** (`BLOCKED_EXTERNAL_REACHABILITY`) and must not be required for PASS.
3. `chunk_id` is reliably set for Knowledge hits; live MCP documents set `document_id` when connector ids exist.
4. Generic web research (Phase 8B) is **out of scope**.

## STOP

Phase 8A final gate complete. **Do not start Phase 8B.**
