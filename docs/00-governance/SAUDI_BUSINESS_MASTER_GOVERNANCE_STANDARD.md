# Saudi Business — Master Project Governance, Architecture & Delivery Standard

> Project-specific adoption of the universal Master Project Governance, Architecture & Delivery Standard.

## Document Control

- **Document ID:** SB-GOV-MASTER-001
- **Title:** Saudi Business Master Governance, Architecture & Delivery Standard
- **Version:** GOV-0.1
- **Status:** DRAFT
- **Owner:** Project Governance Authority
- **Created Date:** 2026-09-06
- **Last Updated:** 2026-09-06
- **Related Requirements:** UNKNOWN — requirements reconstruction pending
- **Related ADRs:** Existing ADR inventory pending baseline audit
- **Supersedes:** None
- **Change Summary:** Initial project-specific governance adoption for the existing Saudi Business project

---

## 1. Project Classification

**Project:** Saudi Business  
**Type:** EXISTING PROJECT  
**Repository:** `majaber1/saudi-business`  
**Governance Mode:** READ-ONLY BASELINE DISCOVERY before any further product implementation.

No Wave 7, Knowledge Workspace, architecture remediation, schema change, API change, AI change, or production deployment may begin until the current baseline is audited and approved.

---

## 2. Core Governance Principle

Saudi Business MUST follow this chain:

Business Need
→ Product Definition
→ Requirements
→ Architecture
→ HLD
→ ADRs
→ LLD
→ Data Design
→ Integration Design
→ AI Design
→ Security Design
→ Cost Model
→ Roadmap
→ Backlog
→ Implementation
→ Testing
→ Live E2E Verification
→ Operational Readiness
→ Release
→ Production
→ Monitoring
→ Controlled Change

Code implements approved architecture. Code does not invent architecture.

---

## 3. Existing Project Safety Mode

The next governed activity is a **READ-ONLY BASELINE DISCOVERY**.

During baseline discovery, do NOT change:

- product source code
- frontend/backend behavior
- routes or APIs
- database/schema/migrations
- authentication/authorization/tenancy
- AI prompts/providers/models/agents
- integrations
- deployment/infrastructure
- tests merely to match implementation
- historical documentation merely to legitimize accidental code

Allowed:

- inspect/read/analyze
- run non-destructive tests
- inspect Git, DB, migrations, architecture, tests, deployment and logs
- create NEW governance/audit documents
- propose ADRs and Change Requests

---

## 4. Current Known Baseline

The following is the currently known baseline and must be independently verified during audit:

- **Branch:** `feat/ai-decision-workspace-v1`
- **Known latest commit:** `0566ef5` — `fix(e2e): handle missing financial data semantics`
- **Known full backend regression:** 530 tests passed
- **Known frontend checks:** typecheck PASS, lint PASS, build PASS
- **Known application status:** Waves 1–6 implemented at different verification levels; final product-level governance classification pending feature inventory
- **Production status:** NOT CERTIFIED / NO production-readiness evidence baseline approved yet

Known product findings requiring governance treatment rather than ad-hoc fixes:

- project profile editing flow
- existing study editing flow
- New Study versus Edit Study semantics
- backward navigation in feasibility wizard
- assumption editing/recalculation lifecycle
- study/business-record versioning
- Arabic PDF rendering
- final full-lifecycle E2E certification gaps
- Wave 3 catalog/acceptance dataset availability
- Validation requirement for real non-simulated evidence

Any unavailable fact must be recorded as **UNKNOWN**.

---

## 5. Required Governance Directory

Saudi Business governance documentation shall use:

```text
docs/
├── 00-governance/
├── 01-product/
├── 02-requirements/
├── 03-architecture/
├── 04-design/
├── 05-delivery/
├── 06-testing/
├── 07-operations/
├── 08-security-compliance/
└── 09-releases/
```

Historical architecture documents must not be silently rewritten. Existing authoritative architecture must be referenced and reviewed.

---

## 6. Immediate Baseline Artifacts Required

Before further feature implementation, create or reconstruct:

