# Saudi Business — Master Architecture

Locked: 2026-09-04. This document is a permanent reference. Every future
feature must be checked against it before implementation. It does not
replace `docs/architecture/CURRENT_STATE_AUDIT.md` (a point-in-time
implementation-state record) or `docs/product/SAUDI_BUSINESS_PRODUCT_BLUEPRINT.md`
(the four-entry-point product framing) -- this document is the structural
contract those build on.

Do not modify this document to fit a new feature. If a feature doesn't fit,
write an ADR under `docs/architecture/adr/` instead (see
`docs/architecture/adr/README.md`). Do not implement an architecture change
described in an ADR unless it has been explicitly approved.

## Product definition

Saudi Business is a **Business Decision, Funding & Growth OS**. Permanent
lifecycle a business moves through, each stage persisted, none disposable:

```
IDEA → VALIDATE → STUDY → DECIDE → FUND → LICENSE → LAUNCH →
MEASURE ACTUALS → FORECAST vs ACTUAL → REFORECAST → BUSINESS HEALTH →
SCALE / FIX / PIVOT / STOP
```

## Fixed product waves

Every feature maps to exactly one primary wave. A feature that doesn't fit
any wave is out of scope until an ADR extends this list.

- **Wave 1 — Professional Feasibility**: Idea, Business Profile, Saudi
  Market Evidence, Assumptions, Financial Model, Scenarios, Decision,
  Professional Arabic Study.
- **Wave 2 — Funding Intelligence**: Company Financial Profile, Financial
  Health, Funding Gap, Borrowing Capacity, Collateral, Funding Readiness,
  Funding Programs, Funding Matching, Financing Structure.
- **Wave 3 — Opportunities & Franchise**: Real Source Ingestion,
  Opportunity Marketplace, Franchise Marketplace, Saudi Fit Analysis,
  Comparison, Save, Start Study.
- **Wave 4 — Validation OS**: Validation Plan, Experiments, KPIs, Targets,
  Actual Results, Evidence.
- **Wave 5 — Launch & Actuals**: Actual Metrics, Forecast vs Actual,
  Variance, Reforecast.
- **Wave 6 — Growth OS**: Business Health, What-if, Risk Detection, Monthly
  Review, Recommended Action, Scale / Fix / Pivot / Stop.

## Fixed logical architecture

**Experience layer**: Idea, Study, Funding, Opportunities, Franchises,
Launch, Growth.

**Persistent workspace**: Project, Study, Company, Opportunity, Franchise,
Documents, Reports, Versions, Decisions.

**Intelligence engines**: Research/Evidence, Validation, Feasibility,
Financial, Scenario, Decision, Financial Health, Funding Gap, Borrowing
Capacity, Collateral, Funding Matching, Franchise Fit, Opportunity Fit,
Licensing, Forecast, Reforecast, Business Health.

**AI layer**. AI is a Research Assistant, Extraction Assistant, Analyst,
Advisor, Explainer, Copilot. AI is **not** a Database, Financial Calculator,
Lender, Regulator, Official Source, or Eligibility Authority. Every
deterministic engine above stays deterministic code; AI may explain its
output, never replace or override it.

**Data & source layer**: Saudi Government Sources, Market Sources, Funding
Institutions, Funding Rules, Franchise Sources, Opportunity Sources, User
Documents, Accounting Data, Bank Data, Actual Business Metrics.

**Trust & governance**: Provenance, Source Authority, Freshness, Effective
Date, Rule Version, Calculation Version, Assumption Origin, Audit Trail,
Confidence, Data Quality, Version History.

## What exists today (as of commit 7c4de37)

Wave 1 backend: Quick Idea Check, Business Profile, Evidence + Source
Authority Registry, Assumptions (versioned), deterministic Feasibility
engine (assumption-driven), Scenario engine (explicit overrides), Decision
engine. Wave 1 frontend: Overview, Business Profile, Market Evidence,
Assumptions tabs are real; Scenarios/Decision have no UI yet.

Wave 2 backend: Company Financial Profile (period statements), Document
intake foundation, Financial Health engine, Funding Gap, Borrowing
Capacity. **None of Wave 2 has a frontend workspace yet** -- see
`docs/architecture/FEATURE_DELIVERY_CONTRACT.md` for why this makes these
features `BACKEND_ONLY`, not complete.

Waves 3-6: not started.

## Architecture change policy

Every feature must first read this file and
`docs/architecture/FEATURE_DELIVERY_CONTRACT.md`. If the feature fits the
waves/layers above, implement it directly. If it doesn't, write an ADR
(`docs/architecture/adr/README.md` has the template and process) instead of
silently redesigning. Do not implement an architectural change until it has
been explicitly approved by the user.
