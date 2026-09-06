# Saudi Business — Read-Only Workspace Audit

## Document Control

- **Document ID:** SB-GOV-AUDIT-001
- **Title:** Read-Only Workspace Audit
- **Version:** GOV-0.1
- **Status:** DRAFT
- **Owner:** Project Governance Authority
- **Created Date:** 2026-09-06
- **Last Updated:** 2026-09-06
- **Related Requirements:** Requirements reconstruction pending
- **Related ADRs:** Existing ADR inventory pending formal review
- **Supersedes:** None
- **Change Summary:** First governance-era read-only audit of the existing Saudi Business implementation

---

## 1. Audit Scope and Safety

This audit was performed under the Saudi Business adoption of the **Master Project Governance, Architecture & Delivery Standard**.

Project classification: **EXISTING PROJECT**.

Audit mode: **READ-ONLY PRODUCT/ARCHITECTURE DISCOVERY**.

No product source code, API behavior, database schema, migration, test, authentication behavior, AI configuration, deployment configuration, or production environment was modified by this audit.

Governance documentation is the only permitted write during this activity.

### Audited source-control baseline

- Repository: `majaber1/saudi-business`
- Branch: `feat/ai-decision-workspace-v1`
- Product-code baseline before governance adoption: `0566ef527820b7f37240b4008ee8e68cc68e1d29`
- Governance branch HEAD at audit start: `a51ab878339340dfd1934f52edad22dbfc7e430f`
- Product-code baseline message: `fix(e2e): handle missing financial data semantics`
- Working-tree state: local workstation state was not directly inspectable in this remote audit; last user-verified product working tree was clean before governance commits.
- Production deployment status: **NOT VERIFIED**
- Production readiness: **NO-GO / NOT CERTIFIED**

Unknown items remain `UNKNOWN`; they are not inferred.

---

## 2. Authoritative Architecture Reviewed

The locked structural contract is:

`docs/architecture/SAUDI_BUSINESS_MASTER_ARCHITECTURE.md`

It defines Saudi Business as a **Business Decision, Funding & Growth OS** with the permanent lifecycle:

`IDEA → VALIDATE → STUDY → DECIDE → FUND → LICENSE → LAUNCH → MEASURE ACTUALS → FORECAST vs ACTUAL → REFORECAST → BUSINESS HEALTH → SCALE / FIX / PIVOT / STOP`

The fixed product waves are Wave 1 through Wave 6 only.

The persistent workspace is expected to preserve Project, Study, Company, Opportunity, Franchise, Documents, Reports, Versions, and Decisions.

The Product Blueprint additionally requires that all entry points converge into the same `Project → Study` aggregate and that saved business state not disappear as one-way wizard state.

The locked Feature Delivery Contract states that backend success is not feature success and that real user-visible persistence/navigation is required for a completed user-facing capability.

---

## 3. Repository / Workspace Inventory

The repository contains the following major implementation areas:

- `apps/web/` — Next.js web application
- `backend/app/` — FastAPI backend
- `database/migrations/` — Alembic schema history
- `database/seed.py` — explicitly demo/illustrative catalog seeding
- `financial-engine/` — deterministic feasibility calculator
- `funding-engine/` — deterministic funding helper/matcher foundation
- `backend/app/services/` — domain services for financial health, funding, opportunity fit, validation, launch, growth, reporting, storage and monitoring
- `backend/app/api/` — authenticated API surface
- `tests/` — backend/domain/API/migration test suite
- `.github/workflows/` — CI, migration validation, dependency audit, secret scan and production smoke workflows
- `run_browser_journey.py` / `run_browser_journey_wave4.py` — Playwright browser journey scripts
- `ai-engine/agents/agents.md` — conceptual AI-agent names only
- `knowledge-base/rag_pipeline.md` — conceptual RAG pipeline only
- `docs/` — architecture/product/delivery/governance material

### Current framework/runtime evidence

