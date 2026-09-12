# Owner Acceptance Test — Post-merge Production Rerun

**Gate:** OWNER TESTABILITY (binary PASS/FAIL)  
**Production URL:** https://saudi-business-web.vercel.app  
**Validated application-code SHA:** `1f1a3057b18ec4a4e972d0cb7178688dfef1b3ea`  
**PR #33 merge commit:** `1f1a3057b18ec4a4e972d0cb7178688dfef1b3ea`  
**Evidence merge:** PR #34 (documentation/screenshots only; no application behavior change)  
**Rerun date (UTC):** 2026-09-12  
**Scenario:** أريد إنشاء شركة خدمات أمن سيبراني في الرياض تقدم خدمات MSSP للشركات

**Account:** fresh production test account created through the UI; identifier redacted from public evidence.  
**Password:** intentionally not stored in repository evidence.

> SHA semantics: the OWNER GATE validates the application behavior introduced by PR #33 at `1f1a3057…`. Later documentation-only commits may advance `main` and Vercel's deployment SHA without changing the validated application code.

---

## Deploy confirmation

| Check | Result |
|-------|--------|
| PR #33 merged | Yes — https://github.com/majaber1/saudi-business/pull/33 |
| Validated application-code SHA | `1f1a3057b18ec4a4e972d0cb7178688dfef1b3ea` |
| Vercel `saudi-business-web` deployed from validated code | success (production) |
| `POST /api/v2/studies/{id}/continue` on prod | route live |
| Evidence package | PR #34, docs/screenshots only |

---

## PASS/FAIL — steps 1–19

| Step | Result | Evidence |
|------|--------|----------|
| 1 Open production URL | **PASS** | `owner-rerun-01-register.png` |
| 2 Register / Login | **PASS** | Fresh account created through production UI |
| 3 Dashboard | **PASS** | `owner-rerun-02-dashboard.png` |
| 4 Create project | **PASS** | `owner-rerun-03-project.png` |
| 5 Idea visible | **PASS** | Arabic MSSP idea visible on project |
| 6 Start AI study | **PASS** | `owner-rerun-04-study.png` / workspace |
| 7 Archetype friendly labels | **PASS** | `owner-rerun-05-archetype.png` — «أعمال خدمية», no raw primary IDs |
| 8 Complete Discovery | **PASS** | Reached assumptions with persisted answers |
| 9 AI Estimate where useful | **PASS** | Estimate invoked where available; manual answer path used when estimate stalled |
| 10 Assumptions CTA | **PASS** | `owner-rerun-07-assumptions-cta.png` — «اعتماد والمتابعة للتحليل المالي» |
| 11 Financial inside study | **PASS** | `owner-rerun-08-financial-in-study.png` — workspace URL, not `/tools/financial`; NPV/IRR shown |
| 12 Risks from study | **PASS** | `owner-late-04-after-risks-click.png` — risks panel + continue CTA |
| 13 Decision from study | **PASS** | `owner-late-05-decision-report.png` — `GO_WITH_CONDITIONS` |
| 14 Report from study | **PASS** | Same study workspace — final report + print/save |
| 15 Refresh persists | **PASS** | Report panel remains after reload |
| 16 Logout | **PASS** | Visible UI logout control → login |
| 17 Login again | **PASS** | Same account returns to product |
| 18 Find project via Projects | **PASS** | Projects navigation → same project; no pasted study URL |
| 19 Reopen + full persistence | **PASS** | Continue study from project → same workspace; verdict/NPV/assumptions/risks/report/friendly archetype persisted (`owner-persist-06-reopened.png`) |

---

## OWNER GATE: **PASS**

All required steps 1–19 were completed on production for the validated PR #33 application code.

### Strict-path compliance

- No database edits were used to satisfy the owner journey.
- No API shortcut was used in place of the owner UI flow.
- No hardcoded study URL was used for reopen verification; navigation used Projects → project → Continue study.
- Standalone `/tools/financial` was **not** used as the study financial path.
- Production evidence, not localhost evidence, is authoritative for this gate.

### Evidence chronology

- The first production run encountered an AI Estimate stall during Discovery; that run is retained as defect evidence in `OWNER_RERUN_RESULTS.md`.
- The owner journey was subsequently completed on the same production study using the normal UI/manual-answer path, then late stages and persistence were verified and captured in the post-merge evidence files.

### Remaining non-blocking observations

- AI Estimate can still stall mid-discovery; this is a separate reliability defect and is not hidden by the OWNER GATE result.
- A system/debug line may contain an internal archetype key, but primary owner-facing classification labels remain friendly Arabic.
