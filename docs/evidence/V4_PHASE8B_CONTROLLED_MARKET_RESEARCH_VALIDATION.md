# V4 Phase 8B — Controlled Market Research Intelligence Validation

**Status:** PASS (implementation + full validation audit)  
**Date (UTC):** 2026-09-12  
**Branch:** `cursor/v4-phase8b-controlled-market-research-1831`  
**Commit:** `e26d9af621a58ddda04313f464943ba57201fc24`  
**Baseline main:** `6c8120fb65943ebb0df0c142f9de5aea6b31d7e0` (Phase 8A merged)  
**STOP:** Do **not** start Phase 8C.

## Objective

Ship Controlled Market Research Intelligence so studies can answer competitor / market / pricing / regulation questions using **sourced evidence only**, through the existing LangGraph → Research → MCP → Source → Knowledge → Evidence Pack path.

**Core rule:** Research → Evidence → Knowledge → Assumption  
**Never:** Search → LLM summary → Decision

## Architecture changes

```
Existing LangGraph
        |
Research Node (Phase 8A)
        |
Market Research module (Phase 8B)  ← NEW, same runtime
        |
MCP Boundary (source_status / source_fetch only)
        |
Source Connector (GASTAT / MISA live only)
        |
Knowledge Layer (no second RAG / vector DB)
        |
Evidence Pack → Evidence Agent (official beats ai_assumption)
```

### New package

`ai_engine/research/market/`

| File | Role |
|------|------|
| `schemas.py` | ResearchType, CompetitorEvidence, MarketSignal, PricingSignal, RegulationSignal, MarketInsight, plan/result |
| `planner.py` | Classify COMPETITOR / MARKET_SIZE / PRICING / REGULATION / SECTOR_SIGNAL; select GASTAT/MISA + SAMA/ZATCA/NCA placeholders |
| `competitor.py` | Evidence-only competitors; NOT_FOUND / NOT_VERIFIED; never invent |
| `market_signal.py` | Official metric extraction + CONFLICT detection |
| `pricing_signal.py` | Evidence-based prices only; reject ai_assumption |
| `regulation.py` | Framework placeholders only (no new connectors) |
| `service.py` | Orchestrate market research, cache, map insights → ResearchClaim |

### Wiring (non-invasive)

- `ai_engine/research/service.py` — after official Knowledge/MCP claims, run market synthesis over collected evidence; attach `market_research` to `ResearchResult`
- `ai_engine/research/nodes/research.py` — persist `market_research_context` on StudyState
- `ai_engine/models/study_state.py` — `market_research_context`
- `backend/app/api/v2/study_engine.py` — public payload + snapshot restore
- Workspace UI — market research panel (insight, source, URL, evidence ref, confidence)

### Explicitly unchanged

- Financial Engine
- Risk Engine
- Decision Engine
- Report Engine
- No second agent runtime / CrewAI / AutoGen
- No unrestricted web search / generic AI web agent
- No second RAG / vector database
- No new live connectors (SAMA/ZATCA/NCA placeholders only)

## Source governance

| Source | Phase 8B role |
|--------|----------------|
| GASTAT | Live economic / sector signals |
| MISA | Live investment signals |
| SAMA / ZATCA / NCA | Placeholders only |
| Monsha'at | Remains blocked (not required) |

No arbitrary URL fetching in the market module. Evidence URLs are references only; live retrieval remains GASTAT/MISA via existing MCP/connectors + SafePageReader allowlists.

## Trust gate results

| Gate | Result |
|------|--------|
| Market Research Planner | **PASS** |
| Competitor Intelligence (no invention) | **PASS** |
| Market Signals (no silent estimation) | **PASS** |
| Pricing Signals (evidence-only) | **PASS** |
| Regulation Framework (placeholders) | **PASS** |
| Knowledge Integration (same Evidence Pack path) | **PASS** |
| Evidence Trust (official > ai_assumption) | **PASS** |
| Conflict detection (no silent override) | **PASS** |
| Security (no arbitrary fetch / SSRF helpers intact) | **PASS** |
| Performance cache | **PASS** |
| Regression (8A/7A/7B/MISA/Knowledge/Financial Trust) | **PASS** |

## Business scenarios

### A — Saudi retail / SME

- Market research runs; GASTAT/MISA selected
- Competitors without evidence → NOT_FOUND
- CPI signal from official GASTAT URL → VERIFIED claim
- Assumptions only linked via verified evidence claims

### B — Investment project

- MISA FDI evidence selected/visible
- Investment signal (`fdi_inflow`) returned with source key + reference

### C — No available evidence

- Status NOT_FOUND / PARTIAL
- Zero invented competitor/price/market-size claims

### D — Conflicting evidence

- Same metric+period different values → CONFLICT
- No silent override

## AI trust audit

| Question | Expected | Result |
|----------|----------|--------|
| Who are the competitors? | Only verified / else NOT_FOUND | PASS — empty names without evidence |
| What is market size? | Evidence or UNKNOWN | PASS — no unsupported TAM number |

## Automated tests

`tests/test_phase8b_controlled_market_research.py` — **28 passed**

Coverage: planner, schemas/competitors, market signals, pricing, regulation, scenarios A–D, AI trust, knowledge merge, security, cache/perf, orchestrator safety, UX payload.

## Regression

Aggregate with Phase 8A / 7A / 7B / MISA / Knowledge / Financial Trust: **115 passed**.

Tenant isolation (GASTAT / MISA / Knowledge): **PASS**.

## Live acceptance

See `docs/evidence/V4_PHASE8B_TEST_RESULTS.json` and `/opt/cursor/artifacts/phase8b_live_acceptance.log`.

| Check | Result |
|-------|--------|
| Scenario A retail | PASS |
| Scenario B investment | PASS |
| Scenario C empty | PASS |
| Scenario D conflict | PASS |
| Cache/perf | PASS |
| Security no httpx | PASS |

## Security results

- Market module does not call `httpx` / open-web fetch for synthesis
- Existing SafePageReader allowlist + private IP rejection remain for GASTAT/MISA connectors
- Redirect/content limits unchanged in Phase 7B research security helpers

## Performance results

- First synthesis: sub-millisecond on provided evidence fixtures
- Cached repeat increments `cache_hits` and avoids recompute
- Duplicate ingestion avoided by synthesizing over already-collected research claims (no second crawl)

## Failed tests

None in Phase 8B suite / regression aggregate for this gate.

## Known limitations

1. **Monsha'at** remains blocked external reachability (not a Phase 8B dependency).
2. **Competitor discovery** requires uploaded/official sourced mentions — no open-web competitor crawler (by design).
3. **SAMA / ZATCA / NCA** are framework placeholders only — no live connectors.
4. **Pricing** requires official/user evidence text with explicit SAR amounts — no estimated price tables.
5. **Market size / TAM** is not invented; without numeric official evidence the system returns NOT_FOUND/UNKNOWN.
6. **Research persistence model** still primarily uses version snapshots for research/market context fields.

## Architecture deviations

None material. Phase 8B extends the existing Research node path; no second runtime, RAG, or engine replacement.

## STOP

Phase 8B Controlled Market Research MVP + validation audit complete.  
**Do not start Phase 8C automatically.**
