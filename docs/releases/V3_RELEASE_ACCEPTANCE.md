# V3 Release Acceptance — Saudi Business

**Release candidate:** v3.0.0
**Branch:** release/v3.0.0
**Baseline SHA (origin/main):** `fa9ecbc0d7a7f1c5fa6ac610e8d775e83b22c6e4`
**V3 candidate tip:** `6e19a5415163c082b8fc82b6d818d94e4a363824`
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

## Financial Trust re-validation (null-display fix)

**Result: PASS (5/5)** on tip `6e19a5415163c082b8fc82b6d818d94e4a363824` (null-display pass)

Evidence:
- docs/evidence/v3-financial-proof/FIVE_SCENARIO_FINANCIAL_TRUST.md
- docs/evidence/v3-financial-proof/FIVE_SCENARIO_FINANCIAL_TRUST.json

Verified for Residential, Data Center, Cybersecurity Services, SaaS, Uber Mobility:
- no raw `Payback: null` / `IRR: null` in user-facing display or chat summary
- correct NPV/IRR/payback calculations vs hand check
- Data Center soft CAPEX warning visible
- display fields survive persistence round-trip

Owner Gate step 10 `rawBad=false` after product fix (not by weakening the gate assertion).

## Financial Trust final gate (horizon + five scenarios)

**Result: PASS (5/5)** on tip `6e19a5415163c082b8fc82b6d818d94e4a363824`

Additional fix: `run_financial_analysis` no longer truncates revenues/costs to 3 years (incorrect NPV on 4-year residential/DC studies).

Evidence:
- `docs/evidence/V3_FINANCIAL_TRUST_FINAL_VALIDATION.md`
- `docs/evidence/v3-financial-trust-final/`

Regression: `tests/test_financial_trust_hardening.py` — **16 passed**.

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
| P1 | Raw null IRR/payback in UI | FIXED (structured display + reason + missing condition; revalidated) |
| P1 | Silent AI JSON fallback | PARTIALLY_FIXED |
| P1 | Unrealistic input without warning | FIXED |
| P1 | Services ignore billing/utilization/resources | FIXED |
| P1 | Persistence | FIXED (Owner Gate 14/18/19 PASS) |
| P1 | Disconnected financial navigation | FIXED |
| P1 | Evidence/assumption inconsistency | PARTIALLY_FIXED |

## Owner Gate (19/19)

**Result: 19/19 PASS** on local V3 candidate (`6e19a5415163c082b8fc82b6d818d94e4a363824`; still valid on tip `6e19a54` financial surfaces)

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
| Financial trust hardening unit tests | 16 passed |
| Frozen engines | Unchanged except financial trust surfaces |
| Foreign-project contamination | None in release diff |

## Production / preview deploy status (follow-up)

| Surface | SHA | State |
|---------|-----|-------|
| Production Web `https://saudi-business-web.vercel.app` | `fa9ecbc0d7a7f1c5fa6ac610e8d775e83b22c6e4` (main) | READY |
| Production API `https://feasibilityos-ai.vercel.app` | `fa9ecbc0d7a7f1c5fa6ac610e8d775e83b22c6e4` (main) | READY |
| Preview Web (tip `6e19a54`) | `6e19a54…` | READY |
| Preview API (tip `6e19a54` + all recent non-prod) | n/a | **ERROR — Resource provisioning failed** |

Backend preview failure reproduces on Git and CLI deploys for `feasibilityos-ai` (not unique to V3 code). Production builds for the same project still succeed. This blocks pre-merge preview Owner Gate / FT smoke against a live V3 API URL until Vercel/Neon preview provisioning is fixed or production receives the merge deploy.

Evidence: `docs/evidence/V3_PREVIEW_API_PROVISIONING_BLOCKER.md`

## Known limitations

1. Production still on baseline `fa9ecbc0d7a7f1c5fa6ac610e8d775e83b22c6e4` — V3 tip not deployed; production Owner Gate retest required after merge/deploy.
2. `feasibilityos-ai` preview deployments currently fail with `Resource provisioning failed` (platform), so preview API smoke is blocked.
3. AI Estimate can hang — manual discovery answers remain valid.
4. /tools/financial remains a non-canonical calculator only.
5. Silent LLM numeric invention mitigated, not eliminated.
6. PR #32 must not be merged as-is.

## Production readiness verdict

**V3 STATUS: READY (candidate)** — all candidate gates PASS.

**Tag readiness: NOT READY** until: PR merge → Web+Backend production deploy → production SHAs match tip → Owner Gate 19/19 on production → five financial smokes on production.
