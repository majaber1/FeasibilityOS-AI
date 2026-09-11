# Phase 6.1 — Production Acceptance

**PR:** [#30](https://github.com/majaber1/saudi-business/pull/30) — `cursor/knowledge-intelligence-learning-1831`  
**Date:** 2026-09-11  
**Method:** Live HTTP E2E against local API on the PR branch (Alembic head `0029_knowledge_intel_learning` applied). Fresh accounts + fresh studies. No feature work beyond a one-line persistence clip required for Learning.  
**Artifacts:** `/opt/cursor/artifacts/phase61_production_acceptance/`

## Verdict

**FINAL STATUS: READY TO MERGE**

| Gate | Result |
|------|--------|
| Knowledge Quality | **PASS** |
| Similarity | **PASS** |
| Influence | **PASS** |
| Learning | **PASS** |
| Business Value | **PASS** |
| E2E | **PASS** |

## Scope exercised

Three fresh studies, each with a matching knowledge pack only (isolated tenant), plus a shared-tenant leakage ranking check:

1. **Residential** + residential knowledge pack  
2. **Data center** + data center knowledge pack  
3. **Cybersecurity services** + services knowledge pack  

For each study we verified:

- Similar projects retrieved (own pack ranked #1)
- Quality score visible on document + dashboard
- Assumptions show knowledge influence with real `document_id` / `chunk_id` refs
- Financial / Risk / Decision / Report still produced (engines unchanged in shape)
- No cross-archetype assumption-key leakage
- Persistence after GET refresh + re-login

## Case results

### 1) Residential (`real_estate`)

| Check | Result |
|-------|--------|
| Quality | **84%** — CAPEX/outcome/Saudi/recency reasons present |
| Similar projects | Own pack #1 at **66%** similarity |
| Influence | **6/6** assumptions knowledge-influenced; real document/chunk refs |
| Engines | `REPORT_READY`, verdict `DEFER`, financial keys intact (`npv`, `irr`, scenarios, …), **3** risks |
| Persistence | Influence survived refresh + re-login |
| Learning memory | Written with `conditions` + `influence_summary` |

- Study: `study_195a403a9fb6`  
- Account: `p61_residential_801e7eb7f2@example.com`

### 2) Data center (`data_center`)

| Check | Result |
|-------|--------|
| Quality | **84%** |
| Similar projects | Own pack #1 at **56%** similarity |
| Influence | **7/7** assumptions knowledge-influenced; real refs |
| Engines | `REPORT_READY`, verdict `DEFER`, financial keys intact, **3** risks |
| Persistence | Influence survived refresh + re-login |
| Learning memory | Written after clip fix (see note) |

- Study: `study_91b638de94e6`  
- Account: `p61_dc_retry_5a59582b@example.com`

### 3) Cybersecurity services (`services`)

| Check | Result |
|-------|--------|
| Quality | **86%** |
| Similar projects | Own pack #1 at **57%** similarity |
| Influence | **7/7** assumptions knowledge-influenced; real refs |
| Engines | `REPORT_READY`, verdict `GO_WITH_CONDITIONS`, NPV/IRR present, **3** risks |
| Persistence | Influence survived refresh + re-login |
| Learning memory | Written with `conditions` + `influence_summary` |

- Study: `study_370d626c3645`  
- Account: `p61_cybersecurity_465fa44127@example.com`

## No archetype leakage

Shared tenant uploaded all three packs, then queried each archetype profile:

| Query | Top hit | Pass |
|-------|---------|------|
| Residential | residential pack | **PASS** |
| Data center | data center pack | **PASS** |
| Cybersecurity | cybersecurity pack | **PASS** |

No foreign archetype keys appeared on any assumption set (`forbidden_key_leakage: []` for all cases).

## Engines unchanged

Across all three studies, Financial / Risk / Decision / Report outputs kept the existing payload shape (`analysis_complete`, `capex`, projections, `npv`, `irr`, scenarios, risks, verdict). Knowledge only attached influence metadata and similar-project context; it did not replace engine calculations.

## Learning-loop note (minimal fix)

First data-center attempt reached `REPORT_READY` with quality / similarity / influence / engines all green, but Study Memory insert failed:

`StringDataRightTruncation: value too long for type character varying(120)` on `study_memories.sector` (LLM sector prose > 120 chars).

**Fix (not a feature):** clip `archetype` / `project_type` / `sector` / `country` to column limits in `ai_engine/knowledge/memory.py` before upsert.  
Data-center re-run after fix: Learning **PASS**.

## Business value

Knowledge Intelligence materially changes study quality without changing frozen engines:

- Uploaded packs receive actionable **quality scores**
- Retrieval returns **ranked similar projects** with sector/geography/quality reasons
- Assumptions carry **traceable knowledge influence** (real document/chunk ids)
- Completed studies write **learning memories** (`conditions`, `influence_summary`) for future retrieval
- Archetypes stay isolated (no pack/assumption leakage)

## Evidence files

- `/opt/cursor/artifacts/phase61_production_acceptance/acceptance_results.json`
- `/opt/cursor/artifacts/phase61_production_acceptance/case_residential.json`
- `/opt/cursor/artifacts/phase61_production_acceptance/case_data_center.json`
- `/opt/cursor/artifacts/phase61_production_acceptance/case_cybersecurity.json`
