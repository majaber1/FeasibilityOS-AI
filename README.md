# Saudi Business | سعودي بزنس

Saudi-first bilingual business workspace for feasibility, financial analysis, funding matching, business qualification, proposals, reports and investment opportunities.

## Operational source of truth

Last verified against current `main`: **2026-08-26**.

| Layer | Canonical source | Current state |
| --- | --- | --- |
| Code | `main` in `majaber1/saudi-business` | Next.js 16 frontend + FastAPI backend |
| Production web | `https://saudi-business-web.vercel.app` | Public application |
| Public deployment health | `GET /api/deployment-health` | Server-side proxy to backend readiness/health |
| Backend liveness | `GET /health` | DB + persistence + Cloudflare R2 configuration summary |
| Backend readiness | `GET /health/ready` | Production readiness gate |
| Database | PostgreSQL | Health reports actual connectivity; demo SQLite is explicitly non-production |
| Document storage | Cloudflare R2 | Implemented in `backend/app/services/object_storage.py`; health reports whether the four R2 variables are configured |
| Architecture | `docs/PRODUCT_ARCHITECTURE.md` | Canonical current product architecture |

**Runtime health overrides prose.** Old audit reports and implementation notes are dated evidence. Jaber Dashboard should read `.jaber-dashboard.json`, GitHub HEAD and the public deployment-health endpoint instead of copying operational claims manually.

## Current V1 capabilities

- Registration/login and role-based access
- Business/project workspace
- Feasibility workflow
- Financial analysis
- Funding matching
- Business qualification
- Proposal builder
- PDF/DOCX report generation
- Investment opportunities
- Franchise catalog
- Lead capture
- Protected administration/metrics
- Authenticated funding-document upload/download backed by Cloudflare R2 when configured
- Bilingual Arabic/English Next.js interface
- PostgreSQL-backed FastAPI services

### Explicitly removed / not claimed

- **Auctions are removed from the current product.** Old architecture/readme references to `/tools/auctions` or `/api/auctions` are stale and must not be used.
- Live payments are not silently simulated.
- Government/funding catalogs may include clearly labelled sample or unverified data until an authoritative integration is configured.
- Multazim GRC remains a separate product boundary.

## Health contract

Public web endpoint:

```text
GET https://saudi-business-web.vercel.app/api/deployment-health
```

Backend endpoints:

```text
GET /health
GET /health/ready
```

Safe health fields include database connectivity/backend, persistence description and Cloudflare R2 configuration state. Secrets, hosts, passwords and access keys are not returned.

## Cloudflare R2

Funding-document storage uses:

```text
R2_ACCOUNT_ID
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
R2_BUCKET_NAME
```

The presence of the R2 implementation is not proof that production credentials are configured. Use `/api/deployment-health` / backend health for current runtime state.

## Local development

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH="backend"
uvicorn app.main:app --reload --app-dir backend
```

Linux/macOS:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=backend uvicorn app.main:app --reload --app-dir backend
```

Frontend:

```bash
cd apps/web
npm ci
npm run typecheck
npm run build
npm run dev
```

Run backend tests:

```bash
pytest tests/ -v
```

Apply migrations with a configured `DATABASE_URL`:

```bash
alembic -c database/alembic.ini upgrade head
```

Hosted web deployments must set server-only `BACKEND_API_URL`. Browser API traffic defaults to the same-origin `/api/backend` rewrite, so the backend can keep a deny-by-default CORS posture.

## Architecture and operations

- [`docs/PRODUCT_ARCHITECTURE.md`](docs/PRODUCT_ARCHITECTURE.md) — current product/service architecture
- [`docs/PRODUCTION_RUNBOOK.md`](docs/PRODUCTION_RUNBOOK.md) — operations/readiness/backups
- [`docs/SAUDI_BUSINESS_FULL_AUDIT.md`](docs/SAUDI_BUSINESS_FULL_AUDIT.md) — dated audit evidence
- [`docs/BASELINE_TEST_RESULTS.md`](docs/BASELINE_TEST_RESULTS.md) — dated test baseline

Historical planning files may describe future modules. They do not override the current `main` implementation or live health.
