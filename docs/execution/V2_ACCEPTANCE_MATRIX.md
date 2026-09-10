# V2 AI Study Recovery — Acceptance Matrix

## BRANCH
`feat/v2-ai-study-semantic-recovery`

## HEAD
`a2a7c9d98d125fcf33dd3b567855b8060f5c81dc`

## PREVIEWS
- Frontend: https://saudi-business-cw6fnvld1-20262031.vercel.app
- Backend: https://feasibilityos-h37rxua9v-20262031.vercel.app
- Git aliases also available on the same Preview deployments

## AUTOMATED GATES
| Gate | Result |
|------|--------|
| Backend pytest (CI) | PASS |
| Migrations (CI Alembic) | PASS |
| Frontend typecheck | PASS |
| Frontend lint | PASS |
| Frontend build | PASS |
| Playwright golden A–D (local) | PASS |
| Preview AI API golden A–D (`vercel curl`) | PASS |
| Preview browser UI golden A–D (OIDC Trusted Sources) | PASS |

## GOLDEN SCENARIOS
| Scenario | Local Playwright | Preview API | Preview Browser |
|----------|------------------|-------------|-----------------|
| A WhatsApp AI SaaS | PASS | PASS | PASS |
| B Residential Complex | PASS | PASS | PASS |
| C Data Center | PASS | PASS | PASS |
| D Government Award | PASS | PASS | PASS |

## PHASES (browser + API evidence)
| Phase | Status | Evidence |
|-------|--------|----------|
| Classification | PASS | Archetype-specific question catalogs (11/13/10/12 cards) |
| Discovery structured UX | PASS | Interactive cards; no Markdown/JSON dump |
| Question UX | PASS | SINGLE/MULTI/NUMBER/CURRENCY/YES_NO controls |
| Information Gate | PASS | Research primary + provisional path executes |
| Evidence semantics | PASS | Provisional keeps Evidence empty; estimates → Assumptions |
| Assumptions + bulk approve | PASS | Approve Assumptions advances pipeline |
| Financial | PASS | Deterministic calc / MODEL_INCOMPLETE when needed |
| Scenarios | PASS | BASE/UPSIDE/DOWNSIDE + challenge API |
| Risks | PASS | Archetype-specific risks |
| Decision | PASS | Verdict with rationale |
| Readiness / Funding | PASS | Explained score + blockers via existing matcher |
| Report | PASS | Snapshot from persisted study state |
| Persistence | PASS | Refresh keeps study; locale toggle does not log out |
| Auth | PASS | Register/login on Preview via OIDC-protected routes |
| Arabic/English | PASS | Locale toggle on Preview |

## REUSED
- LangGraph orchestrator, existing agents, funding-engine matcher, reporting PDF helpers, V2 study API

## FIXED
- Structured discovery (no Markdown question dumps)
- Bulk assumption approval Option A
- Financial incomplete vs fake NPV=-CAPEX
- Decision incomplete guard
- Assumption previous_values history
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
**PENDING_PREVIEW_REVERIFY** (project-card V2 CTAs + previous_values test landed; Preview A–D re-run required on new HEAD)
