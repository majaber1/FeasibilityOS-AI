# Vercel `feasibilityos-ai` — Resource Provisioning Failure

**Date:** 2026-09-11  
**Scope:** Investigation only — no application / Phase 6 code changes.  
**Classification:** **VERCEL PLATFORM ISSUE**

---

## Verdict

| Result | Value |
|--------|-------|
| Classification | **VERCEL PLATFORM ISSUE** |
| Exact error | `errorCode=BUILD_FAILED`, `errorMessage=Resource provisioning failed` |
| Code issue? | **No** |
| Configuration root cause? | **No** (not causal for this failure mode) |
| Action | Document only |

---

## Exact error (failing PR preview)

| Field | Value |
|------|-------|
| Deployment | `dpl_CL34hhAjbB1y52MV6fNu3gWbDHrq` |
| URL | https://feasibilityos-52jbc7ukf-20262031.vercel.app |
| Target | Preview (`target=null`) |
| Branch / SHA | `cursor/knowledge-intelligence-layer-1831` / `b517b8b` (PR #27) |
| `errorCode` | `BUILD_FAILED` |
| `errorMessage` | `Resource provisioning failed` |
| Build duration | **~2s** created→ready; CLI shows build **0ms**, **empty** build events / logs |
| Lambdas | Placeholder build with `output: []` (never packaged) |
| Region | `iad1` |
| Plan | Hobby |

There are **no** Python install lines, dependency errors, OOM messages, maxDuration violations, or runtime stack traces. Failure occurs **before** the build machine runs `@vercel/python`.

---

## Working comparison (same project, same region, same plan)

| Field | Failing preview | Working production (PR #27 merge) |
|------|-----------------|-----------------------------------|
| Deployment | `dpl_CL34hhAjbB1y52MV6fNu3gWbDHrq` | `dpl_Bkb4YtS85kDQeSBrdwgCWaLdyMtA` |
| SHA | `b517b8b` (PR branch tip) | `b99c09e` (merge to `main`) |
| Ready state | `ERROR` | `READY` |
| Timing | ~2s | ~55s (clone → uv install → bytecode → deploy) |
| Function output | empty | `api/index.py` ~**87.73MB**, region `iad1` |
| Build machine (prod logs) | n/a (never started) | 2 cores / 8 GB, Washington D.C. (`iad1`) |

Production health after merge: `GET https://feasibilityos-ai.vercel.app/health` → **200**, `db_connected=true`, postgres.

---

## Pattern (decisive)

From Vercel deployment history for `feasibilityos-ai`:

1. **Last READY preview:** `2026-09-11T00:04:03Z` (`cursor/validate-ai-feasibility-workflow-1831`).
2. **From `2026-09-11T00:35:08Z` onward:** every **preview** deployment fails with the **same** `Resource provisioning failed`.
3. Affected branches include **unrelated** workstreams (assumptions, reliability, discovery advisor, Phase 6) — not specific to Knowledge Intelligence code.
4. **Production** deployments on `main` continue to succeed throughout the same window (including `b99c09e`).
5. Sibling project **`saudi-business-web`** preview + production remain **READY** for the same commits/branches.

This isolates the failure to **platform preview resource provisioning** for `feasibilityos-ai`, not to Phase 6 application code.

---

## Configuration checked (not root cause)

| Check | Finding |
|------|---------|
| `vercel.json` | Legacy `builds` + `@vercel/python` → `api/index.py`; routes `/(.*)` → entry. Unchanged vs working prod. |
| Runtime / region | `serverlessFunctionRegion` / `functionDefaultRegions`: **`iad1`** (preview + prod). |
| Function defaults | `functionDefaultTimeout`: **300s**; `functionDefaultMemoryType`: **standard**; Fluid on; build machine `basic` / fixed. |
| Framework | Project `framework=fastapi`; Node project setting `24.x` (Python runtime used for build). |
| Env — shared preview+prod | Neon/DB URLs, `GROQ_*`, related Postgres vars present on **both**. |
| Env — production only | `ENVIRONMENT`, `JWT_SECRET` (preview missing). **Not causal** for pre-build provisioning: older previews were READY without these; failure is before runtime/auth. |
| Runtime errors | None on failing previews (no function ever deployed). Prod `/health` OK. |
| Memory / size limit at fail | Not reached — no bundle produced. Working prod package ~87.73MB successfully. |

No configuration change is warranted for this incident. Adding preview `JWT_SECRET` would be a separate hardening item and would **not** fix `Resource provisioning failed`.

---

## Why not CODE ISSUE

- Same entrypoint and `vercel.json` deploy successfully to **production** for the merged Phase 6 SHA.
- Failures span **multiple unrelated PR branches** after a sharp cutoff time.
- Empty logs / 0ms build / empty lambda output = platform could not allocate a build/deploy slot, not an app compile failure.
- Web project previews for the same Git refs succeed.

---

## Action

**Document only.** Do not modify Phase 6 or application code for this failure.

Optional follow-ups (ops / Vercel support — out of scope here):

- Open Vercel support with project `feasibilityos-ai`, error `Resource provisioning failed`, cutoff ~`2026-09-11T00:35Z`, hobby plan, preview-only.
- Rely on **production** (`https://feasibilityos-ai.vercel.app`) for post-merge verification until preview provisioning recovers.

---

## Evidence artifact

`/opt/cursor/artifacts/vercel_ai_provisioning_investigation.json`
