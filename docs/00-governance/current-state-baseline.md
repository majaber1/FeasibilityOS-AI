# Saudi Business — Current State Baseline

## Document Control

- **Document ID:** SB-GOV-BASELINE-001
- **Title:** Current State Baseline
- **Version:** GOV-0.1
- **Status:** DRAFT
- **Owner:** Project Governance Authority
- **Created Date:** 2026-09-06
- **Last Updated:** 2026-09-06
- **Related Requirements:** UNKNOWN — requirements reconstruction pending
- **Related ADRs:** Existing ADR inventory pending audit
- **Supersedes:** None
- **Change Summary:** Initial protected baseline snapshot for governance adoption

---

## 1. Project Identity

- **Project Name:** Saudi Business
- **Project Type:** EXISTING PROJECT
- **Repository:** `majaber1/saudi-business`
- **Repository URL:** GitHub repository `majaber1/saudi-business`
- **Primary working branch:** `feat/ai-decision-workspace-v1`
- **Governance Standard:** `docs/00-governance/SAUDI_BUSINESS_MASTER_GOVERNANCE_STANDARD.md`

---

## 2. Source-Control Baseline

Baseline immediately before governance-document adoption:

- **Branch:** `feat/ai-decision-workspace-v1`
- **Application HEAD:** `0566ef5` — `fix(e2e): handle missing financial data semantics`
- **Previous application baseline:** `8490d29` — `fix(wave6): restore current validation gate and prevent stale funding context`
- **Working tree at last user-verified application commit:** clean after commit/push was completed
- **Governance document adoption commit:** recorded separately in Git after application baseline; governance-only change
- **Tags:** UNKNOWN — complete tag inventory pending audit
- **Latest release/tag:** UNKNOWN — pending audit

This document must not be interpreted as evidence that production is deployed or ready.

---

## 3. Known Framework / Runtime State

Evidence currently available:

- **Frontend:** Next.js 16.3.0 (observed local dev runtime)
- **Frontend build:** 36 routes generated successfully at last user-run build
- **Backend framework:** FastAPI / Uvicorn observed from local runtime
- **Backend test command:** `python -m pytest tests/ -q`
- **Last user-reported full backend result:** 530 passed
- **Database technology:** UNKNOWN in this baseline until repository/database audit completes
- **Current migration head:** UNKNOWN pending explicit migration audit
- **Node runtime:** UNKNOWN pending environment audit
- **Python runtime:** UNKNOWN pending environment audit

---

## 4. Known Local Runtime / Environment

Last observed local development environment:

- **Frontend:** `http://127.0.0.1:3000`
- **Backend:** `http://127.0.0.1:8000`
- **Frontend runtime state:** local Next.js development server observed running
- **Backend runtime state:** local Uvicorn server observed running
- **Production environment:** NOT VERIFIED
- **Preview/staging environment:** UNKNOWN
- **Deployment provider/configuration:** repository audit pending

---

## 5. Product Capability Baseline

The current intended lifecycle is:

IDEA
→ FEASIBILITY
→ FUNDING
→ OPPORTUNITY / FRANCHISE
→ VALIDATION
→ DECISION
→ LAUNCH
→ ACTUALS
→ FORECAST vs ACTUAL
→ REFORECAST
→ BUSINESS HEALTH
→ GROWTH
→ SCALE / FIX / PIVOT / HOLD / STOP

Known implemented capability areas include:

- Feasibility / study creation and financial analysis
- Funding intelligence and deterministic funding matching
- Opportunity / franchise capability
- Validation OS
- Launch and Actuals OS
- Growth OS
- Financial-health handling
- Borrowing-capacity handling
- Financial Analysis UI

**Important:** these capabilities have different levels of verification. The baseline audit must classify every feature using the approved verification statuses. No blanket `PRODUCTION_READY` claim is permitted.

---

## 6. Last Known Verification Evidence

User-executed evidence available immediately before governance adoption:

- Focused financial-health / borrowing-capacity tests: **35 passed**
- Full backend regression after latest application fix: **530 passed**
- Frontend typecheck: **PASS**
- Frontend lint: **PASS**
- Frontend build: **PASS**
- Static/dynamic route generation: **36 routes**

Previous Wave 6 safety closure evidence included:

- Growth focused tests: 41 passed
- Validation focused tests: 19 passed
- Launch focused tests: 25 passed
- Full backend at that prior baseline: 528 passed
- Chrome smoke for current-cycle launch gate and scenario-specific funding context: reported PASS

These records are evidence of testing only. They do not by themselves establish production readiness.

---

## 7. Known Product / UX Findings

