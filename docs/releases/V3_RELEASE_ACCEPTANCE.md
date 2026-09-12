# V3 Release Acceptance — Saudi Business

**Release candidate:** v3.0.0
**Branch:** release/v3.0.0
**Baseline SHA (origin/main):** `fa9ecbc0d7a7f1c5fa6ac610e8d775e83b22c6e4`
**V3 candidate tip:** `54f1fa1aef08ce648b618e68630f650c17785a68`
**Date (UTC):** 2026-09-12
**PR:** https://github.com/majaber1/saudi-business/pull/36
**PR #33 merge ancestor:** `1f1a3057b18ec4a4e972d0cb7178688dfef1b3ea`

## Goal

Clean, testable, financially trustworthy production release. No new product features. Engines frozen: Archetype, Knowledge, Discovery, Risk, Decision.

## Baseline confirmation

| Check | Result |
|-------|--------|
| Started from latest origin/main | PASS — `fa9ecbc0d7a7f1c5fa6ac610e8d775e83b22c6e4` |
| PR #33 Owner Testability present | PASS — ancestor `1f1a3057b18ec4a4e972d0cb7178688dfef1b3ea` |
| Production Web SHA (pre-release) | `fa9ecbc0d7a7f1c5fa6ac610e8d775e83b22c6e4` |
| Production Backend SHA (pre-release) | `fa9ecbc0d7a7f1c5fa6ac610e8d775e83b22c6e4` |
| Accidental other-project mix | PASS — no foreign app paths in release diff |
| Destructive git reset/clean | Not used |

## Financial Trust recovery (from PR #32, selective port)

**Source:** cursor/financial-trust-hardening-1831
**Method:** Manual port of calculation/trust surfaces only. Did not merge old PR. Did not overwrite Owner Testability journey/nav.

### Ported

- Financial trust helpers (IRR + payback user messaging, input warnings)
- Services revenue prefers billing_rate x utilization x resources x billable_period
- Services OPEX never silent zero — labeled defaults/warnings
- Soft CAPEX warning for unrealistic data-center inputs
- Backend evaluate/feasibility display helpers + warnings
- In-study financial UI messaging + /tools/financial non-canonical banner retained
- approve-evidence button test id for owner journey

### Intentionally not taken from PR #32

- Dashboard V2 study-count regressions
- Workspace journey panel removals
- Raw archetype ID display
- Standalone financial as canonical path

## Five-scenario mathematical proof

Evidence: docs/evidence/v3-financial-proof/FIVE_SCENARIO_MATH_PROOF.md
Automated hardening tests: tests/test_financial_trust_hardening.py — 12/12 PASS
Scenario proofs: 5/5 PASS

| Scenario | Result |
|----------|--------|
| A Residential 500 Riyadh | PASS |
| B Data Center 20MW Riyadh (+ 25M unrealistic warning) | PASS |
| C Cyber MSSP services (billing x util x resources; non-zero OPEX) | PASS |
| D SaaS ARR/churn/CAC | PASS |
| E Uber-like mobility | PASS |

## Original audit findings

| ID | Finding | Status |
|----|---------|--------|
| P0 | Incorrect real-estate NPV | FIXED |
| P1 | Raw null IRR/payback in UI | FIXED |
| P1 | Silent AI JSON fallback | PARTIALLY_FIXED |
| P1 | Unrealistic input without warning | FIXED |
| P1 | Services ignore billing/utilization/resources | FIXED |
| P1 | Persistence | FIXED (Owner Gate 14/18/19 PASS) |
| P1 | Disconnected financial navigation | FIXED |
| P1 | Evidence/assumption inconsistency | PARTIALLY_FIXED |

## Owner Gate (19/19)

**Result: 19/19 PASS** on local V3 candidate (`12d40971ce1c126ce22607cf8e2ea2d3b718b574`)

Normal UI journey only. Evidence: docs/evidence/v3-owner-gate/

| Step band | Result |
|-----------|--------|
| 1-9 Auth / project / study / classification / discovery / assumptions | PASS |
| 10 In-study financial (NPV + readable IRR/payback; not tools calculator) | PASS |
| 11-13 Risks / Decision / Report | PASS |
| 14-19 Refresh / logout / login / projects / reopen / persistence | PASS |

## Regression

| Area | Status |
|------|--------|
| Financial trust + study engine unit tests | 68 passed |
| Frozen engines | Unchanged except financial trust surfaces |
| Foreign-project contamination | None in release diff |

## Known limitations

1. Production still on baseline `fa9ecbc0d7a7f1c5fa6ac610e8d775e83b22c6e4` — V3 tip not deployed; production Owner Gate retest required after merge/deploy.
2. AI Estimate can hang — manual discovery answers remain valid.
3. /tools/financial remains a non-canonical calculator only.
4. Silent LLM numeric invention mitigated, not eliminated.
5. PR #32 must not be merged as-is.

## Production readiness verdict

**V3 STATUS: READY (candidate)** — all candidate gates PASS.

Do not tag v3.0.0 until: PR merge, Web+Backend production deploy, production SHAs match, Owner Gate 19/19 on production, five financial smokes on production.
