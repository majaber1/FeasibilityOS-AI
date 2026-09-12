# Owner Acceptance Test — Saudi Business

**Gate:** OWNER TESTABILITY (binary PASS/FAIL — no completion percentages)  
**Production URL:** https://saudi-business-web.vercel.app  
**Production deploy SHA (at last live retest):** `93e4d385ac0d1338d98b1ebc33cfb27f2071263e`  
**Fix PR:** https://github.com/majaber1/saudi-business/pull/33  
**Branch:** `cursor/phase65-product-ux-hardening-1831`  
**Test date (UTC):** 2026-09-12  
**Language:** Arabic (RTL)

**Single scenario:**

> أريد إنشاء شركة خدمات أمن سيبراني في الرياض تقدم خدمات MSSP للشركات

---

## 1) Production URL

https://saudi-business-web.vercel.app

---

## 2) Account

Create a fresh account on production (no shared seed account):

1. Open https://saudi-business-web.vercel.app/register  
2. Enter name, email, password (≥8 chars, letter + number)  
3. Click إنشاء حساب  

Agent runs used password pattern `OwnerGateTest9!` with a fresh email.

Login: https://saudi-business-web.vercel.app/login

---

## 3) Exact 10-minute owner script

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open production URL | App loads |
| 2 | Register or Login | Enter product (Dashboard/Projects) |
| 3 | Click **لوحة التحكم** | Dashboard opens; no giant marketing footer covering workspace |
| 4 | **المشاريع** → **إضافة مشروع** → enter idea text + budget → save | Project space opens |
| 5 | Confirm idea text visible | Same Arabic MSSP sentence shown |
| 6 | Click **دراسة جدوى بالذكاء الاصطناعي** | Study workspace opens (or **Continue** if study already exists) |
| 7 | Confirm classification (friendly label only) → continue | No raw IDs like `saas_digital` / `data_center` |
| 8 | Complete AI Discovery (use **دع الذكاء الاصطناعي يقدر** where useful) | Interview completes |
| 9 | Review assumptions in study → approve | Assumptions panel visible; no raw keys as primary labels |
| 10 | Use in-study **Financial** panel / **Continue** | NPV/IRR from study assumptions (not `/tools/financial` calculator) |
| 11 | View risks → **Continue** | Risks listed for this study |
| 12 | View decision | Verdict + rationale for this study |
| 13 | Open report panel | Report summary + print/save available |
| 14 | Refresh browser | Progress still there |
| 15 | **خروج** | Logged out |
| 16 | Login again | Dashboard |
| 17 | Open **المشاريع** / recent projects | Same project listed (no pasted URL) |
| 18 | Continue AI study | Same study reopens (not `/studies/new`) |
| 19 | Confirm answers / assumptions / analysis / report still present | Persisted |

Screenshots from production baseline: `docs/evidence/owner-gate-screenshots/`

---

## 4) PASS/FAIL (production UI, last live run)

| Step | Result | Evidence | Classification if fail |
|------|--------|----------|------------------------|
| 1 Open URL | **PASS** | owner-01 | |
| 2 Register/Login | **PASS** | owner-01 | |
| 3 Dashboard | **PASS** | owner-02 / owner-09 | Marketing footer noise (hard fail for shell cleanliness) |
| 4 Create project | **PASS** | owner-03 | |
| 5 Idea visible | **PASS** | owner-03 | |
| 6 Start AI study | **PASS** | owner-04 / owner-05 | |
| 7 Archetype | **FAIL** | owner-05 | **PRODUCT_FAILURE** — raw IDs on production |
| 8 AI Discovery | **PASS** | owner-06 | |
| 9 AI Estimate | **PASS** | owner-06 | |
| 10 Assumptions | **FAIL** | — | **PRODUCT_FAILURE** — not a clear next step on production |
| 11 In-study financial | **FAIL** | owner-07 | **PRODUCT_FAILURE** — standalone `/tools/financial` |
| 12 Risks | **FAIL** | — | **PRODUCT_FAILURE** — no owner CTA |
| 13 Decision | **FAIL** | — | **PRODUCT_FAILURE** — no owner CTA |
| 14 Report | **FAIL** | — | **PRODUCT_FAILURE** — no owner CTA |
| 15 Refresh | **PASS** | owner-08 | In-session |
| 16 Logout | **PASS** | | |
| 17 Re-login | **PASS** | owner-09 | |
| 18 Find project | **PASS** | owner-09 | |
| 19 Reopen study + persistence | **FAIL** | owner-09, owner-11 | **PRODUCT_FAILURE** — `/studies/new` + V1 study count |

### Shell blockers on production (still)

| Issue | Status |
|-------|--------|
| Marketing footer on app pages | Fix on PR #33 — **not deployed** |
| Raw archetype IDs | Fix on PR #33 — **not deployed** |
| Disconnected Financial tool | Banner + in-study continue path on PR #33 — **not deployed** |
| Always-new AI study link | Reopen wiring on PR #33 — **not deployed** |
| Assumptions → Financial → Risks → Decision → Report buttons | Journey nav + `/continue` on PR #33 — **not deployed** |

---

## 5) Known remaining blockers

**OWNER GATE: FAIL — not DONE.**

Fixes exist on PR #33 (shell, labels, reopen, journey continue panels, `/api/v2/studies/{id}/continue`) but are **not on production** until merge + deploy.

Do not claim DONE until a fresh production re-run shows PASS on steps 1–19 without workarounds.

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

After merging PR #33:

1. Repeat this script on production with a **new** account.  
2. Fill the PASS/FAIL table again.  
3. Gate flips to DONE only when every required step is **PASS**.