Observed during manual product use and E2E work:

### Critical workflow gaps requiring formal review

1. Existing project profile is not clearly editable from the normal project workspace.
2. Existing feasibility study is not clearly editable after results are generated.
3. `New Study` behavior can preload previous information, creating ambiguity between create and edit semantics.
4. Feasibility stepper circles are indicators rather than usable navigation; users cannot naturally return from results to prior inputs.
5. Assumptions require a clear persistent edit/recalculate workflow.
6. Study / business-record version history is not clearly exposed or governed.
7. Arabic PDF/report rendering has produced unreadable `nnnn` text.
8. Full lifecycle browser certification previously exposed incomplete Wave 3 journey evidence and persistence gaps.
9. Wave 3 acceptance/catalog data may be empty in local test context.
10. Validation correctly requires real, non-simulated evidence before GO; an approved certification evidence strategy is still required.

Severity is not assigned here; formal classification belongs in `design-review.md`.

---

## 8. Known Data / Evidence Semantics

Current Saudi Business rules to preserve:

- VERIFIED_EXTERNAL_FACT
- USER_INPUT
- USER_ASSUMPTION
- PLATFORM_DERIVED
- ACTUAL
- FORECAST
- UNKNOWN

Mandatory principles:

- UNKNOWN ≠ ZERO
- assumptions are not verified facts
- potential funding is not cash
- guarantees are not cash
- deterministic financial calculations are not delegated to AI
- AI is not the authoritative source of factual business state

---

## 9. Known Architecture Baseline

Existing authoritative architecture document known from project history:

- `docs/architecture/SAUDI_BUSINESS_MASTER_ARCHITECTURE.md`

The baseline audit must inspect it and determine:

- current architecture version
- architecture drift
- implemented vs documented components
- missing ADRs
- required CRs

No architecture rewrite is authorized by this baseline document.

---

## 10. AI / Agent Baseline

- AI architecture present in project: pending audit
- Production AI provider(s): UNKNOWN
- Model(s): UNKNOWN
- Agent inventory: UNKNOWN
- LLM-call limits: UNKNOWN
- Tool-call limits: UNKNOWN
- Per-workflow cost: UNKNOWN
- Grounding/evaluation baseline: UNKNOWN

These must be discovered from actual repository/runtime evidence, not inferred.

---

## 11. Integration Baseline

Known integration categories from the product domain include funding/public-source references and potential external-source use, but the actual integration inventory, adapters, authentication, retries, failure behavior, monitoring, and production verification are **UNKNOWN pending audit**.

---

## 12. Security / Compliance Baseline

- Authentication: implemented, detailed review pending
- Authorization/ownership isolation: implemented in multiple product areas, complete audit pending
- Tenant model: UNKNOWN pending audit
- Security baseline: NOT ASSESSED under the new governance standard
- Threat model: NOT ASSESSED
- Saudi PDPL applicability: assessment required
- SDAIA/NCA applicability: assessment required

No compliance claim is made.

---

## 13. Operations Baseline

- Observability: UNKNOWN
- Monitoring: UNKNOWN
- Alerting: UNKNOWN
- Logging baseline: UNKNOWN
- Backup/restore: UNKNOWN
- RPO/RTO: UNKNOWN
- Disaster recovery: UNKNOWN
- Incident response: UNKNOWN
- Production runbooks: UNKNOWN

---

## 14. Cost Baseline

- Fixed monthly cost: UNKNOWN
- Variable cost: UNKNOWN
- AI cost: UNKNOWN
- Cost per workflow: UNKNOWN
- Cost per report: UNKNOWN
- Cost per customer: UNKNOWN

**Status:** COST REVIEW REQUIRED.

---

## 15. Production Status

**Current evidence-based production readiness:** `NO_GO / NOT YET ASSESSED UNDER GOVERNANCE BASELINE`

Reason:

- formal requirements baseline not yet reconstructed
- architecture baseline not yet reviewed/frozen
- live full-lifecycle E2E not yet certified under the new standard
- security/operations/cost readiness not yet assessed
- known UX lifecycle findings remain open

This is not a statement that the application cannot run; it is a governance/readiness classification.

---

## 16. Next Allowed Activity

**READ-ONLY WORKSPACE AUDIT** only.

Next required artifacts include:

- `workspace-audit.md`
- `design-review.md`
- feature inventory
- requirements reconstruction
- architecture review
- ADR / CR proposals
- roadmap/backlog reconstruction
- testing / security / operations / cost assessment
- governance manifest proposal
- baseline-freeze approval package

No Wave 6.5 remediation and no Wave 7 implementation may start before baseline acceptance.
