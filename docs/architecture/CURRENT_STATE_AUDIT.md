# Saudi Business current-state audit

Audit date: 2026-09-02  
Branch baseline: `feat/ai-decision-workspace-v1` at `4f00dc2`

## Executive finding

The repository has authenticated project CRUD, an owner-scoped feasibility API, a small deterministic calculator, and basic PDF/DOCX export. It does **not** yet implement the requested AI Business Decision Workspace. The production-shaped journey stops at a three-step creation wizard. Existing studies have no permanent frontend route, the Projects page always starts the wizard again, browser local storage holds bearer tokens, and most study state is an unvalidated JSON object. A completed result can be persisted in PostgreSQL but cannot be reopened through the customer interface.

Production release for this epic is **NO-GO** until the golden journey passes against Preview with real PostgreSQL, AI Gateway, evidence snapshots, and rendered Arabic reports.

## Current user journey and persistence

1. Registration and login call FastAPI. Login returns a JWT saved as `sb_token` in `localStorage`.
2. `/projects` loads owner-scoped projects and supports create, edit, archive, and restore.
3. Every active project links to `/feasibility/new?project_id=…`, even if a study exists or is complete.
4. The wizard creates a study, keeps its active step in React memory, saves one financial-input step, computes, and offers a new report download.
5. Refresh returns the wizard to step 1 and can create a duplicate. No baseline project/study detail URL exists.

Projects persist in PostgreSQL when configured. Development can use explicitly marked in-memory project records; auth, studies, and reports return 503 without a database. A study persists identity, status, `current_step`, and a general JSON payload. Step saves merge under `step_N`. Financial runs create rows, but API reads expose only the newest result. Reports create metadata rows without a stored artifact reference, so previous bytes cannot be reopened.

## Authentication

FastAPI implements registration, login, current user, profile update, password change, email verification, and password reset. Public roles are allowlisted; privileged roles cannot be self-assigned. Password policy, token expiry, one-time account tokens, generic invalid-login errors, and endpoint rate limiting exist. Email verification is opt-in and delivery depends on SMTP.

The frontend's bearer JWT is accessible to same-origin JavaScript. There is no HTTP-only session layer, refresh rotation/revocation, CSRF design, server-side protected-route middleware, or reliable redirect-back behavior on the baseline. Rate limiting is process-local and therefore not a complete serverless control.

## Database model

Existing entities include users, organizations, roles, projects, feasibility studies, financial assumptions/results/sensitivity scenarios, funding programs/matches, reports, documents, audit logs, account tokens, proposals, qualifications, notifications, and analytics events.

Missing target concepts are `study_versions`, `study_sections`, `evidence_items`, `source_snapshots`, `financial_models`, `scenario_runs`, `decision_snapshots`, `ai_runs`, `funding_program_versions`, and typed `audit_events`. Assumptions lack provenance and immutable version links. Results link only to a mutable study. Important codes are free-form strings. The baseline has neither a durable one-study-per-project invariant nor optimistic concurrency.

Migrations `0001`–`0008` are linear. CI exercises a fresh Postgres upgrade and downgrade/re-upgrade cycle. Existing production rows must be preserved by additive migrations.

## Financial engine

`financial-engine/calculator.py` deterministically calculates ROI, simple payback, break-even units, NPV, IRR, a three-way verdict, and revenue sensitivity. No LLM arithmetic is used. Missing outputs include full revenue/CAPEX/OPEX/COGS/staffing/working-capital models, P&L, cash flow, balance sheet, version-linked scenario runs, change comparison, and expanded sensitivity. The generic verdict lacks the required assumptions, evidence, risks, and explanation.

## Reporting

PDF generation uses Helvetica, which lacks dependable Arabic coverage. Shaping/bidi packages are optional and silently fall back to unshaped text. DOCX right-aligns paragraphs but does not set complex-script fonts/bidi properties. Reports contain only identity, a few metrics, verdict, and disclaimer; they omit evidence, sources, provenance, statements, scenarios, risks, licensing/funding notes, limitations, charts, and reproducible version metadata.

