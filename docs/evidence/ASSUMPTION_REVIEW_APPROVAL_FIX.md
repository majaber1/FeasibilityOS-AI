# Assumption Review Approval Fix

**Date:** 2026-09-11  
**Branch:** `cursor/assumption-review-approval-fix-1831`  
**PR:** https://github.com/majaber1/saudi-business/pull/24  
**Status:** PASS (API + browser E2E)

## Problem

In Study Workspace → Assumptions Review, **Approve Assumptions / Approve All Assumptions** stayed disabled and could not be clicked, blocking progress into financial analysis.

## Investigation (no assumed cause)

### 1) Frontend disable conditions

`AssumptionReviewPanel` and the workspace page gate Approve All on:

| Condition | Disables? | Notes |
|-----------|-----------|-------|
| `loading` / save in progress | Yes | Correct |
| `assumptions.length === 0` | Yes | Correct — but this was the observed UI state |
| API/study `error` **with** rows present | No | Must not block Approve All |
| Individual cards still `PENDING_REVIEW` | No | Global approve must remain available |

**Observed bug:** phase was `ASSUMPTIONS_REVIEW` while `assumptions` was `[]`, so the CTA rendered disabled.

### 2) API fields

`GET /api/v2/studies/{id}` (and approve/action payloads) return assumption objects with:

- `id` (e.g. `asm_arr`)
- `status` (`PENDING_REVIEW` \| `APPROVED` \| `EDITED` \| `REJECTED`)
- `source` (`AI_ESTIMATED` \| `RULE_BASED` \| `USER_PROVIDED`)
- `confidence`
- `reviewed` (bool)
- `value` / `low` / `base` / `high`

Per-card: `POST .../assumptions/action` with `approve` \| `reject` \| `regenerate`.  
Global: `POST .../approve/assumptions`.

### 3) Persistence / lifecycle

| Event | Expected |
|-------|----------|
| AI / rule fill | `source=AI_ESTIMATED` or `RULE_BASED`, `status=PENDING_REVIEW`, `reviewed=false` |
| User structured answer seed | `source=USER_PROVIDED`, `status=APPROVED`, `reviewed=true` |
| Approve (card or all) | `status=APPROVED`, `reviewed=true` |
| Edit | `status=EDITED`, `source=USER_PROVIDED`, `reviewed=true` |
| Reject | `status=REJECTED`, `reviewed=true` |

Approve-all advances phase to analysis (`READY_FOR_ANALYSIS` → financial → `ANALYZED`).

### 4) Root cause

1. **Empty assumptions in review phase:** `get_llm("assumptions")` (or equivalent client init) could fail **outside** the try/except that handled invoke/parse errors. Evidence approve still advanced phase to `ASSUMPTIONS_REVIEW`, leaving zero rows → Approve disabled.
2. **Empty / `TBD` values** on rule fallback prevented deterministic financial extract after approve (`Could not extract financial data from assumptions`).
3. UX lacked reliable empty-state recovery and per-card Approve / Edit / Regenerate.

## Fix summary

| Area | Change |
|------|--------|
| `ai_engine/agents/assumption.py` | LLM init inside try/except; numeric defaults (never empty/`TBD`); lifecycle fields on every row |
| `ai_engine/models/study_state.py` | `id`, `status`, `reviewed` on `Assumption` |
| `backend/app/api/v2/study_engine.py` | Rebuild assumptions if empty after evidence approve / regenerate; approve-all marks non-rejected rows approved; `POST /assumptions/action` |
| `AssumptionReviewPanel.tsx` | Empty state + Regenerate; per-card Approve/Edit/Regenerate; Approve All only disabled for loading / no rows / error-with-no-data |
| Workspace page | Show panel whenever phase is `ASSUMPTIONS_REVIEW` (even if empty); wire card actions |

## Tests

### A) Unit / agent smoke

- LLM unavailable → rule fallback rows with `RULE_BASED`, `PENDING_REVIEW`, non-empty numeric values.
- Deterministic financial extract succeeds on those rows.

### B) API SaaS journey

User `saas_ar_1789093373@example.com`, project `305`, study `study_bb4593447e39`:

1. Create SaaS study → archetype → structured answers → evidence approve  
2. Assumptions appear (count 8)  
3. Card approve + **Approve All** → phase `ANALYZED`  
4. `financial_results` present (`npv`, `irr`, `payback_months`, `capex`, scenarios)

Artifact: `/opt/cursor/artifacts/assumption-api-e2e.json`

### C) Browser E2E

Study: `http://127.0.0.1:3000/projects/307/studies/study_c9cbb93f20db/workspace`

| Check | Result |
|-------|--------|
| Assumption cards visible (8) | PASS |
| Per-card Approve / Edit / Regenerate | PASS |
| Approve All **enabled** | PASS |
| Approve All advances phase → Analyzed | PASS |
| Financial panel (NPV) without extract error | PASS |

Screenshots:

- <img src="/opt/cursor/artifacts/assumption-review-enabled-approve.webp" alt="Approve All enabled with per-card actions" />
- <img src="/opt/cursor/artifacts/assumption-review-after-approve.webp" alt="After approve: Analyzed with NPV" />

JSON results: `/opt/cursor/artifacts/assumption-review-approve-all-e2e-test-results.json`

## Limitations / follow-ups

- When discovery answers reuse assumption keys, rows seed as `USER_PROVIDED`/`APPROVED` (by design). Pure `AI_ESTIMATED`/`PENDING_REVIEW` is covered by LLM-down agent smoke and regenerate without overlapping answers.
- IRR / payback may still be `null` for some CAPEX=0 SaaS extracts; NPV still computed. Separate from Approve enablement.
- Environment LLM 429 rate limits force rule/keyword fallbacks; fallback path is now safe for approve → financial.

## Verdict

**PASS** — Approve All is clickable whenever assumptions exist; empty generation recovers via regenerate / post-evidence rebuild; approve advances into financial analysis.
