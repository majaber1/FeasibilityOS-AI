# Owner Acceptance Test — Saudi Business

**Gate:** OWNER TESTABILITY (binary PASS/FAIL — no completion percentages)  
**Production URL:** https://saudi-business-web.vercel.app  
**Production deploy SHA (at test):** `93e4d385ac0d1338d98b1ebc33cfb27f2071263e`  
**Shell + reopen fix PR:** https://github.com/majaber1/saudi-business/pull/33  
**Branch commit (fixes, not yet on production):** see latest on `cursor/phase65-product-ux-hardening-1831`  
**Test date (UTC):** 2026-09-12  
**Language:** Arabic (RTL)

**Single scenario:**

> أريد إنشاء شركة خدمات أمن سيبراني في الرياض تقدم خدمات MSSP للشركات

---

## 1) Production URL

https://saudi-business-web.vercel.app

---

## 2) Account

Create a fresh account on production (no shared seed account required):

1. Open https://saudi-business-web.vercel.app/register  
2. Enter name, email, password (≥8 chars, letter + number)  
3. Click إنشاء حساب  

Agent run used password pattern `OwnerGateTest9!` with a fresh email.

Login: https://saudi-business-web.vercel.app/login

---

## 3) Exact 10-minute owner script

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open production URL | App loads |
| 2 | Register or Login | Enter product (Dashboard/Projects) |
| 3 | Click **لوحة التحكم** | Dashboard opens |
| 4 | **المشاريع** → **إضافة مشروع** → enter idea text + budget → save | Project space opens |
| 5 | Confirm idea text visible | Same Arabic MSSP sentence shown |
| 6 | Click **دراسة جدوى بالذكاء الاصطناعي** | Study workspace opens |
| 7 | Confirm classification (friendly label only) → continue | No raw IDs like `saas_digital` / `data_center` |
| 8 | Complete AI Discovery (use **دع الذكاء الاصطناعي يقدر** where useful) | Interview completes |
| 9 | Review assumptions in study | Assumptions visible |
| 10 | Run **financial analysis inside the study** | NPV/IRR from study assumptions |
| 11 | View risks | Risks for this study |
| 12 | View decision | Decision for this study |
| 13 | Open report | Report for this study |
| 14 | Refresh browser | Progress still there |
| 15 | **خروج** | Logged out |
| 16 | Login again | Dashboard |
| 17 | Open **المشاريع** / recent projects | Same project listed (no pasted URL) |
| 18 | Continue AI study | Same study reopens |
| 19 | Confirm answers / assumptions / analysis / report still present | Persisted |

Screenshots from production run: `docs/evidence/owner-gate-screenshots/`

---

## 4) PASS/FAIL (production UI, 2026-09-12)

| Step | Result | Evidence | Classification if fail |
|------|--------|----------|------------------------|
| 1 Open URL | **PASS** | owner-01 | |
| 2 Register/Login | **PASS** | owner-01 | |
| 3 Dashboard | **PASS** | owner-02 / owner-09 | Marketing hero noise (not a hard fail) |
| 4 Create project | **PASS** | owner-03 | |
| 5 Idea visible | **PASS** | owner-03 | |
| 6 Start AI study | **PASS** | owner-04 / owner-05 | |
| 7 Archetype | **FAIL** | owner-05 | **PRODUCT_FAILURE** — raw IDs shown (`saas_digital`, `data_center`, `real_estate`, `services`) |
| 8 AI Discovery | **PASS** | owner-06 | Q7/7 + AI estimate CTA works |
| 9 AI Estimate | **PASS** | owner-06 | |
| 10 Assumptions | **FAIL** | — | **PRODUCT_FAILURE** — not reachable as clear next step in owner UI |
| 11 In-study financial | **FAIL** | owner-07 | **PRODUCT_FAILURE** — lands on standalone `/tools/financial` calculator |
| 12 Risks | **FAIL** | — | **PRODUCT_FAILURE** — not reachable |
| 13 Decision | **FAIL** | — | **PRODUCT_FAILURE** — not reachable |
| 14 Report | **FAIL** | — | **PRODUCT_FAILURE** — not reachable |
| 15 Refresh | **PASS** | owner-08 | In-session |
| 16 Logout | **PASS** | | |
| 17 Re-login | **PASS** | owner-09 | |
| 18 Find project | **PASS** | owner-09 | Project listed |
| 19 Reopen study + persistence | **FAIL** | owner-09, owner-11 | **PRODUCT_FAILURE** — AI study CTA pointed at `/studies/new`; dashboard showed 0 studies; workspace hang / new study instead of reopen |

### Shell blockers on production

| Issue | Evidence | Status |
|-------|----------|--------|
| Marketing footer on Projects / Project / Workspace | owner-03, owner-06, owner-10 | **PRODUCT_FAILURE** (fix in PR #33 AppChrome — not deployed) |
| Raw archetype IDs | owner-05 | **PRODUCT_FAILURE** (fix in PR #33 — not deployed) |
| Disconnected Financial tool | owner-07 | **PRODUCT_FAILURE** (banner in PR #33; in-study financial path still incomplete) |
| Always-new AI study link | owner-11 | **PRODUCT_FAILURE** (reopen wiring added on branch — not deployed) |

---

## 5) Known remaining blockers (OWNER GATE still FAIL)

1. **Study reopen after logout** — production still routes owners to `studies/new` and dashboard V1 study count ignores V2 AI studies.  
2. **Assumptions / Risks / Decision / Report** not proven as owner-reachable stages after Discovery.  
3. **Financial** still a standalone calculator unless used inside study financial tab.  
4. **Shell UX** (footer + raw IDs) fixed on branch, **not on production** until PR #33 merges and deploys.  

**OWNER GATE: FAIL — not DONE.**

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

After merging PR #33 (and any follow-up for assumptions/risks/decision/report navigation):

1. Repeat this script on production with a **new** account.  
2. Fill the PASS/FAIL table again.  
3. Gate flips to DONE only when every required step is **PASS**.