- Frontend: Next.js `16.3.0`
- React: `19.2.4`
- TypeScript: `5.9.3`
- Backend: FastAPI `0.141.1`
- SQLAlchemy: `2.0.35`
- Alembic: `1.13.3`
- PostgreSQL driver: psycopg2 `2.9.12`
- ReportLab: `4.2.2`
- python-docx: `1.1.2`
- CI Python: `3.11`
- CI Node: `22`
- Local runtime versions actually installed on the user workstation: **UNKNOWN**

---

## 4. Database and Persistence Audit

### Database architecture observed

`backend/app/db.py` resolves persistence in this order:

1. `DATABASE_URL`
2. `POSTGRES_URL`
3. non-production SQLite demo fallback

In production, the application does not silently fall back to SQLite when PostgreSQL configuration is absent.

Persistence-dependent study/report endpoints explicitly return failure rather than pretending durable state exists when persistence is not configured.

### Migration state

The latest migration present in the audited branch is:

`0024_wave6_integrity`

with parent:

`0023_growth_os`

The migration is additive and links `growth_decisions` to `growth_scenarios` through a nullable FK.

CI contains PostgreSQL migration upgrade/downgrade/re-upgrade checks.

### Persistence strengths

- Project ownership is enforced server-side.
- Studies are tied to a parent project.
- Study save operations support optimistic revision conflict detection.
- Assumptions are versioned by key and historical values are retired rather than overwritten.
- Financial calculations persist result rows.
- Validation, launch and growth have dedicated schema migrations and service layers.

### Persistence gaps / risks

1. **Study-level version history is incomplete.** `study.revision` is concurrency control, not a full immutable business snapshot/version model.
2. Financial API reads expose the latest financial result as the current result; the user-facing workspace does not expose a complete comparison/history experience.
3. The visible `Version history` study tab is not implemented as a real version-history feature; it currently falls through to generic section notes.
4. Report generation creates report metadata but regenerates bytes on each request; no audited durable report artifact reference is used by the feasibility report download path.
5. A formal immutable linkage among Project/Study version, assumptions, evidence, financial result, decision, launch baseline and later actuals is not yet evidenced end-to-end.

---

## 5. Authentication / Authorization Audit

The earlier 2026-09-02 audit identified a localStorage bearer-token design. The current branch has materially changed this implementation.

### Current observed design

- `/api/session/login` exchanges backend credentials and writes an HTTP-only `sb_session` cookie.
- Cookie settings include `httpOnly`, `SameSite=Lax`, and secure cookies on Vercel.
- The same-origin backend proxy replaces browser authorization with the server-side session cookie credential.
- Mutation proxy requests perform origin / `Sec-Fetch-Site` checks.
- A localStorage key still exists, but the intended current usage is a non-secret UI session hint (`session`), not the raw credential.
- Backend project/study access derives authorization from the authenticated user and parent-resource ownership.

### Current assessment

The old statement "raw bearer credential is stored in localStorage" is stale for the current branch and must not be repeated as current architecture without qualification.

Still requiring later security review:

- session revocation/rotation design
- distributed rate limiting
- CSRF posture beyond current same-origin checks
- tenant/organization isolation where organization-level tenancy is used
- production cookie/proxy verification
- privileged admin behavior

Security production status: **NOT ASSESSED / NOT CERTIFIED**.

---

## 6. Project and Study Lifecycle Audit

### Current persistent path

A permanent route exists:

`/projects/{projectId}`

and a permanent study route exists:

`/projects/{projectId}/studies/{studyId}`

The project workspace reuses the first existing study or creates one when none exists.

The backend `POST /feasibility/` enforces a one-study-per-project behavior for a provided `project_id`: if a study already exists, the existing resource is returned instead of creating a duplicate.

This is a meaningful improvement over the 2026-09-02 implementation.

### Critical coexistence problem

A legacy standalone flow still exists at:

