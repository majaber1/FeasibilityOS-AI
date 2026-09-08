# Saudi Business — Product Architecture

Last verified against current `main`: **2026-08-26**.

## Source-of-truth policy

1. Current GitHub `main` is the code authority.
2. `GET /api/deployment-health` on the public web application is the runtime authority for frontend/backend reachability and safe dependency state.
3. Backend `/health` and `/health/ready` are the detailed operational contracts.
4. This file is the canonical architecture document.
5. Historical implementation plans and audits are dated evidence and must not override current runtime/code.

## Runtime topology

```text
Browser
  |
  v
Next.js 16 web app
  |-- same-origin /api/backend/* rewrite
  |-- public /api/deployment-health
  |
  | server-only BACKEND_API_URL
  v
FastAPI backend
  |-- auth / RBAC
  |-- businesses/projects
  |-- feasibility / financial
  |-- funding / qualification
  |-- proposals / reports
  |-- opportunities / franchises
  |-- documents / leads / admin
  |-- /health
  `-- /health/ready
        |
        +--> PostgreSQL
        `--> Cloudflare R2 for authenticated funding documents
```

The frontend and backend are separate deployable components but form one product. Browser clients use a same-origin rewrite by default; the backend origin stays server-side.

## Core product model

```text
Customer Account
  ↓
Organization / Business Context
  ↓
Business / Project
  ↓
Independent Tools / Services
```

Major tools can be entered independently and can optionally reuse shared business/project context. Linking between outputs is explicit rather than silently merging unrelated workflows.

## Current service boundaries

| Service | Web route | Backend boundary | Current state |
| --- | --- | --- | --- |
| Feasibility Study | `/tools/feasibility` | feasibility API | Implemented |
| Financial Analysis | `/tools/financial` | financial API | Implemented |
| Funding Matcher | `/tools/funding` | funding API | Implemented |
| Business Qualification | `/tools/qualification` | qualification API | Implemented |
| Proposal Builder | proposal workflow | proposals API | Implemented/MVP |
| Reports | reports workflow | reports API | Implemented |
| Investment Opportunities | opportunities workflow | opportunities API | Implemented |
| Franchise | franchise workflow | franchises API | Catalog/service boundary |
| Funding Documents | funding/document workflow | documents API + Cloudflare R2 | Implemented; runtime configuration health-reported |
| Leads | public/product CTAs | leads API | Implemented |
| Admin / Metrics | protected admin | admin/metrics | Implemented |

### Removed boundary

**Auctions are removed from the current application and database migration history includes their removal.** Do not restore or document `/tools/auctions` or `/api/auctions` as an active current service unless a future product decision explicitly reintroduces them.

## Persistence

### PostgreSQL

The FastAPI backend is designed for PostgreSQL production persistence. Health never equates a configured URL with a working database: `/health` performs a safe connection ping and `/health/ready` gates production readiness.

Development/demo SQLite states are clearly labelled non-production and non-durable where applicable.

### Cloudflare R2

Authenticated funding documents use `backend/app/services/object_storage.py`, which creates an S3-compatible client for Cloudflare R2 using:

- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`

Backend health reports only whether the complete R2 configuration is present and the provider label; it never returns credential values.

## Health contract

### Public web health

`GET /api/deployment-health`

The Next.js server calls backend `/health/ready` and `/health`, then returns a safe allow-list including:

- frontend/backend readiness
- service/version/environment
- DB enabled/backend/connected state
- persistence label
- object-storage state/provider

### Backend health

- `GET /health` — liveness + safe dependency state.
- `GET /health/ready` — production readiness gate with safe failure codes.

Jaber Dashboard should consume the public deployment-health URL rather than relying on hardcoded repository-audit text.

## Security model

- Role-based APIs and protected admin boundaries.
- JWT production secret requirements are part of readiness checks.
- Email delivery is only a readiness requirement when email verification is explicitly enabled.
- CORS is deny-by-default in production unless configured.
- Browser-to-backend traffic normally stays same-origin through the Next.js rewrite.
- R2 and database credentials are server-only secrets.

## Modular architecture

Saudi Business is a modular monolith, not a collection of microservices. Tool boundaries are explicit in routes/models/APIs so a service can be extracted later if scale, ownership or commercial packaging requires it. Until then, unnecessary service separation should be avoided.

## Documentation maintenance rule

Changes to active modules, database/storage providers, health contracts, deployment topology or product boundaries must update this document and README in the same PR. Jaber Dashboard sync should flag documentation drift when the referenced blobs or verification timestamps fall behind relevant code changes.
