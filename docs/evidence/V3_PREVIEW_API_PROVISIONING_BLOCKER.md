# V3 Follow-up — Backend Preview Provisioning Blocker

**Date (UTC):** 2026-09-12  
**Candidate tip:** `6e19a5415163c082b8fc82b6d818d94e4a363824` (`release/v3.0.0`)  
**PR:** https://github.com/majaber1/saudi-business/pull/36

## Finding

`feasibilityos-ai` **preview** deployments fail immediately with:

- `errorCode`: `BUILD_FAILED`
- `errorMessage`: `Resource provisioning failed`
- Build output empty / ~0ms — failure before meaningful app build

Reproduced for:

- Git deployments of `release/v3.0.0` (including tip `6e19a54`)
- Many other non-main branches over the last day+
- CLI `vercel deploy` linked to `feasibilityos-ai`

## Contrast

| Deploy | Result |
|--------|--------|
| Production API `https://feasibilityos-ai.vercel.app` from `main` @ `fa9ecbc` | READY |
| Production Web `https://saudi-business-web.vercel.app` from `main` @ `fa9ecbc` | READY |
| Preview Web `saudi-business-web` @ tip `6e19a54` | READY |
| Preview API `feasibilityos-ai` @ tip `6e19a54` | ERROR |

Example failed deploy: `dpl_6nE2Dt4kTn8M8GA1eq1tL1gkNPT4`  
Inspector: https://vercel.com/20262031/feasibilityos-ai/6nE2Dt4kTn8M8GA1eq1tL1gkNPT4

## Impact on V3 release

- Candidate Financial Trust + Owner Gate already **PASS** locally.
- Pre-merge **live preview API** Owner Gate / five-scenario smoke is **blocked** by platform provisioning (not by V3 financial code).
- Production remains on baseline `fa9ecbc` until PR merge + prod deploy.
- Tag `v3.0.0` remains **not ready**.

## Recommended next actions (owner)

1. Fix Neon/Vercel preview resource provisioning for `feasibilityos-ai`, **or**
2. Merge PR #36 → production deploy Web+API → run Owner Gate 19/19 + FT five smokes on production SHAs → then tag.
