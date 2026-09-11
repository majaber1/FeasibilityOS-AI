# Assumption Review Approval Fix

**Date:** 2026-09-11  
**Branch:** `cursor/assumption-review-approval-fix-1831`  
**PR:** https://github.com/majaber1/saudi-business/pull/24  
**Status:** PASS (reproduction + fix + browser E2E + regression)

## CURRENT V2 model (preserved)

`Assumption` fields (no per-row status enum):

- `key`, `value`, `source`, `confidence`, `low`/`base`/`high`
- `origin` (`user` | `ai_estimated` | `document` | `default` | `rule_fallback`)
- `ai_estimated`, labels, `unit`, `input_type`

Study-level gate only: `assumptions_approved: bool` + phase `ASSUMPTIONS_REVIEW` → `READY_FOR_ANALYSIS`.

A prior draft incorrectly added `PENDING_REVIEW` / `EDITED` / `REJECTED`. That was **reverted**. Reject = remove row from `assumptions` (not a parallel lifecycle).

## 1) Reproduction (pre-fix)

Stuck study created for browser:

- URL: `http://127.0.0.1:3000/projects/308/studies/study_2ac1eafb9192/workspace`
- Artifact: `/opt/cursor/artifacts/assumption-stuck-pre-fix-state.json`
- UI screenshot: `/opt/cursor/artifacts/assumption-stuck-pre-fix-ui.webp`

| Field | Value |
|-------|-------|
| phase | `ASSUMPTIONS_REVIEW` |
| assumptions count | `0` |
| assumptions | `[]` |
| assumptions_approved | `false` |
| evidence_approved | `true` |
| error | `null` (DB-seeded stuck) / `AI service error: …` on live get_llm failure |
| per-assumption status | N/A (no status field in model) |

Frontend:

- Panel gate (pre-fix): `phase === ASSUMPTIONS_REVIEW && assumptions.length > 0` → **panel hidden**
- Approve disable: `loading \|\| assumptions.length === 0` → **disabled=true** (confirmed in DevTools)

## 2) Exact disable reason (proven)

**`assumptions.length === 0` while phase is `ASSUMPTIONS_REVIEW`.**

Disproved as primary causes for this stuck study:

| Hypothesis | Result |
|------------|--------|
| phase mismatch | No — phase correctly `ASSUMPTIONS_REVIEW` |
| draft/rejected rows | No — array empty; no status model |
| assumptions_approved mismatch | No — false, as expected pre-approve |
| stale frontend state | No — GET API also returned count 0 |
| API validation on click | N/A — button never enabled |
| loading/error alone | No — loading false; error null on seeded stuck |

## 3) Architectural root cause

`ai_engine/agents/assumption.py` called `get_llm("assumptions")` **outside** the try/except.

`approve_stage(evidence)` sets `phase = ASSUMPTIONS_REVIEW` **before** `run_study_step`. If LLM client init raises, the exception is caught at the API layer, phase stays `ASSUMPTIONS_REVIEW`, and `assumptions` remains `[]`.

That is a **state-machine / generation defect**, not a missing Approve enablement rule.

Unit proof (pre-fix): `get_llm` raising → `run_assumptions` aborts → `assumptions=[]`.  
Unit proof (post-fix): same raise → Rule Fallback seeds non-empty numeric rows.

## 4) Exact fix (smallest)

1. Move `get_llm` inside try/except; on failure seed **Rule Fallback** rows with numeric defaults (never empty/`TBD`).
2. After evidence approve: if still `ASSUMPTIONS_REVIEW` and empty → rebuild via `run_assumptions`.
3. Regenerate: clear + hard-guarantee rebuild if empty.
4. UX on **current** fields: Approve / Edit / Reject / Regenerate / Why (source/origin/confidence/L-B-H).
5. Bulk CTA: **Approve all eligible assumptions** — disabled only with an explicit visible reason (loading / no rows / all values empty). Rejected rows are removed, never silently approved. Empty values block bulk approve with a banner.

**DB CHANGE:** NO  
**API CHANGE:** YES (additive `POST .../assumptions/action` for approve|reject|regenerate mapped to existing fields)

## 5) Browser E2E

### Stuck study repair
- Regenerate → rows appear → Approve all eligible → Analyzed + financials  
- Artifact: `/opt/cursor/artifacts/assumption-e2e-stuck-study-analyzed.webp`

### Fresh SaaS (project 311 / `study_24b54764b5c8`)
- Cards with Approve/Edit/Reject/Regenerate/Why  
- Bulk enabled → Analyzed with financial panel  
- Refresh + logout/login persistence  

<img src="/opt/cursor/artifacts/assumption-e2e-review-enabled.webp" alt="Eligible approve enabled" />
<img src="/opt/cursor/artifacts/assumption-e2e-after-approve-financial.webp" alt="After approve financial" />
<img src="/opt/cursor/artifacts/assumption-e2e-persistence-reload.webp" alt="Persistence after reload" />

### API SaaS full path
`saas_e2e_*` → `ASSUMPTIONS_REVIEW` → card approve/edit/reject/regen → bulk → `ANALYZED` → `REPORT_READY` (`verdict=DEFER`).  
Artifact: `/opt/cursor/artifacts/assumption-saas-api-journey.json`

## 6) Archetype regression (API)

| Case | Archetype | Assumptions | Financial | SaaS leak | Mobility leak |
|------|-----------|-------------|-----------|-----------|---------------|
| Residential | `real_estate` | 7 | yes | none | none |
| Data Center | `data_center` | 10 | yes | none | none |
| Professional Services | `services` | 7 | yes | none | none |
| SaaS | `saas_digital` | 8 | yes | expected SaaS keys | n/a |

Artifact: `/opt/cursor/artifacts/assumption-archetype-regression.json`

## Verdict

**PASS** — empty `ASSUMPTIONS_REVIEW` fixed at generation/transition; Approve disable reason was empty array; no invented status enum; fresh + stuck browser paths reach Financial; regressions clean.
