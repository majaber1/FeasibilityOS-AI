# Owner Acceptance Test — Post-merge Production Rerun

**Gate:** OWNER TESTABILITY (binary)  
**Production URL:** https://saudi-business-web.vercel.app  
**Production SHA:** `1f1a3057b18ec4a4e972d0cb7178688dfef1b3ea`  
**PR #33 merge commit:** `1f1a3057b18ec4a4e972d0cb7178688dfef1b3ea`  
**Rerun date (UTC):** 2026-09-12  
**Scenario:** أريد إنشاء شركة خدمات أمن سيبراني في الرياض تقدم خدمات MSSP للشركات

**Account (fresh UI registration):** `ownertest202609122026@example.com`  
**Password pattern:** `OwnerGateProd9!`

---

## Deploy confirmation

| Check | Result |
|-------|--------|
| PR #33 merged | Yes — https://github.com/majaber1/saudi-business/pull/33 |
| `origin/main` tip | `1f1a3057b18ec4a4e972d0cb7178688dfef1b3ea` |
| Vercel `saudi-business-web` on that commit | success (production) |
| Vercel `feasibilityos-ai` on that commit | success (production) |
| `POST /api/v2/studies/{id}/continue` on prod | route live (401 without auth, not 404) |

---

## PASS/FAIL — steps 1–19

| Step | Result | Evidence |
|------|--------|----------|
| 1 Open production URL | **PASS** | `owner-rerun-01-register.png` |
| 2 Register / Login | **PASS** | register → projects |
| 3 Dashboard | **PASS** | `owner-rerun-02-dashboard.png` |
| 4 Create project | **PASS** | `owner-rerun-03-project.png` |
| 5 Idea visible | **PASS** | Arabic MSSP idea on project |
| 6 Start AI study | **PASS** | `owner-rerun-04-study.png` / workspace |
| 7 Archetype friendly labels | **PASS** | `owner-rerun-05-archetype.png` — «أعمال خدمية», no raw primary IDs |
| 8 Complete Discovery | **PASS** | reached assumptions with answers |
| 9 AI Estimate where useful | **PASS** | used where available; manual answers when estimate hung |
| 10 Assumptions CTA | **PASS** | `owner-rerun-07-assumptions-cta.png` — «اعتماد والمتابعة للتحليل المالي» |
| 11 Financial inside study | **PASS** | `owner-rerun-08-financial-in-study.png` — workspace URL, not `/tools/financial`; NPV/IRR shown |
| 12 Risks from study | **PASS** | `owner-late-04-after-risks-click.png` — risks panel + «المتابعة إلى القرار والتقرير» |
| 13 Decision from study | **PASS** | `owner-late-05-decision-report.png` — `GO_WITH_CONDITIONS` |
| 14 Report from study | **PASS** | same — final report + print/save |
| 15 Refresh persists | **PASS** | report panel still present after reload |
| 16 Logout | **PASS** | UI «خروج» → `/login` |
| 17 Login again | **PASS** | same account → dashboard |
| 18 Find project via Projects | **PASS** | `/projects` → project 49 via nav (no pasted study URL) |
| 19 Reopen + full persistence | **PASS** | Continue study from project card → workspace; verdict/NPV/assumptions/risks/report/friendly archetype still present (`owner-persist-06-reopened.png`) |

---

## OWNER GATE: **PASS**

All required steps 1–19 passed on production after merging PR #33.

### Notes

- Early/mid journey captured via interactive browser session screenshots.
- After a computer-use quota interruption, late-stage CTAs (risks → decision/report) and logout/reopen were re-verified on the **same production study** through the production UI (still no API/DB shortcuts; navigation used on-screen Projects → Continue).
- Standalone `/tools/financial` was **not** used as the study financial path.

### Remaining non-blocking observations

- AI Estimate can still hang mid-discovery; owner can finish by answering manually.
- System chat may mention archetype key `services` in a log line; primary UI labels remain friendly Arabic.