## Missing routes and broken journeys

- Permanent project and study workspace routes.
- Server-managed session creation/destruction and protected redirect-back.
- Study version, evidence, assumption, scenario, decision, AI-run, and report-history APIs.
- Evidence registry/ingestion/snapshot APIs.
- AI advisor streaming/tool API with persisted validated runs.
- Assumption confirmation/edit/recalculate and version comparison.
- Report listing/reopen by stored version.
- Database, object storage, and AI Gateway readiness checks.

Existing studies are routed to creation; refresh loses the active UI; concurrent tabs can overwrite JSON; latest-only results hide history; funding records are not linked to immutable evidence; internal codes appear in Arabic; and report metadata does not preserve an artifact.

## Security and data-quality risks

- XSS-accessible bearer tokens and no distributed revocation.
- Unvalidated JSON schema drift and ambiguous provenance.
- Financial inputs without currency/unit/time-basis metadata.
- No immutable source snapshot, checksum, or freshness policy.
- Funding eligibility can be mistaken for approval.
- Arabic PDF font/shaping is not guaranteed.
- Audit records lack request/version/AI/evidence correlation and a documented redaction policy.

## Retain

- Project-root ownership relationship and owner-scoped queries.
- Strict project mutation fields and public-role allowlist.
- Database-required production-shaped auth/study/report behavior.
- Deterministic financial module as a tested foundation.
- Same-origin Next.js proxy through server-only `BACKEND_API_URL`.
- Hashed, expiring, one-time account-action tokens.
- Additive Alembic workflow and Postgres migration CI.
- Arabic-first visual tokens, language provider, and UI primitives.

## Replace or redesign

- Ephemeral three-step wizard as the primary surface.
- Local-storage bearer auth as the final architecture.
- Unversioned all-purpose payload and latest-only result contract.
- Generic feasible/not-feasible customer verdict.
- Non-snapshotted funding/evidence presentation.
- Helvetica/optional-shaping report generation.
- Report metadata without durable artifacts.
- Process-local-only production rate limiting.

## Vercel and environment audit

The local frontend link targets team `20262031`, project `saudi-business-web`, ID `prj_AwjW55DHPwNwWE2GThQ09kQHb4wG`, Node 24.x. Live read-only inspection showed only `BACKEND_API_URL` in Preview and Production; values were not read. No AI Gateway variable was listed. The declared backend is `feasibilityos-ai`; its CLI inspection did not complete during the audit and made no mutation.

Repository configuration references `BACKEND_API_URL`, `NEXT_PUBLIC_API_BASE_URL`, `DATABASE_URL`, `POSTGRES_URL`, `JWT_SECRET`, `ENVIRONMENT`, `AUTO_MIGRATE_DB`, `CORS_ORIGINS`, `REQUIRE_EMAIL_VERIFICATION`, `SMTP_HOST`, `SMTP_FROM`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `PUBLIC_WEB_URL`, and `EXPOSE_ACCOUNT_TOKENS`. Object-storage and AI Gateway connectivity are absent from the audited study/report path.

## Tests and CI

Pytest covers auth, project ownership/CRUD, persistence, current financial helpers, funding, migration configuration, and selected services. The frontend has lint/typecheck/build but no component or browser-E2E suite. CI runs backend tests, dependency audits, frontend checks, Postgres migrations, secret scanning, and Compose validation. Production smoke is a shell-level check after `main`, not the required Preview golden journey.

## P0 direction

This branch first adds permanent project/study routes, derives CTAs from persisted studies, restores saved data by ID, checks project-study route consistency, exposes autosave state, makes creation idempotent, and rejects stale saves using a revision. Later phases must normalize/version the domain and replace placeholder sections with typed experiences.
