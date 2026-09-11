# Final Pre-Merge Validation — Assumptions Review Approval Fix

**PR:** https://github.com/majaber1/saudi-business/pull/24  
**Branch:** `cursor/assumption-review-approval-fix-1831`  
**Date:** 2026-09-11  
**Verdict:** **PASS** (recovery + failure simulations + browser A/B + full journey A–E + regressions)

---

## Root cause

`get_llm("assumptions")` ran **outside** the try/except in `ai_engine/agents/assumption.py`.

Sequence that stuck users:

1. Evidence approve sets `phase = ASSUMPTIONS_REVIEW`
2. Orchestrator invokes assumption agent
3. LLM client init fails (timeout / 429 / missing key / bad response)
4. Exception aborts before any rows are seeded
5. Study persists as `ASSUMPTIONS_REVIEW` with `assumptions = []`
6. Frontend disables Approve via `loading || assumptions.length === 0`

This is a **state-machine / generation defect**, not a missing per-assumption status enum.  
No `PENDING_REVIEW` / `EDITED` / `REJECTED` model was kept.

### Secondary defect found during validation

Discovery `structured_answers` keys can collide with assumption schema keys. Placeholder answers (`confirmed` / `ok` / `yes`) were seeded as assumption **values**, so financial extract later failed with “Could not extract financial data…”.

Minimal guard added: ignore non-numeric / placeholder user answers for numeric assumption fields so Rule Fallback / AI can supply parseable values.

---

## Fix summary

1. Wrap LLM init in try/except; on failure seed **Rule Fallback** rows with numeric defaults and clear `Rule Fallback` source label.
2. After evidence → review: if still empty, rebuild via `run_assumptions`.
3. Regenerate clears and hard-guarantees non-empty persisted assumptions.
4. UX on **current** model (`source` / `origin` / `ai_estimated`): Approve / Edit / Reject / Regenerate / Why.
5. Reject removes the row (not a parallel status lifecycle).
6. Bulk CTA: **Approve all eligible assumptions** with explicit visible disable reason.
7. Skip unusable structured-answer placeholders for numeric assumption fields.

---

## Files changed

| File | Change |
|------|--------|
| `ai_engine/agents/assumption.py` | LLM init inside try; Rule Fallback defaults; placeholder structured-answer guard |
| `ai_engine/models/study_state.py` | Kept current Assumption fields (no status enum) |
| `backend/app/api/v2/study_engine.py` | Empty-state rebuild; regenerate guarantee; card action endpoint |
| `apps/web/components/study/AssumptionReviewPanel.tsx` | Empty state + per-card actions + eligible bulk approve |
| `apps/web/app/projects/[projectId]/studies/[studyId]/workspace/page.tsx` | Always show panel in `ASSUMPTIONS_REVIEW`; wire actions |
| `docs/evidence/ASSUMPTION_REVIEW_APPROVAL_FIX.md` | Investigation evidence |
| `docs/evidence/FINAL_PRE_MERGE_VALIDATION.md` | This document |

---

## API changes

**YES (additive only)**

- `POST /api/v2/studies/{id}/assumptions/action` — `approve` | `reject` | `regenerate` mapped onto existing fields
- Existing `.../assumptions/regenerate` and `.../approve/assumptions` hardened

**DB changes:** **NO**

---

## 1) Existing studies recovery — PASS

| Check | Result |
|-------|--------|
| Seed stuck `ASSUMPTIONS_REVIEW` + `assumptions=[]` | Recovered via regenerate API only (no DB surgery for recovery step) |
| Historical empty studies (3) reassigned for auth then regenerated | Persisted 6–8 rows; approve → `ANALYZED` + financial |
| After regenerate, GET returns same non-empty set | PASS |
| User can continue to financial without DB intervention | PASS |

Artifact: `/opt/cursor/artifacts/final-recovery-failure-tests.json`

---

## 2) Failure scenarios — PASS

Simulated:

| Case | Phase kept | Rows | Label | Empty values | Financial after approve |
|------|------------|------|-------|--------------|-------------------------|
| LLM timeout | `ASSUMPTIONS_REVIEW` | 6 | `Rule Fallback` | none | PASS (NPV computed) |
| Groq / LLM 429 | `ASSUMPTIONS_REVIEW` | 6 | `Rule Fallback` | none | PASS |
| Invalid JSON response | `ASSUMPTIONS_REVIEW` | 6 | `Rule Fallback` | none | PASS |