`/feasibility/new`

That route behaves like an ephemeral three-step wizard while the approved architecture expects a persistent workspace.

The two experiences now coexist and expose different semantics to the user.

This is the most important product-flow drift identified by this audit.

---

## 7. Legacy Feasibility Wizard Findings

`apps/web/app/feasibility/new/page.tsx` contains several production-risk behaviors.

### 7.1 Synthetic financial values are preloaded

The route initializes:

- investment: `500000`
- revenues: `420000,600000,780000,900000,1020000`
- operating costs: `360000,430000,500000,560000,620000`
- fixed costs: `300000`
- variable-cost percentage: `25`
- discount rate: `10`

These are hardcoded UI defaults, not values derived from the user's business record or verified evidence.

This exactly explains the values observed during manual UAT.

Risk: a user can calculate and generate a feasibility result from synthetic defaults while believing the numbers belong to the project.

Classification: **CRITICAL**.

### 7.2 Step indicator is not navigation

The 1/2/3 step circles are rendered as non-interactive list items. There is no back/edit navigation from step 2 or step 3.

Classification: **HIGH**.

### 7.3 "New study" label conflicts with backend semantics

At result step, `resetWizard()` resets React state but retains linked project context and form values.

For a linked project, submitting step 1 again calls `createStudy`, while the backend returns the already existing study because the project is constrained to a single study.

Therefore the button labelled **New study** may actually reopen/reuse the current study and allow its step data to be overwritten/recomputed rather than create a new independent study.

This is not merely a cosmetic issue; it creates a material risk of user misunderstanding and unintended study modification.

Classification: **CRITICAL**.

### 7.4 Legacy funding shortcut

The wizard calls a simplified funding matcher using values including:

- `has_mvp = stage !== "idea"`
- `has_technical_team = true`

`has_technical_team=true` is not collected from the user in this flow.

This legacy shortcut conflicts with the stricter persistent Funding Intelligence semantics and must not be treated as authoritative funding-readiness evidence.

Classification: **HIGH**.

---

## 8. Project Workspace Findings

The `/projects` page provides actual Create/Edit/Archive/Restore behavior and calls the authenticated project API.

The `/projects/{id}` workspace provides a persistent path to continue/open the first study.

### Gaps

- The project-detail route does not surface a direct `Edit Project` control even though edit exists on the project-list page and backend API.
- The project list itself initializes a new-project investment input at `100000`; this is another synthetic numeric default that may be mistaken for a user assumption.
- Project → Studies presentation only uses the first study record; there is no explicit user-facing study/history model.
- Project metadata and Study Business Profile are separate concepts but the UX does not clearly explain their relationship.

---

## 9. Study Workspace Findings

The permanent study workspace contains section navigation for:

- Overview
- Business Profile
- Advisor
- Market Evidence
- Assumptions
- Financial Analysis
- Scenarios
- Risks
- Funding
- Validation
- Launch & Actuals
- Growth OS
- Compliance & Licensing
- Report
- Sources
- Version History

### Real wired sections observed

- Business Profile
- Evidence
- Assumptions
- Financial Analysis
- Funding
- Validation
- Launch
- Growth
- Sources when opportunity lineage exists

### Placeholder sections observed

The following visible tabs currently fall through to a generic section-notes textarea instead of a purpose-built product capability:

- Advisor
- Scenarios
- Risks
- Compliance & Licensing
- Report
- Version History
- Sources when no lineage exists

A visible tab must not be counted as implemented merely because generic notes can be saved.

Classification: **HIGH product-completeness risk**.

### Data-trust fallback issue

Opportunity-lineage rendering contains fallback values such as:

- verification status → `VERIFIED_CURRENT`
- data version → `1.0.0`
- transferred date → `2026-09-04`

when lineage values are missing.

A missing source-verification property must remain missing/unknown rather than become a fabricated verification state/date/version.

Classification: **CRITICAL data-trust issue**.

