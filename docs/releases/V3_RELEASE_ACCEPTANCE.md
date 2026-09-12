# V3 Release Acceptance — Saudi Business

**Release candidate:**   
**Branch:**   
**Baseline SHA (origin/main):**   
**V3 candidate tip:**   
**Date (UTC):** 2026-09-12  
**PR:** https://github.com/majaber1/saudi-business/pull/36  
**PR #33 merge ancestor:** 

## Goal

Clean, testable, financially trustworthy production release. No new product features. Engines frozen: Archetype, Knowledge, Discovery, Risk, Decision.

## Baseline confirmation

| Check | Result |
|-------|--------|
| Started from latest  | PASS —  |
| PR #33 Owner Testability present | PASS — ancestor  |
| Production Web SHA (pre-release) |  |
| Production Backend SHA (pre-release) |  |
| Accidental other-project mix | PASS — no foreign app paths in  |
| Destructive git reset/clean | Not used |

## Financial Trust recovery (from PR #32, selective port)

**Source:**  @   
**Method:** Manual port of calculation/trust surfaces only. Did **not** merge old PR. Did **not** overwrite Owner Testability journey/nav.

### Ported

- 
- Services revenue prefers 
- Services OPEX never silent zero — labeled defaults/warnings
- IRR + payback user-facing unavailable copy (no raw  / )
- Soft CAPEX warning for unrealistic data-center inputs
- Backend evaluate/feasibility display helpers + warnings
- In-study financial UI messaging +  non-canonical banner retained
-  for owner testability of Evidence → Assumptions

### Intentionally not taken from PR #32

- Dashboard V2 study-count regressions
- Workspace journey panel removals
- Raw archetype ID display
- Standalone financial as canonical path

## Five-scenario mathematical proof

Evidence:   
Automated hardening tests:  — **12/12 PASS**  
Scenario proofs: **5/5 PASS**

| Scenario | Result |
|----------|--------|
| A Residential 500 Riyadh | PASS |
| B Data Center 20MW Riyadh (+ 25M unrealistic warning) | PASS |
| C Cyber MSSP services (billing×util×resources; non-zero OPEX) | PASS |
| D SaaS ARR/churn/CAC | PASS |
| E Uber-like mobility | PASS |

## Original audit findings

| ID | Finding | Status | Evidence |
|----|---------|--------|----------|
| P0 | Incorrect real-estate NPV | **FIXED** | Scenario A hand NPV match |
| P1 | Raw null IRR/payback in UI | **FIXED** |  / ; Owner Gate g6-10 shows readable unavailable text |
| P1 | Silent AI JSON fallback | **PARTIALLY_FIXED** | Deterministic extract + labeled defaults |
| P1 | Unrealistic input without warning | **FIXED** | Soft DC CAPEX warning |
| P1 | Services ignore billing/utilization/resources | **FIXED** | capacity revenue path + tests |
| P1 | Persistence | **FIXED** | Owner Gate steps 14, 18, 19 PASS |
| P1 | Disconnected financial navigation | **FIXED** | In-study financial; not  |
| P1 | Evidence/assumption inconsistency | **PARTIALLY_FIXED** | FORECAST labeling; frozen scope |

**P0:** FIXED  
**P1:** 6 FIXED (code+owner), 2 PARTIALLY_FIXED

## Owner Gate (19/19)

**Result: 19/19 PASS** on local V3 candidate ()

Normal UI journey only (register → project → AI study → classification → discovery → evidence approve → assumptions → in-study financial → risks → decision → report → refresh → logout → login → projects → reopen → persistence).

Evidence:  (, ).

| Step | Result |
|------|--------|
| 1–9 Auth / project / study / classification / discovery / assumptions | PASS |
| 10 In-study financial (NPV + readable IRR/payback; not tools calculator) | PASS |
| 11–13 Risks / Decision / Report | PASS |
| 14–19 Refresh / logout / login / projects / reopen / persistence | PASS |

## Regression (frozen engines)

| Area | Status |
|------|--------|
| Financial trust unit + study engine tests | 68 passed |
| Classification / Discovery / Knowledge / Risk / Decision code paths | Unchanged except financial trust surfaces |
| Tenant isolation | Unchanged auth scoping |
| Foreign-project contamination | None in release diff |

## Known limitations

1. Production is still on baseline  — V3 tip not deployed; production Owner Gate retest required after merge/deploy.
2. AI Estimate can hang — manual discovery answers remain a valid owner path.
3. Standalone  remains a non-canonical calculator only.
4. Silent LLM numeric invention mitigated by deterministic extract + labeled defaults, not eliminated.
5. PR #32 must not be merged as-is (conflicts / Owner Testability regressions).

## Production readiness verdict

**V3 STATUS: READY (candidate)** — all candidate gates PASS.

Do **not** tag  until:

1. PR approved and merged to 
2. Web + Backend production deploy
3. Production SHAs match merge commit
4. Owner Gate 19/19 PASS on production
5. Five financial smoke scenarios PASS on production

Only then create tag  — **Saudi Business V3 — Trusted Study Release**.
