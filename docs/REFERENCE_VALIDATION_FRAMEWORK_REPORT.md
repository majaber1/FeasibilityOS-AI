# Saudi Business Reference Validation Framework

## Scope and evidence rule

This framework validates the existing lifecycle without changing its architecture, service boundaries, API design, or database design. A lifecycle stage is classified as `VERIFIED_LIVE_E2E` only when it was exercised through Chromium and rendered to the user. Generated reference values are `USER_ASSUMPTION` test inputs, never market facts.

## Current lifecycle coverage

| Stage | Current implementation | Verification |
|---|---|---|
| Register | Account registration and automatic authenticated session | VERIFIED_LIVE_E2E |
| Login | Explicit logout and login with the registered account | VERIFIED_LIVE_E2E |
| Create Project | Persistent project workspace | VERIFIED_LIVE_E2E |
| Create Study | Study linked to the new project | VERIFIED_LIVE_E2E |
| Edit Project | Project name and investment edit | VERIFIED_LIVE_E2E |
| Edit Assumptions | Versioned CAPEX and revenue assumptions with `USER` origin | VERIFIED_LIVE_E2E |
| Calculate | Deterministic calculation from saved assumptions | VERIFIED_LIVE_E2E |
| Validation | Hypotheses and user-recorded, non-simulated evidence | VERIFIED_LIVE_E2E |
| Decision | GO decision after evidence gate | VERIFIED_LIVE_E2E |
| Launch | Launch workspace and persisted task | VERIFIED_LIVE_E2E |
| Growth | Growth workspace renders `INSUFFICIENT_DATA` rather than coercing missing actuals to zero | VERIFIED_LIVE_E2E |

## Reference dataset

The governed fixture is `tests/fixtures/reference-projects.json`. It contains exactly ten requested profiles: Scrap AI Marketplace, SaaS Platform, Restaurant, Manufacturing, Logistics, Healthcare Clinic, E-commerce, Recycling Plant, Agriculture Technology, and B2B Services.

Every persisted test project is prefixed `REFERENCE_TEST_DATA —`. The fixture-level disclaimer states that all numbers and descriptions are generated `USER_ASSUMPTION` inputs and are not verified external facts.

## Compliance findings

### Missing or partial steps

- No requested lifecycle stage is missing from the persistent Project/Study path exercised by the browser test.
- Growth is verified as a visible state (`INSUFFICIENT_DATA`) and by integration-level HOLD-decision persistence; it is not evidence of operating actuals or production growth readiness.
- The ten-project matrix is integration verified. Only one representative project is browser-certified end to end; ten separate browser journeys are not claimed.
- Production deployment, live external market sources, Arabic report quality, operational readiness, security certification, and recovery are outside this local reference run and remain unverified.

### Persistence

- Project edits, business profile, assumptions, calculation result, validation decision, launch task, and growth state persisted after refresh.
- The same artifacts remained visible after logout/login and project/study reopening.
- A dedicated integration regression verifies that a second project's new study has a distinct identity and an empty assumption set, preventing previous-project data leakage.

### Duplicate records

- `POST /feasibility/` currently implements one-study-per-project reuse. Integration tests verify repeated creation requests for one project return the same study and the project list contains one study.
- This prevents accidental duplicates, but it also means the product does not currently support multiple independent studies per project. That is an existing lifecycle constraint, not redesigned here.

### Verified issues fixed

1. Playwright hard-coded occupied application ports. The harness now uses isolated configurable ports (3100/8100 by default).
2. The `/projects` page read browser session state during its first render, producing React hydration error #418 after relogin. Session discovery now occurs after client mount, yielding deterministic server/client HTML.
3. The Playwright journey lacked explicit relogin persistence and durable screenshots. Both are now part of the acceptance test.

No database, API, service, or architecture changes were introduced.

## Architecture risks

- One-study-per-project semantics constrain true study versioning and may confuse users if labelled as “new study.”
- The legacy standalone feasibility wizard still coexists with the persistent workspace and remains a product-flow drift risk.
- Browser reference evidence covers one representative lifecycle, while the ten-profile breadth is integration-level.
- External evidence freshness and generated reference assumptions must remain visibly distinct.
- Production, operations, security, Arabic report rendering, and recovery evidence remain outside this framework.

## Final report

### Implemented

- Exact ten-project `REFERENCE_TEST_DATA` fixture with explicit assumption disclaimer.
- Automated Playwright lifecycle including register, login, project/study creation, editing, assumption persistence, calculation, validation, decision, launch, growth, refresh, logout/login, and reopen.
- Configurable isolated E2E ports and persistent screenshot evidence.
- Machine-readable `project-governance.json`.
- Project/study isolation regression and hydration fix.

### Verified

- One representative full lifecycle is user-visible in Chromium with zero unexpected console, page, authorization, not-found, or server errors.
- Ten reference profiles complete the backend lifecycle integration path.
- Duplicate-study guard, cross-project study isolation, evidence-gated GO, persistence, and UNKNOWN/INSUFFICIENT_DATA semantics.
- Frontend typecheck, lint, and production build.

### Blocked

- Production readiness and production E2E certification are not established by local evidence.
- External-source facts, Arabic reports, operational recovery, and security readiness were not part of this run.

### Evidence

- `apps/web/e2e/full-lifecycle.spec.ts`
- `tests/test_wave65_lifecycle.py`
- `tests/fixtures/reference-projects.json`
- `evidence/reference-validation/01-lifecycle-before-relogin.png`
- `evidence/reference-validation/02-lifecycle-after-relogin.png`
- `project-governance.json`

### Remaining risks

- Multiple-study/version-history semantics are not available under the current one-study-per-project behavior.
- The legacy wizard remains alongside the governed persistent workspace.
- Local SQLite/Chromium evidence does not substitute for production database, deployment, or external-integration evidence.
