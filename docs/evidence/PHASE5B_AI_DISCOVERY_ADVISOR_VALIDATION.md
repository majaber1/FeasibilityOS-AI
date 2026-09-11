# Phase 5B — AI Discovery Advisor Acceptance Validation

**Status:** READY TO MERGE  
**Date:** 2026-09-11  
**PR:** https://github.com/majaber1/saudi-business/pull/25  
**Branch:** `cursor/ai-discovery-advisor-1831`  
**Commit:** `7b8183de94b2acd065c875ca95928d90a0a160e8`  
**Baseline:** Phase 5A on `main` (`046c4d64096be17c6665e26375ef7e24b70f59d5`) is an ancestor  
**Preview:** https://saudi-business-m3b0pce3x-20262031.vercel.app  
**Method:** Fresh account per scenario, Playwright against local `http://127.0.0.1:3000` → API `:8000` on PR branch code

## Scope

Validate AI Discovery Advisor on the real user path only. No architecture redesign. No new engines.

Flow exercised:

Project → Archetype classification → **AI Discovery Advisor** → Assumptions Review → Financial → Risk → Decision → **REPORT_READY**

## Mandatory checks (all scenarios)

| Check | Result |
| --- | --- |
| Flat “Missing Information” list absent on interview path | PASS (`no_flat_missing_list`) |
| No raw JSON / tool / prompt leakage | PASS |
| No provider / org / model / billing leakage | PASS |
| No SaaS leakage into RE / DC | PASS (residential=`real_estate`, datacenter=`data_center`) |
| No mobility → data_center | PASS (uber=`services`) |
| Refresh + logout/login persistence | PASS (SaaS) |
| Arabic / English smoke | PASS (Uber) |

## Scenario results

| # | Scenario | Suggested archetype | Confirmed | Discovery interview | AI estimate | Manual answer | Assumptions | REPORT_READY | Leaks | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | SaaS AI compliance | `saas_digital` | `saas_digital` | PASS | PASS | PASS | PASS | PASS | 0 | **PASS** |
| B | Cybersecurity MSSP | `services` | `services` | PASS | PASS | soft* | PASS | PASS | 0 | **PASS** |
| C | Residential compound 500 | `real_estate` | `real_estate` | PASS | PASS | PASS | PASS | PASS | 0 | **PASS** |
| D | 20MW data center | `data_center` | `data_center` | PASS | PASS | PASS | PASS | PASS | 0 | **PASS** |
| E | Uber / mobility | `services` | `services` | PASS | PASS | soft* | PASS | PASS | 0 | **PASS** |

\* Cyber and Uber completed discovery primarily via “Let AI estimate” on numeric cards; interview submitted and journey continued. Not a blocker.

Machine JSON: `docs/evidence/phase5b-ai-discovery-advisor/phase5b_acceptance_results.json`

## Persistence (SaaS)

- Refresh after REPORT_READY: phase retained (`التقرير جاهز` / Report Ready) — PASS  
- Logout / login resume to same study: phase retained — PASS  

Screenshots: `p5b-saas-05-refresh.png`, `p5b-saas-06-relogin.png`

## Arabic / English (Uber)

- Arabic UI characters visible after language switch — PASS (`p5b-uber-07-arabic.png`)  
- English restored — PASS (`p5b-uber-08-english.png`)

## Representative screenshots

| Evidence | File |
| --- | --- |
| SaaS interview (no missing list) | `docs/evidence/phase5b-ai-discovery-advisor/p5b-saas-interview.png` |
| SaaS AI estimate | `docs/evidence/phase5b-ai-discovery-advisor/p5b-saas-ai-estimate.png` |
| SaaS assumptions | `docs/evidence/phase5b-ai-discovery-advisor/p5b-saas-assumptions.png` |
| SaaS report | `docs/evidence/phase5b-ai-discovery-advisor/p5b-saas-report.png` |
| Cyber interview / report | `p5b-cyber-interview.png`, `p5b-cyber-report.png` |
| Residential interview / report | `p5b-residential-interview.png`, `p5b-residential-report.png` |
| Data center interview / report | `p5b-datacenter-interview.png`, `p5b-datacenter-report.png` |
| Uber interview / report / AR / EN | `p5b-uber-interview.png`, `p5b-uber-report.png`, `p5b-uber-07-arabic.png`, `p5b-uber-08-english.png` |

## Known limitations

1. Some service journeys (Cyber, Uber) may complete discovery mostly with AI estimates when cards are numeric-first; manual select still verified on SaaS / Residential / Data Center.
2. Acceptance E2E ran against local branch stack (web `:3000` + API `:8000`) matching PR commit; Vercel preview is deployed for the same commit.
3. Unrelated CI noise: `Vercel – feasibilityos-ai` may fail (separate app); required saudi-business checks are green.

## Final verdict

All five browser journeys reached **REPORT_READY** with Discovery Advisor on the real path, no flat Missing Information list, no provider/internal leakage, persistence and AR/EN smoke PASS.

**FINAL STATUS: READY TO MERGE**