### Governance
- `docs/00-governance/current-state-baseline.md`
- `docs/00-governance/workspace-audit.md`
- `docs/00-governance/design-review.md`
- `docs/00-governance/architecture-constitution.md`
- `docs/00-governance/change-control.md`
- `docs/00-governance/review-policy.md`
- `docs/00-governance/versioning-policy.md`
- `docs/00-governance/definition-of-ready.md`
- `docs/00-governance/definition-of-done.md`
- `docs/00-governance/risk-register.md`
- `docs/00-governance/assumptions-register.md`
- `docs/00-governance/dependency-register.md`
- `docs/00-governance/decision-register.md`

### Product / Requirements
- business case
- product vision
- PRD
- scope
- personas
- user journeys
- functional requirements
- non-functional requirements
- acceptance criteria
- traceability matrix

### Architecture / Design
- architecture baseline/review
- HLD
- domain model
- deployment architecture
- LLD
- database design
- API contracts
- integration architecture
- AI architecture
- agent architecture where applicable
- security architecture
- cost model
- ADR inventory

### Delivery / Testing / Operations
- roadmap
- backlog
- milestones
- phase plan
- test strategy
- test matrix
- E2E plan
- regression plan
- AI evaluation where applicable
- SLO/observability/logging/alerting
- backup/restore
- DR
- incident response
- runbooks
- production readiness

---

## 7. Saudi Business Product Lifecycle Baseline

The current intended business lifecycle is:

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

The audit must verify that the **same project/study identity and data lineage** persist across this lifecycle.

No lifecycle stage is considered complete merely because an endpoint, screen, unit test, or mocked workflow exists.

---

## 8. Feature Verification Classification

Every major feature must be classified using only:

- NOT_IMPLEMENTED
- PARTIAL
- IMPLEMENTED_NOT_VERIFIED
- VERIFIED_UNIT
- VERIFIED_INTEGRATION
- VERIFIED_WITH_MOCKS_ONLY
- VERIFIED_LIVE_E2E
- PRODUCTION_READY
- BLOCKED
- DEPRECATED

Do not use unsupported percentages.

---

## 9. Saudi Business Data / Evidence Rules

Mandatory evidence classifications:

- VERIFIED_EXTERNAL_FACT
- USER_INPUT
- USER_ASSUMPTION
- PLATFORM_DERIVED
- ACTUAL
- FORECAST
- UNKNOWN

Rules:

- UNKNOWN ≠ ZERO
- USER_ASSUMPTION ≠ FACT
- POTENTIAL FUNDING ≠ CASH
- GUARANTEE ≠ CASH
- AI output ≠ authoritative factual state
- deterministic financial calculations remain deterministic
- business records must not silently overwrite history when versioning is required

---

## 10. Source of Truth Boundaries

AI may interpret, classify, summarize, recommend, and explain.

AI must not become authoritative truth for:

- project/account identity
- user-entered business facts
- actual financial records
- funding approvals
- lender/regulator decisions
- official eligibility
- deterministic financial outputs
- external verified facts without provenance

---

## 11. Architecture Governance

The approved architecture is the design contract.

Implementation agents may not independently change:

- architecture style
- domain boundaries
- database technology/ownership
- tenancy
- authentication/authorization
- public API contracts
- AI/agent architecture
- model-provider strategy
- integration pattern
- deployment/security/source-of-truth model
- storage/observability strategy
- major framework versions

Any material change requires a formal CR and, where applicable, a new ADR.

---

## 12. Candidate Change Requests Already Identified

The baseline audit should assess and formalize, where justified:

- **CR — Project Profile Editing**
- **CR — Existing Study Editing Workspace**
- **CR — New Study vs Edit Study Semantics**
- **CR — Study / Business Record Versioning**
- **CR — Feasibility Wizard Navigation / Reopen Flow**
- **CR — Arabic PDF Rendering**
- **CR — Acceptance / Certification Dataset Strategy**
- **CR — Internal Project Governance Dashboard**

These are proposals only until formally reviewed and approved.

---

## 13. Definition of Done Enforcement

A Saudi Business feature is not DONE because code exists, UI exists, an endpoint exists, unit tests pass, or mocks pass.

