# Owner Acceptance Test — Saudi Business

**Gate:** OWNER TESTABILITY (binary PASS/FAIL — no completion %)  
**Production URL:** https://saudi-business-web.vercel.app  
**Production deploy SHA (live retest):** `93e4d385ac0d1338d98b1ebc33cfb27f2071263e`  
**Fix PR:** https://github.com/majaber1/saudi-business/pull/33  
**Branch tip (fixes, not on production):** `cursor/phase65-product-ux-hardening-1831`  
**Latest live retest (UTC):** 2026-09-12  
**Language:** Arabic (RTL)

**Single scenario:**

> أريد إنشاء شركة خدمات أمن سيبراني في الرياض تقدم خدمات MSSP للشركات

---

## 1) Production URL

https://saudi-business-web.vercel.app

---

## 2) Account

Create a fresh account on production (no shared seed):

1. Open https://saudi-business-web.vercel.app/register  
2. Enter name, email, password (≥8 chars, letter + number)  
3. Click إنشاء حساب  

Agent pattern: `OwnerGateTest9!` with a fresh email.  
Login: https://saudi-business-web.vercel.app/login

---

## 3) Exact 10-minute owner script

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open production URL | App loads |
| 2 | Register or Login | Enter product (Dashboard/Projects) |
| 3 | Click **لوحة التحكم** | Dashboard opens; workspace usable |
| 4 | **المشاريع** → **إضافة مشروع** → enter idea + budget → save | Project space opens |
| 5 | Confirm idea text visible | Same Arabic MSSP sentence |
| 6 | Click **دراسة جدوى بالذكاء الاصطناعي** | Study workspace opens |
| 7 | Confirm classification (friendly label) → continue | No raw IDs (`saas_digital`, etc.) |
| 8 | Complete AI Discovery (use **دع الذكاء الاصطناعي يقدر**) | Interview completes |
| 9 | Review assumptions → **اعتماد والمتابعة للتحليل المالي** | Assumptions visible; clear next CTA |
| 10 | Run **financial analysis inside the study** | NPV/IRR from study assumptions |
| 11 | View risks → continue | Risks for this study |
| 12 | View decision | Decision for this study |
| 13 | Open report | Report for this study |
| 14 | Refresh browser | Progress still there |
| 15 | **خروج** | Logged out (visible Log out control) |
| 16 | Login again | Dashboard |
| 17 | Open **المشاريع** (not Opportunities) | Same project listed |
| 18 | Continue AI study | Same study reopens |
| 19 | Confirm answers / assumptions / analysis / report | Persisted |

Screenshots: `docs/evidence/owner-gate-screenshots/` and `/opt/cursor/artifacts/owner-*.png`

---

## 4) PASS/FAIL — production UI (2026-09-12 live E2E)

| Step | Result | Notes |
|------|--------|-------|
| 1 Open URL | **PASS** | |
| 2 Register/Login | **PASS** | Fresh UI registration |
| 3 Dashboard | **PASS** | Cleaner than earlier runs |
| 4 Create project | **PASS** | |
| 5 Idea visible | **PASS** | |
| 6 Start AI study | **PASS** | |
| 7 Archetype | **PASS*** | Latest run showed friendly Arabic label; earlier run had raw IDs — treat as unstable until PR deploy |
| 8 AI Discovery | **PASS** | AI estimate used |
| 9 Assumptions | **PASS*** | Review panel reached; no clear “continue to financial” on production |
| 10 In-study financial | **FAIL** | **PRODUCT_FAILURE** — lands on disconnected `/tools/financial` |
| 11 Risks | **FAIL** | Not reachable after assumptions |
| 12 Decision | **FAIL** | Not reachable |
| 13 Report | **FAIL** | Not reachable |
| 14 Refresh | **PASS** | Project still listed |
| 15 Logout | **FAIL** | Log out hard to discover on production UI |
| 16 Re-login | **FAIL** | Blocked by logout discoverability |
| 17 Find project | **PASS** | Via dashboard / URL fallback |
| 18 Reopen study | **FAIL** | **PRODUCT_FAILURE** — reopen / continue path unreliable |
| 19 Persistence of analysis/report | **FAIL** | Never reached late stages |

\* Steps 7/9 improved vs earlier baseline but remain gated by missing production deploy of PR #33 journey CTAs.

### Shell / nav blockers on production

| Issue | Status |
|-------|--------|
| Marketing footer on app pages | Fix on PR #33 — not deployed |
| Disconnected Financial tool | Banner + in-study continue on PR #33 — not deployed |
| Assumptions → Financial → Risks → Decision → Report CTAs | `/continue` + panels on PR #33 — not deployed |
| Projects vs Opportunities confusion | Signed-in nav prefers Projects on PR #33 — not deployed |
| Logout discoverability | Stronger Log out + mobile entry on PR #33 — not deployed |
| Study reopen after logout | Reopen wiring on PR #33 — not deployed |

---

## 5) Known remaining blockers

**OWNER GATE: FAIL — not DONE.**

PR #33 contains the product fixes. Production SHA `93e4d385…` does not include them.

Do not claim DONE until a fresh production re-run shows **PASS on steps 1–19** with no workarounds.

---

## 6) Commit / PR / Production SHA

| Item | Value |
|------|-------|
| Production URL | https://saudi-business-web.vercel.app |
| Production SHA | `93e4d385ac0d1338d98b1ebc33cfb27f2071263e` |
| Fix PR | https://github.com/majaber1/saudi-business/pull/33 |
| Fix branch | `cursor/phase65-product-ux-hardening-1831` |

---

## Re-test after deploy

1. Merge PR #33 and wait for production deploy.  
2. Repeat this script with a **new** account.  
3. Gate flips DONE only when every required step is **PASS**.