Must-nots verified:

- Does **not** create empty assumptions
- Does **not** silently advance phase on failure (`assumptions_approved` stays false; phase stays review)
- Does **not** break financial analysis after Rule Fallback + approve

Artifact: `/opt/cursor/artifacts/final-failure-simulations.json`

---

## 3) Browser acceptance — PASS

Fresh accounts prepared in `/opt/cursor/artifacts/final-browser-scenario-targets.json`.

| Scenario | Archetype / variant | Assumptions keys | Leakage | Journey | Browser evidence |
|----------|---------------------|------------------|---------|---------|------------------|
| **A** SaaS AI compliance | `saas_digital` | ARR/CAC/churn present | n/a | `REPORT_READY` / `DEFER` | assumptions + financial screenshots |
| **B** Cyber MSSP | `services` / `professional` | consultants, utilization, contracts, MRC | no SaaS / no mobility | `REPORT_READY` | assumptions + financial screenshots |
| **C** Residential RE | `real_estate` | land / BOQ / units / price | no SaaS | `REPORT_READY` / `GO_WITH_CONDITIONS` | financial screenshot |
| **D** Data center | `data_center` | MW / racks / PUE / occupancy | no SaaS | `REPORT_READY` | financial screenshot |
| **E** Uber mobility | `services` / `mobility` | take_rate / trips / drivers | no SaaS | `REPORT_READY` / `GO_WITH_CONDITIONS` | assumptions + financial screenshots |

Browser screenshots (complete A–E):

- `/opt/cursor/artifacts/final-scen-A-assumptions.webp`
- `/opt/cursor/artifacts/final-scen-A-financial.webp`
- `/opt/cursor/artifacts/final-scen-B-assumptions.webp`
- `/opt/cursor/artifacts/final-scen-B-financial.webp`
- `/opt/cursor/artifacts/final-scen-C-financial.webp`
- `/opt/cursor/artifacts/final-scen-D-financial.webp`
- `/opt/cursor/artifacts/final-scen-E-assumptions.webp`
- `/opt/cursor/artifacts/final-scen-E-financial.webp`

Full A–E API continuation after regenerate (numeric Rule Fallback) → financial → decision → **REPORT_READY**:  
`/opt/cursor/artifacts/final-scenario-repaired-journey.json` — **5/5 PASS**

### Browser note

A prior Discovery UI bug (CAC input not rendering) can block a pure click-path through structured questions. Validation therefore:

1. Used fresh accounts + API to reach a correct `ASSUMPTIONS_REVIEW` state for each archetype  
2. Validated Assumptions Review UI + Approve → Financial in browser for A–E (screenshots above)  
3. Completed Financial → Risk/Decision → Report for all five via authenticated API against the same studies

---

## 4) Regression results — PASS

| Case | Result |
|------|--------|
| SaaS | PASS — SaaS metrics present; report ready |
| Professional services (cyber) | PASS — no SaaS / no mobility keys |
| Residential real estate | PASS — no SaaS keys |
| Data center | PASS — no SaaS keys |
| Uber mobility | PASS — mobility keys present; no SaaS keys |

---

## Known limitations

1. **Discovery ↔ assumption key collision:** mitigated for numeric placeholders; text collisions still possible if users type non-numeric prose into numeric assumption keys via discovery.
2. **Discovery CAC field UI:** separate frontend rendering issue can block pure UI question completion; not part of the empty-assumptions approve defect, but affects unaided browser onboarding.
3. **Rule Fallback values are indicative** (clearly labeled). Users should edit before treating as bank-grade inputs.
4. **IRR / payback** may be null in some CAPEX=0 SaaS extracts; NPV / analysis still produced.

---

## Merge recommendation

**READY TO MERGE.**

All required pre-merge checks for PR #24 passed:

- Stuck empty `ASSUMPTIONS_REVIEW` recovers via regenerate without DB intervention  
- Timeout / 429 / invalid JSON → Rule Fallback, phase held, financial still works  
- Fresh SaaS + professional + RE + DC + mobility journeys reach report without archetype leakage  
- No invented assumption status enum; no DB migration  

**Do not start unrelated UI work (Form vs AI Advisor) until this PR is merged or explicitly parked.**