DONE requires, as applicable:

- requirement satisfied
- architecture compliant
- real DB/persistence works
- refresh/reopen works
- restart persistence where applicable
- integration/failure paths verified
- browser E2E passes
- external integration verified live where applicable
- Arabic/localization checked
- security/error handling checked
- docs and traceability updated
- rollback defined
- evidence stored

---

## 14. AI / Agent Limits

Before any AI workflow is approved it must define:

- model/provider
- exact business role
- tools/data access
- maximum LLM calls
- maximum tool calls
- maximum tokens
- maximum retries
- maximum execution time
- failure/escalation behavior
- cost estimate or UNKNOWN — COST REVIEW REQUIRED

No unlimited autonomous loops.

Preferred LLM-call budget:

- simple: 1
- moderate: ≤2
- complex: ≤3 unless explicitly approved

---

## 15. Testing Standard

Saudi Business test evidence must distinguish:

- MOCK VERIFIED
- INTEGRATION VERIFIED
- LIVE E2E VERIFIED
- PRODUCTION VERIFIED

Required test strategy covers:

Unit, Integration, Contract, DB, Migration, Browser, E2E, Regression, Security, Load, Failure, Recovery, Accessibility, Localization/Arabic, Production Smoke, AI Evaluation where applicable.

---

## 16. Governance Dashboard

After the governance baseline is approved, Saudi Business must implement an internal governance dashboard in an admin/internal area, using a machine-readable governance manifest rather than manually hardcoded status.

The dashboard is **not implemented during the first baseline audit**.

It must later answer:

- current phase and gate
- roadmap/milestones
- architecture version and ADR/CR state
- requirements and verification levels
- risks and blockers
- testing evidence
- release/production status
- AI workflows/agents/call limits/cost
- known/unknown costs
- documentation completeness

Recommended manifest: `project-governance.json`.

---

## 17. Formal Gates

Saudi Business shall use:

- G0 Business
- G1 Product
- G2 Requirements
- G3 Data/Domain
- G4 Architecture
- G5 Detailed Design
- G6 Delivery Planning
- G7 Implementation
- G8 Verification
- G9 Operational Readiness
- G10 Production

The baseline audit must determine the **evidence-based current gate**. Do not infer it from previous Wave names.

---

## 18. Immediate Execution Order

For Saudi Business as an existing project:

A. Protect/record current state  
B. Read-only workspace audit  
C. Product/design review  
D. Architecture review  
E. Feature inventory  
F. Requirements reconstruction  
G. Current-vs-target architecture  
H. ADR / CR proposals  
I. HLD / LLD / Data / API  
J. AI / Integration / Security / Cost  
K. Roadmap / Backlog  
L. Testing / Operations  
M. Governance manifest  
N. Baseline freeze proposal  
**STOP**

Implementation starts only after baseline acceptance.

---

## 19. Baseline Freeze

Once approved, create independent identifiers for:

- Product Baseline
- Architecture Baseline
- PRD Baseline
- Requirements Baseline
- Governance Baseline

Suggested initial proposal (not yet approved):

- `GOV-1.0`
- `ARCH-1.0`
- `PRD-1.0`
- `REQ-1.0`

Do not tag/freeze until audit and approval are complete.

---

## 20. Absolute Rules for Saudi Business

- No architecture improvisation.
- No hidden scope change.
- No silent DB/API/AI/integration changes.
- No uncontrolled agents or LLM loops.
- No fabricated business facts.
- No UNKNOWN-to-zero coercion.
- No mock-only production claims.
- No fake completion percentage.
- No invented dates/costs.
- No production deployment without readiness evidence.
- No future phase starts without baseline review.
- No feature closes without real user-visible behavior and persistence where applicable.

---

## 21. Next Governed Action

**READ-ONLY BASELINE AUDIT.**

The proposed Wave 6.5 multi-project acceptance/UX-hardening exercise is deferred until the baseline audit is approved and its work is represented as governed backlog items with acceptance criteria.

Wave 7 / Knowledge Workspace remains NOT STARTED.
