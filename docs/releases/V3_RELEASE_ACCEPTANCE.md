# V3 Release Acceptance — Saudi Business

**Release candidate:** `v3.0.0`  
**Branch:** `release/v3.0.0`  
**Baseline SHA (origin/main):** `fa9ecbc0d7a7f1c5fa6ac610e8d775e83b22c6e4`  
**V3 candidate tip:** `f22f3ccfbda4a8d6e60e1daa6466094654729e3b`
**Date (UTC):** 2026-09-12  
**PR:** https://github.com/majaber1/saudi-business/pull/36  
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
**Method:** Manual port of calculation/trust surfaces only. Did **not** merge old PR. Did **not** overwrite Owner Testability journey/nav (`StudyJourneyPanels`, V2 study counts, `archetypeLabels`, continue CTA).

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
| P1 | Persistence | **FIXED** (code) / **UNVERIFIED** (owner UI) | PR #33 V2 list/reopen/continue retained; Owner Gate did not prove late-stage persistence |
| P1 | Disconnected financial navigation | **FIXED** | In-study financial path + tools banner + nav → feasibility |
| P1 | Evidence/assumption inconsistency | **PARTIALLY_FIXED** | FORECAST labeling + assumption review CTAs; full evidence graph consistency not redesigned (frozen scope) |

**P0:** FIXED  
**P1:** 5 FIXED (code), 2 PARTIALLY_FIXED, 0 NOT_FIXED — Owner Gate still blocks release

## Owner Gate (19/19)

**Result: 8/19 PASS — BLOCKING**

Assistive Playwright initially reported 19/19; screenshot review falsified late-stage claims. Study workspace remained on empty prompt “ابدأ بوصف مشروعك” and never completed classification → financial → report.

| Step | Result | Notes |
|------|--------|-------|
| 1 Open app | PASS | Local candidate loads |
| 2 Register/Login | PASS | Fresh account |
| 3 Dashboard | PASS | `/dashboard` |
| 4 Create project | PASS | Project workspace created |
| 5 Idea visible | PASS | MSSP Arabic idea/name shown |
| 6 Start AI study | PASS | Opens study workspace |
| 7 Classification friendly label | FAIL | Empty start chat; classification not completed |
| 8 Discovery | FAIL | Not reached |
| 9 Assumptions → financial CTA | FAIL | Not reached |
| 10 In-study financial | FAIL | No NPV/IRR rendered; did not land on `/tools/financial` |
| 11 Risks | FAIL | Not reached |
| 12 Decision | FAIL | Not reached |
| 13 Report | FAIL | Not reached |
| 14 Refresh | PASS | Empty workspace survives refresh |
| 15 Logout | PASS | Logout discoverable |
| 16 Re-login | PASS | |
| 17 Projects list | PASS | Same project listed |
| 18 Reopen study | FAIL | Empty workspace; prior progress not evidenced |
| 19 Persistence of analysis/report | FAIL | No analysis/report to persist |

Evidence: `docs/evidence/v3-owner-gate/` (see `OWNER_GATE_HONEST_SCORE.md`, `f-06.png`, `f-10.png`).

Computer-use interactive retest was blocked by environment spend limit. Do not treat URL-only automation as Owner Gate PASS.

## UX release cleanup (blocker-level only)

| Check | Status |
|-------|--------|
| No marketing footer inside authenticated workflow | PASS on observed screens — product footer “مساحة عمل المنتج” |
| No raw archetype IDs in primary UI | PASS on observed screens (classification stage not completed) |
| Obvious CTA between stages | PARTIAL — study starts as empty chat; late-stage CTAs not proven in this run |
| Logout discoverable | PASS |
| Study reopen discoverable | PARTIAL — AI study CTA exists; persistence of prior study not proven |
| Report reachable | UNVERIFIED in this run |
| Arabic RTL / English LTR | PASS on observed Arabic RTL screens |

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
| Financial trust unit tests | 10/10 PASS |

## Known limitations

1. Owner Gate incomplete on V3 candidate (8/19) — empty study chat start did not prove late-stage financial/risk/decision/report persistence.
2. AI Estimate step can hang — manual assumption entry remains valid owner path.
3. Standalone `/tools/financial` remains as a quick calculator only (explicitly non-canonical).
4. Silent LLM numeric invention is mitigated by deterministic extract + labeled defaults, not eliminated.
5. Financial Trust PR #32 must **not** be merged as-is (conflicts / would regress Owner Testability).

## Production readiness verdict

**V3 STATUS: NOT READY**

Do not merge, deploy, or tag until:

1. Owner Gate 19/19 PASS on V3 candidate (true normal UI, including in-study financial + report + reopen persistence)  
2. PR approved  
3. Merge to main + Web/Backend production deploy  
4. Production SHAs match merge commit  
5. Owner Gate 19/19 PASS on production  
6. Five financial smoke scenarios PASS on production  

Only then create tag `v3.0.0` — **Saudi Business V3 — Trusted Study Release**.