---

## 10. Business Profile Audit

`BusinessProfileTab` is a real editable/persisted form.

It supports:

- activity
- description
- city
- region
- target customer
- capacity/value unit
- legal form
- ownership notes
- existing-business flag
- company age
- current revenue

This is the actual **Project/Business Profile** information the user expected to reopen and edit.

UX problem: the path is discoverable only after entering the existing Study Workspace and selecting `ملف المشروع`; the standalone wizard does not route the user back to this persistent profile.

---

## 11. Assumptions and Financial Analysis Audit

### Strengths

- Assumptions distinguish `USER`, `EVIDENCE_DERIVED`, `AI_SUGGESTED`, and `DEFAULT` origins.
- Evidence-derived assumptions require same-study evidence.
- Posting a new assumption for the same key retires the previous version instead of deleting history.
- The financial-analysis workspace calculates from persisted assumptions.
- It requires `capex` and `revenue_year1` rather than inventing them when missing.
- Result UI labels calculated outputs as platform-derived `FORECAST` values.
- The deterministic feasibility calculation remains outside the LLM layer.

### Gaps

- The UI does not provide a direct "edit this assumption" action; the user must add a new row with the same key to create a version, which is technically sound but not obvious UX.
- The legacy wizard maintains a second, inconsistent input path based on step-2 cash-flow fields.
- Study-wide version comparison is not surfaced.

---

## 12. Funding Intelligence Audit

The repository contains dedicated services/APIs for:

- company financial profile
- financial health
- funding gap
- borrowing capacity
- collateral
- funding readiness
- funding programs
- funding matching
- financing structure

The latest product-code baseline changed missing financial periods from unexpected 404 behavior into explicit `INSUFFICIENT_DATA` / `NO_PERIODS_RECORDED` domain states.

This aligns with the governance rule `UNKNOWN != ZERO`.

### External data caution

A 12-program registry is embedded in service code with provider URLs, rule text and verification labels.

This audit confirms the code structure, but **does not independently verify the live external sources, current eligibility rules, or freshness of every program**.

Therefore no `PRODUCTION_READY` statement is permitted solely because the registry says `VERIFIED_CURRENT`.

The legacy `/feasibility/new` funding shortcut must not be conflated with the persistent Funding Intelligence workspace.

---

## 13. Opportunities / Franchise Audit

The current service includes a structured opportunity registry, provenance fields, matching logic and source-integrity rules.

Important positive control: the service explicitly prevents client/admin payloads from self-promoting an opportunity to `VERIFIED_CURRENT` and states that automated live primary-source verification is not active.

A Playwright browser journey exists for Wave 3 and is designed to test source provenance, fit, study creation, refresh and relogin persistence.

### Cautions

- Presence of a browser script is not proof it passed against the current audited commit/environment.
- Some repository seed data is explicitly `demo` / illustrative and cannot be used as real opportunity evidence.
- Live source freshness was not independently checked in this read-only code audit.

Current external-data production status: **NOT CERTIFIED**.

---

## 14. Validation, Launch and Growth Audit

Dedicated backend services, APIs, frontend components, tests and additive migrations exist for:

- Validation OS (`0021_validation_os`)
- Launch & Actuals (`0022_launch_actuals_os`)
- Growth OS (`0023_growth_os`, `0024_wave6_integrity`)

The implementation contains meaningful guardrails, persistence and lifecycle linkage.

However the complete cross-wave lifecycle is **not yet certified as one uninterrupted production-shaped journey**.

Remaining acceptance evidence is required for:

- real opportunity path on the same test project/study
- real/non-simulated validation evidence where GO is required
- complete refresh and logout/login persistence across lifecycle artifacts
- zero unexpected browser/network failures
- chronological consistency of current validation state and subsequent growth decisions

Accordingly Waves 4–6 must not be promoted to `PRODUCTION_READY` by this audit.

---

## 15. Reporting Audit

