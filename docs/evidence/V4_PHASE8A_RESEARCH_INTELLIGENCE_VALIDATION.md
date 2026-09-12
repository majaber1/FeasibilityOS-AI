# V4 Phase 8A — Research Intelligence MVP Validation

**Status:** PASS  
**Branch:** `cursor/v4-phase8a-research-intelligence-1831`  
**Base:** `main` (post MISA merge `4783086`)  
**STOP:** Do **not** begin Phase 8B.

## Scope

Research-before-assumption path on the existing LangGraph orchestrator:

`Study Gap → Research Planner → Source Registry / MCP → SourceConnector → SourceDocument → Knowledge → Evidence Pack → Evidence Agent → reviewable ai_assumption`

Hard constraints honored:

- No CrewAI / AutoGen / second RAG / new orchestration runtime
- MCP tools used: `source_status` / `source_fetch` only (never Financial / Risk / Decision)
- Knowledge-first; no generic web search (Phase 8B)
- Monsha'at may appear only as unavailable/blocked and must not fail the study
- AI assumption is low-confidence / reviewable and cannot override official research claims
- Langfuse via existing `get_langfuse()` (optional; absence does not break)

## Architecture

| Component | Location |
|-----------|----------|
| Schemas | `ai_engine/research/schemas.py` |
| Planner | `ai_engine/research/planner.py` |
| Service | `ai_engine/research/service.py` |
| LangGraph node | `ai_engine/research/nodes/research.py` |
| Evidence validator | `ai_engine/research/nodes/evidence_validator.py` |
| Trust merge in evidence agent | `ai_engine/agents/evidence.py` |
| Graph wiring | `EVIDENCE_REVIEW → research → evidence → END` in `ai_engine/orchestrator.py` |
| StudyState fields | `research_context`, `research_status`, `research_attempts` |

Live Phase 8A sources: **GASTAT** + **MISA**. Monsha'at remains `BLOCKED_EXTERNAL_REACHABILITY`.

## Unit / integration tests

`tests/test_phase8a_research_intelligence.py` — **15 passed**

Coverage:

- A Planner maps inflation→gastat, FDI→misa, SME→blocked monshaat
- B Knowledge-first short-circuit; live MCP fetch produces official claims
- C Monsha'at blocked does not raise / fail study
- D Trust gate: official wins over `ai_assumption`; assumptions only after research
- E Orchestrator routes `EVIDENCE_REVIEW` → `research`
- F Research node + evidence validator

## Regressions

| Suite | Result |
|-------|--------|
| Orchestrator routing / phase transitions | 7 passed |
| Phase 7A + 7B + MISA | 44 passed |

## Live acceptance (this environment)

| Study | Gaps | Result |
|-------|------|--------|
| GASTAT | Official inflation / GDP / labor statistics | **complete**, 3 official claims, 1 live fetch |
| MISA (+ indicator overlap) | Official FDI / investment climate | **complete**, 5 official claims, 2 live fetches |
| Mixed | monshaat SME + inflation | **complete**, monshaat in `blocked_sources`, study continues |

Sample official claim (GASTAT):

- Statement: Inflation in Saudi Arabia reaches 1.8% in March 2026 …
- `source_type=official`
- URL: `https://www.stats.gov.sa/en/w/news/180`

Trust merge after live research: only `official` types remain (prior `ai_assumption` dropped).

Gate after research: `research_ran=True`, `allow_ai_assumption=True`, `official_claim_count≥1`.

## Scorecard

| Criterion | Result |
|-----------|--------|
| Research runs before AI assumption on evidence path | PASS |
| Knowledge-first then MCP connector fetch | PASS |
| GASTAT live research claims | PASS |
| MISA live research claims | PASS |
| Monsha'at blocked does not fail study | PASS |
| Official claims beat `ai_assumption` | PASS |
| No Financial/Risk/Decision math changes | PASS |
| No second agent runtime | PASS |
| Langfuse optional / non-blocking | PASS |
| Phase 8B not started | PASS (STOP) |

## STOP

Phase 8A complete. **Do not start Phase 8B** (generic web research) automatically.
