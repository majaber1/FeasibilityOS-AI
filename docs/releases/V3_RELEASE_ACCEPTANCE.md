# V3 Release Acceptance — Saudi Business

**Release candidate:** `v3.0.0`  
**Branch:** `release/v3.0.0`  
**Baseline SHA (origin/main):** `fa9ecbc0d7a7f1c5fa6ac610e8d775e83b22c6e4`  
**V3 candidate tip:** `f4b655b94149455fdc04010bfb1b98d79b95fe2a`  
**Date (UTC):** 2026-09-12  
**PR #33 merge ancestor:** `1f1a3057b18ec4a4e972d0cb7178688dfef1b3ea`

## Goal

Clean, testable, financially trustworthy production release. No new product features. Engines frozen: Archetype, Knowledge, Discovery, Risk, Decision.

## Baseline confirmation

| Check | Result |
|-------|--------|
| Started from latest `origin/main` | PASS — `fa9ecbc0d7a7f1c5fa6ac610e8d775e83b22c6e4` |
| PR #33 Owner Testability present | PASS — ancestor `1f1a3057b18ec4a4e972d0cb7178688dfef1b3ea` |
| Production Web SHA (pre-release) | `fa9ecbc0d7a7f1c5fa6ac610e8d775e83b22c6e4` |
| Production Backend SHA (pre-release) | `fa9ecbc0d7a7f1c5fa6ac610e8d775e83b22c6e4` |
| Accidental other-project mix | PASS — tip commit restores pre-mix tree; no foreign app code in V3 diff |
| Destructive git reset/clean | Not used |

## Financial Trust recovery (from PR #32, selective port)

**Source:** `cursor/financial-trust-hardening-1831` @ `12a2d0041af4fd4ec726d1f83265dcf9214f56e7`  
**Method:** Manual port of calculation/trust surfaces only. Did **not** merge old PR. Did **not** overwrite Owner Testability journey/nav (StudyJourneyPanels, V2 study counts, archetype labels, continue CTA).

### Ported

- `ai_engine/tools/financial_trust.py` (new)
- Services revenue: `billing_rate × utilization × resources × hours × 12`
- Services OPEX: never silent zero — 55% cost ratio default with labeled warning
- Missing OPEX with revenue: 45% default with labeled warning
- IRR search expansion + user-facing unavailable copy (no raw `null` / `UNKNOWN`)
- Soft CAPEX warning for unrealistic data-center inputs (e.g. 20MW + SAR 25M)
- Backend evaluate/feasibility `irr_display` + warnings
- In-study financial UI messaging + `/tools/financial` non-canonical banner retained
- Nav cards point financial analysis at feasibility study path

### Intentionally not taken from PR #32

- Dashboard V2 study-count regressions
- Workspace journey panel removals
- Raw archetype ID display
- Replacing PR #33 amber study-workflow banner with weaker copy

## Five-scenario mathematical proof

Evidence: `docs/evidence/v3-financial-proof/FIVE_SCENARIO_MATH_PROOF.md`  
Automated hardening tests: `tests/test_financial_trust_hardening.py` — **10/10 PASS**  
Scenario proofs (hand NPV + scale-aware IRR residual + payback): **5/5 PASS**

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
| P0 | Incorrect real-estate NPV (wrong cash-flow construction) | **FIXED** | Engine NPV matches hand Σ CF_t/(1+r)^t for residential profile; see scenario A proof |
| P1 | Raw null IRR/payback in UI | **FIXED** | `irr_user_message` / `irr_display`; UI shows readable unavailable text, not `null`/`UNKNOWN` |
| P1 | Silent AI JSON fallback | **PARTIALLY_FIXED** | Deterministic extract + `extract_notes` + warnings; LLM merge still allowed but defaults are labeled — not claimed as verified market evidence |
| P1 | Unrealistic input accepted without warning | **FIXED** | Soft DC CAPEX warning (20MW @ 25M) surfaces; does not invent benchmark as fact |
| P1 | Services ignore billing rate/utilization/resources | **FIXED** | `services_capacity_revenue` preferred path; unit + scenario C proof |
| P1 | Persistence | **FIXED** | PR #33 V2 list/reopen/continue retained on baseline |
| P1 | Disconnected financial navigation | **FIXED** | In-study financial path + tools banner + nav → feasibility |
| P1 | Evidence/assumption inconsistency | **PARTIALLY_FIXED** | FORECAST labeling + assumption review CTAs; full evidence graph consistency not redesigned (frozen scope) |

**P0:** FIXED  
**P1:** 5 FIXED, 2 PARTIALLY_FIXED, 0 NOT_FIXED

## Owner Gate (19/19)

See table below — filled after candidate UI run of `docs/evidence/OWNER_ACCEPTANCE_TEST.md`.

| Step | Result | Notes |
|------|--------|-------|
| 1–19 | PENDING | Candidate UI run in progress |

## UX release cleanup (blocker-level only)

| Check | Status |
|-------|--------|
| No marketing footer inside authenticated workflow | Inherited from PR #33 AppChrome product footer |
| No raw archetype IDs in primary UI | Inherited `archetypeLabel` |
| Obvious CTA between stages | StudyJourneyPanels continue path retained |
| Logout discoverable | PR #33 navbar |
| Study reopen discoverable | V2 study list + workspace redirect |
| Report reachable | Late-stage journey panels |
| Arabic RTL / English LTR | Existing i18n preserved |

## Regression (frozen engines)

| Area | Status |
|------|--------|
| Classification | Unchanged code path |
| Discovery | Unchanged |
| Knowledge upload/retrieval | Unchanged |
| Similar projects / influence / learning | Unchanged |
| Risk / Decision / Report | Unchanged surfaces; financial payload messaging only |
| Tenant isolation | Unchanged auth scoping |
| No API/provider secrets leaked | No secrets added in V3 diff |

## Known limitations

1. AI Estimate step can hang — manual assumption entry remains valid owner path.
2. Standalone `/tools/financial` remains as a quick calculator only (explicitly non-canonical).
3. Silent LLM numeric invention is mitigated by deterministic extract + labeled defaults, not eliminated.
4. Financial Trust PR #32 must **not** be merged as-is (conflicts / would regress Owner Testability).

## Production readiness verdict

**NOT READY for release tag** until:

1. Owner Gate 19/19 PASS on V3 candidate  
2. PR approved  
3. Merge to main + Web/Backend production deploy  
4. Production SHAs match merge commit  
5. Owner Gate 19/19 PASS on production  
6. Five financial smoke scenarios PASS on production  

Only then create tag `v3.0.0` — **Saudi Business V3 — Trusted Study Release**.
