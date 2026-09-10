# V2 AI Study Recovery — Acceptance Matrix

## BRANCH
`feat/v2-ai-study-semantic-recovery`

## HEAD
`46fc635fe781251fc542c70c9fce3e1f99008cc9`

## PREVIEWS
- Frontend: https://saudi-business-3qb1q8okc-20262031.vercel.app
- Backend: https://feasibilityos-7hgy5kqgb-20262031.vercel.app
- Branch alias: https://saudi-business-web-git-feat-v2-ai-study-semanti-592752-20262031.vercel.app

## AUTOMATED GATES
| Gate | Result |
|------|--------|
| Backend pytest (CI) | PASS (local V2 suites 68/68; CI subscribed on branch) |
| Migrations (CI Alembic) | PASS |
| Frontend typecheck | PASS |
| Frontend lint | PASS |
| Frontend build | PASS |
| Playwright golden A–D (local) | PASS |
| Preview AI API golden A–D (OIDC) | PASS on this HEAD |
| Preview browser UI golden A–D (OIDC Trusted Sources) | PASS on this HEAD |
| Assumption `previous_values` API test | PASS |
| Project-card V2 phase CTA wiring | PASS (source + Preview journey uses projects → workspace CTA) |

## GOLDEN SCENARIOS
| Scenario | Local Playwright | Preview API | Preview Browser |
|----------|------------------|-------------|-----------------|
| A WhatsApp AI SaaS | PASS | PASS | PASS (11 question cards) |
| B Residential Complex | PASS | PASS | PASS (13 question cards) |
| C Data Center | PASS | PASS | PASS (10 question cards) |
| D Government Award | PASS | PASS | PASS (12 question cards) |

## PHASES (browser + API evidence)
| Phase | Status | Evidence |
|-------|--------|----------|
| Classification | PASS | Archetype-specific catalogs (A11/B13/C10/D12) |
| Discovery structured UX | PASS | Interactive cards; no Markdown/JSON dump |
| Question UX | PASS | SINGLE/MULTI/NUMBER/CURRENCY/YES_NO controls |
| Information Gate | PASS | Research primary + provisional path executes |
| Evidence semantics | PASS | Provisional keeps Evidence empty; estimates → Assumptions |
| Assumptions + bulk approve | PASS | Approve Assumptions advances pipeline |
| Financial | PASS | Deterministic calc / MODEL_INCOMPLETE when needed |
| Scenarios | PASS | BASE/UPSIDE/DOWNSIDE + challenge API |
| Risks | PASS | Archetype-specific risks |
| Decision | PASS | Verdict with rationale / NEED_MORE_VALIDATION when incomplete |
| Readiness / Funding | PASS | Explained score + blockers via existing matcher |
| Report | PASS | Snapshot from persisted study state |
| Persistence | PASS | Refresh keeps study; locale toggle does not log out |
| Auth | PASS | Register/login on Preview via OIDC-protected routes |
| Arabic/English | PASS | Locale toggle on Preview |
| Project cards | PASS | Primary CTA phase-aware via `listV2Studies` + `v2StudyPrimaryAction` |

## REUSED
- LangGraph orchestrator, existing agents, funding-engine matcher, reporting PDF helpers, V2 study API

## FIXED
- Structured discovery (no Markdown question dumps)
- Bulk assumption approval Option A
- Financial incomplete vs fake NPV=-CAPEX
- Decision incomplete guard
- Assumption previous_values history (+ dedicated API test)
- Radar nav rename + project card primary actions (V2 phase-aware Start/Continue/Review Assumptions/Continue Financial/Review Decision)
- Preview browser access via Vercel OIDC Trusted Sources header

## NEW
- `discovery_catalog.py`, `DiscoveryQuestionsPanel`, funding/report/scenarios V2 agents, golden Playwright matrix, Preview browser golden script

## ARCHITECTURE DEVIATIONS
- None intentional beyond wiring existing engines into V2 phases (no duplicate calc engines)

## REMAINING DEFECTS
- Sticky navbar can visually overlay mid-page content in full-page screenshots (cosmetic)
- Live research still depends on provider availability (provisional path is deterministic fallback)
- Some Preview env secrets cannot be pulled locally (expected); OIDC Trusted Sources used for automation

## FINAL STATUS
**ACCEPTED**

### Preview re-verify evidence (this HEAD)
- API log: `/opt/cursor/artifacts/preview-api-golden-ABCD.log` + `preview-api-golden-ABCD.json` (A–D PASS)
- Browser logs: `/opt/cursor/artifacts/preview-ui-golden-A.log` … `preview-ui-golden-D.log` (all PASS)
- Screenshots: `/opt/cursor/artifacts/preview-ui-A-*.png` … `preview-ui-D-*.png`
- Preview JS bundle contains `listV2Studies` / `v2StudyPrimaryAction` / `reviewAssumptions` / `continueFinancial`
- CI on HEAD: Backend tests, Alembic, Frontend build, secret scan, Docker Compose — all PASS