### Confirmed defect

PDF report generation uses ReportLab built-in `Helvetica` / `Helvetica-Bold` / `Helvetica-Oblique`.

Those fonts do not provide dependable Arabic glyph coverage.

The user has already observed Arabic content rendered as `nnnn` in a generated report.

Arabic shaping libraries are installed, but shaping does not solve missing glyph coverage in Helvetica.

### Additional gaps

- DOCX applies paragraph alignment but does not demonstrate a controlled complex-script font policy in the audited generator.
- Feasibility report content is still very limited relative to the product architecture.
- Report metadata is persisted, but the current feasibility download regenerates bytes instead of exposing an immutable reopenable report artifact/version.
- The visible `Report` and `Version History` workspace tabs are placeholders.

Classification: **CRITICAL for Arabic report quality; HIGH for report lifecycle/versioning**.

---

## 16. AI / Agent / RAG Audit

The locked architecture allows AI as assistant/analyst/advisor/explainer, never as the factual source of truth.

Current audited implementation evidence shows:

- `ai-engine/agents/agents.md` lists conceptual agents (CEO, Market, Financial, Risk, Funding, Document) with only one-line descriptions.
- `knowledge-base/rag_pipeline.md` is a conceptual pipeline diagram in text.
- The Study Workspace `Advisor` tab currently renders generic section notes rather than an AI advisor implementation.
- No production AI workflow, model provider, prompt/version registry, LLM budget, agent execution limits, RAG index, retrieval execution path, AI-run observability or live AI evaluation was established by this audit.

Therefore AI/Agent capability status is **NOT_IMPLEMENTED / NOT VERIFIED as a product capability**, regardless of conceptual documentation.

No undocumented agent should be introduced during remediation; AI work requires the governance AI architecture and ADR/budget controls first.

---

## 17. Storage and Documents Audit

Cloudflare R2 adapter code exists and requires explicit R2 configuration.

When storage is not configured, the adapter returns an explicit 503 rather than pretending success.

Known last observed local product state had object storage not configured; current production configuration is **UNKNOWN**.

Report artifacts are not using this storage path in the audited feasibility report endpoint.

---

## 18. Observability / Operations Audit

The backend has lightweight structured request logging and in-process request counters/average latency.

This is useful development observability but is not sufficient evidence of a complete production SLO/alerting/metrics architecture.

Not established by this audit:

- durable metrics backend
- dashboard ownership
- alert routing
- SLO burn alerts
- backup restore test evidence
- DR test evidence
- incident response exercise
- production rollback evidence

Operations readiness: **NOT ASSESSED / NOT CERTIFIED**.

---

## 19. CI / Testing Audit

CI includes:

- backend pytest
- targeted auth/security tests
- dependency audit
- frontend lint
- frontend typecheck
- frontend production build
- PostgreSQL migration tests
- secret scan
- Docker Compose validation

Last user-executed local evidence before governance adoption:

- focused financial-health / borrowing-capacity: 35 passed
- full backend suite: 530 passed
- frontend typecheck: PASS
- frontend lint: PASS
- frontend build: PASS

These are strong implementation checks but are not equivalent to final full lifecycle certification.

A real browser journey exists in the repository, but final current-commit, end-to-end acceptance remains incomplete.

---

## 20. Demo / Hardcoding / Source-Truth Findings

### Explicitly acceptable demo data

`database/seed.py` labels illustrative seed opportunities/franchises as demo and not real listings. Such data is acceptable for test/demo UX only and must never be presented as live market truth.

### Unsafe/default hardcoding requiring remediation proposal

- `/feasibility/new` financial defaults
- `/projects` default investment value
- wizard `has_technical_team=true`
- opportunity-lineage fallback `VERIFIED_CURRENT`
- opportunity-lineage fallback data version
- opportunity-lineage fallback transferred date

These are not all equivalent in severity, but each must be reviewed under source-of-truth rules before production certification.

