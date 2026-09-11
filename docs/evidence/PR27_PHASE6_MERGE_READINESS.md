# PR #27 — Final Merge Readiness (Phase 6 Knowledge MVP)

**Date:** 2026-09-11  
**PR:** https://github.com/majaber1/saudi-business/pull/27  
**Commit:** `866e0f2d54e0c5166dea7ed0700a098d266b804b`
**Scope:** Merge readiness only — no feature expansion.

---

## 1) Vercel `feasibilityos-ai` failure

| Field | Value |
|------|-------|
| Classification | **PLATFORM** (not code-related) |
| Error | `Resource provisioning failed` / `BUILD_FAILED` |
| Build duration | **0 ms** (empty build output) |
| Pattern | Recent **PR preview** deploys for `feasibilityos-ai` fail with the same provisioning error, including **unrelated** PR branches (e.g. Discovery Advisor). **`main` deploys remain READY**. |
| Entrypoint | Unchanged `api/index.py` FastAPI shim — no Phase 6 code path required for this serverless entry. |
| Action taken | Documented only. No code change (would not expand scope / would not fix platform provisioning). |

Evidence: `/opt/cursor/artifacts/merge_ready_vercel_ai_classification.json`

---

## 2) Preview / runtime verification

| Check | Result | Evidence |
|------|--------|----------|
| Frontend preview loads | **PASS** (HTTP 200 via Trusted Sources OIDC; title `Saudi Business \| سعودي بزنس`) | `/opt/cursor/artifacts/merge_ready_frontend_check.json`, screenshot `/opt/cursor/artifacts/merge_ready_frontend_preview.png` |
| Backend health | **PASS** (`db_connected=true`, postgres) | `/opt/cursor/artifacts/merge_ready_backend_health.json` |
| Database connection | **PASS** | same + `/opt/cursor/artifacts/merge_ready_db_migrations.json` |
| Migrations | **PASS** — Alembic head `0028_knowledge_intel`; tables `knowledge_documents`, `knowledge_chunks`, `knowledge_evidence`, `study_memories` | `/opt/cursor/artifacts/merge_ready_db_migrations.json` |
| GitHub Actions CI | **PASS** (backend/frontend/migrations/secret scan/docker) on `866e0f2` | PR checks |
| Web Vercel preview | **PASS** (`saudi-business-web` READY) | PR checks |

Notes:
- Frontend preview is behind Vercel Authentication SSO; verified with `x-vercel-trusted-oidc-idp-token`.
- `feasibilityos-ai` preview is unavailable due to platform provisioning; merge-readiness smoke used the PR-branch local/API runtime with current commit + migrated DB.

---

## 3) Minimal Phase 6 smoke

Flow exercised:

Upload knowledge document → Extraction → Metadata → Storage → Retrieve for new study → Assumptions receive knowledge references → Financial / Risk / Decision / Report

| Step | Result |
|------|--------|
| Upload + extract + metadata + chunks | PASS (`project_type=data_center`, status ready, chunk_count=1, capex/opex/assumptions present) |
| Retrieve | PASS (`hit_count=1`, citations=1, **no embedding leak**) |
| Assumptions with knowledge refs | PASS (**7/7** assumptions with `knowledge_refs`; origin `knowledge_reference`) |
| Engines unchanged path | PASS phases `ASSUMPTIONS_REVIEW → ANALYZED → DECISION_READY → REPORT_READY`; financial results present; verdict returned |
| Study memory feedback | PASS (`memories_count=1` after REPORT_READY) |
| Overall | **PASS** |

Evidence: `/opt/cursor/artifacts/merge_ready_phase6_smoke.json`

---

## Final gate

| Gate | Status |
|------|--------|
| CI | PASS |
| Frontend | PASS |
| Backend | PASS |
| Migration | PASS |
| Vercel AI issue | **PLATFORM** |
| Phase 6 smoke | **PASS** |
| **MERGE** | **READY** |

Caveat: PR check rollup remains `UNSTABLE` solely because of the platform `feasibilityos-ai` preview failure. GitHub Actions required app checks are green; web preview is green.