---

## 21. Architecture Drift / Product Drift

### Drift A — Legacy ephemeral wizard

The approved architecture requires a persistent workspace; `/feasibility/new` still behaves as a disposable one-way wizard with synthetic assumptions.

**Status:** Architecture/Product drift requiring CR/remediation decision.

### Drift B — Visible placeholder capabilities

Several workspace tabs imply product capabilities but only store generic notes.

**Status:** Product/UX drift; must either be implemented according to requirements or explicitly marked unavailable/planned.

### Drift C — Version History not actually exposed

The architecture requires Versions in the persistent workspace. Assumption-level versioning exists, but a study-wide version-history UI/domain is incomplete.

**Status:** Partial architecture fulfillment.

### Drift D — AI product layer not actually implemented

Architecture defines allowed AI roles; conceptual agent docs exist, but a governed production AI capability is not wired into the user journey.

**Status:** Missing implementation, not an unauthorized architecture change.

### Drift E — Arabic reporting implementation does not satisfy Arabic-first product requirements

**Status:** Product/NFR implementation gap.

---

## 22. Maintainability / Technical Debt Signals

Several current source files have grown very large, including Growth, Launch, Validation, Opportunities, Funding and frontend API/workspace components.

Large-file size alone is not an architecture violation, but it creates maintainability/testability risk and should be measured before any refactor proposal.

No refactor is authorized by this audit.

---

## 23. Priority Findings

### BLOCKER / CRITICAL

1. Legacy feasibility wizard can calculate from hardcoded synthetic financial defaults.
2. `New study` UX conflicts with one-study-per-project backend semantics and can unintentionally modify/recompute the existing study.
3. Opportunity lineage can synthesize `VERIFIED_CURRENT`, version and date when those values are missing.
4. Arabic PDF is demonstrably unusable for Arabic content with current Helvetica implementation.
5. Full lifecycle acceptance is not yet certified; production remains NO-GO.

### HIGH

1. No clear backwards/edit navigation in legacy wizard.
2. Project profile/edit path is fragmented across project list and study workspace.
3. Visible workspace tabs are placeholders but look implemented.
4. Study-wide version history/compare/reopen behavior is incomplete.
5. Legacy funding shortcut contains a hardcoded technical-team assumption.
6. External funding/opportunity freshness is not independently live-verified by this audit.
7. Operations/security production readiness evidence is incomplete.

---

## 24. Proposed Change Requests — DO NOT IMPLEMENT YET

The following CRs should be drafted after baseline review:

- **CR-001 — Consolidate Project/Study Workspace Lifecycle and retire or redirect legacy feasibility wizard**
- **CR-002 — Study and calculation version history / comparison / immutable decision linkage**
- **CR-003 — Remove synthetic business-data defaults and enforce source/origin semantics across UI**
- **CR-004 — Arabic report rendering and persisted report artifacts**
- **CR-005 — Workspace placeholder capability policy and navigation cleanup**
- **CR-006 — Opportunity/funding provenance and freshness hardening**
- **CR-007 — Governed AI architecture and implementation plan**
- **CR-008 — Production operations/security readiness closure**

These are proposals only. No remediation was authorized or performed during this audit.

---

## 25. Audit Conclusion

Saudi Business now contains substantial real deterministic domain implementation across feasibility, funding, opportunities, validation, launch and growth. The permanent Project/Study workspace is materially stronger than the 2026-09-02 baseline.

The principal weakness is no longer simply "missing backend features". The dominant risk is **product-flow coherence and truth semantics**: the modern persistent workspace coexists with a legacy wizard that can expose synthetic assumptions and misleading lifecycle behavior.

**Current production-readiness decision: NO-GO / NOT CERTIFIED.**

**Next governance activity:** Design Review + Feature Inventory + Requirements reconstruction / CR proposal package.

STOP after baseline artifacts. Do not start remediation automatically.
