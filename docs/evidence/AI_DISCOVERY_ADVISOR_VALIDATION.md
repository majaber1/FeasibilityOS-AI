# AI Discovery Advisor — Validation Evidence (Phase 5)

**Branch:** `cursor/ai-discovery-advisor-1831`  
**Baseline:** PR #24 merged into `main` (`76fc918`), Phase 5 rebased onto updated `main`  
**Date:** 2026-09-11

## Architecture (unchanged engines)

```
Existing Project Context
→ Existing Archetype / Variant
→ Discovery Question Generator (interview enrichment only)
→ Structured Answers (StudyState.structured_answers)
→ Existing Assumption Engine
→ Existing Financial / Risk / Decision / Report
```

**Did not create:** another classifier, assumption store, study state machine, or duplicate project context.

**Diff vs `main` (discovery-only):**
- `ai_engine/discovery/*` — interview enrichment
- `ai_engine/archetypes/questions.py` — thin hook to enrichment
- `ai_engine/agents/discovery.py` — gate on unanswered interview Qs (not static missing list)
- `backend/app/api/v2/study_engine.py` — `ai_estimates` + numeric poison rejection
- `apps/web/.../DiscoveryQuestionsPanel.tsx` + workspace wiring
- tests under `tests/test_discovery_*`

## Structured answers hygiene

- User answers written only when typed/selected.
- `Let AI estimate` marks `ai_estimated=true` on the question and **does not** write placeholder values into `structured_answers`.
- Numeric/currency/percent fields reject poison strings (`confirmed`, `ok`, …) and coerce numeric strings.
- Existing Assumption Engine fills estimated keys later (confidence / source / rationale).

## Mandatory SaaS browser vertical slice (gate)

Account: `saas_gate_*@example.com`  
Study: `study_534eae0de3e2` / project `335`  
URL: `/projects/335/studies/study_534eae0de3e2/workspace`

| Step | Result |
| --- | --- |
| Project + archetype `saas_digital` | Pass |
| AI Discovery Interview visible | Pass (`discovery-questions-panel`) |
| Flat Missing Information list absent | Pass (`missing-information-box` not shown) |
| One multi-choice answer | Pass (`acquisition_channels` → Paid ads) |
| One numeric answer | Pass (`target_customers` → 500) |
| One Let AI estimate | Pass (`pricing`) |
| Refresh persistence | Pass (answers + `ai_estimated` unchanged) |
| Assumptions → Financial → Risk → Decision | Pass |
| Final phase | **`REPORT_READY`** (`GO_WITH_CONDITIONS`, financial present) |
| Poison placeholders in structured answers | None |

### Screenshots

<img src="docs/evidence/ai-discovery-advisor/saas-gate-01-interview-no-missing-list.png" alt="SaaS interview; no missing-info list" />
<img src="docs/evidence/ai-discovery-advisor/saas-gate-02-multichoice.png" alt="SaaS multi-choice answer" />
<img src="docs/evidence/ai-discovery-advisor/saas-gate-03-numeric.png" alt="SaaS numeric answer" />
<img src="docs/evidence/ai-discovery-advisor/saas-gate-04-ai-estimate.png" alt="SaaS Let AI estimate" />
<img src="docs/evidence/ai-discovery-advisor/saas-gate-05-after-refresh.png" alt="SaaS after refresh persistence" />
<img src="docs/evidence/ai-discovery-advisor/saas-gate-06-assumptions.png" alt="SaaS assumptions review" />
<img src="docs/evidence/ai-discovery-advisor/saas-gate-07-report-ready.png" alt="SaaS REPORT_READY" />

Machine result: `docs/evidence/ai-discovery-advisor/saas-gate-result.json`

## Other archetypes (after SaaS gate)

All reached **`REPORT_READY`** with interview visible, missing-list absent, persistence OK, no poison answers:

| Scenario | Archetype | Final phase |
| --- | --- | --- |
| Professional / Cyber services | `services` (professional) | REPORT_READY |
| Residential real estate | `real_estate` | REPORT_READY |
| Data Center | `data_center` | REPORT_READY |
| Mobility (Uber) | `services` (mobility; drivers/trips/take_rate) | REPORT_READY |

Summary JSON: `docs/evidence/ai-discovery-advisor/discovery-other-archetypes-summary.json`

### Sample screenshots

<img src="docs/evidence/ai-discovery-advisor/discovery-professional-01-interview.png" alt="Professional services interview" />
<img src="docs/evidence/ai-discovery-advisor/discovery-real_estate-01-interview.png" alt="Real estate interview" />
<img src="docs/evidence/ai-discovery-advisor/discovery-data_center-01-interview.png" alt="Data center interview" />
<img src="docs/evidence/ai-discovery-advisor/discovery-mobility-01-interview.png" alt="Mobility interview" />
<img src="docs/evidence/ai-discovery-advisor/discovery-mobility-05-report.png" alt="Mobility REPORT_READY" />

## API / unit checks

- `tests/test_discovery_interview.py` — category packs + AI-estimate satisfaction
- `tests/test_discovery_advisor_api.py` — AI estimate advances phase + DB reload persistence
- Live A–E API pipeline also reached `REPORT_READY` (see `discovery-pipeline-A-E-summary.json`)

## Regression notes

- Static `missing-information-box` remains in code only as a legacy fallback when **not** in `NEEDS_INFORMATION` and no discovery questions exist.
- Primary NEEDS_INFORMATION UX is the AI Discovery Interview.
- Assumption / Financial / Risk / Decision agents were not redesigned.

## Verdict

Phase 5 Discovery Advisor is **browser-validated** for the mandatory SaaS vertical slice and for Professional, Real Estate, Data Center, and Mobility regressions. Ready for human review on PR #25.

## Supplemental interactive browser journeys

Additional manual browser journeys (beyond the Playwright gates) confirmed the same interview UX:

- Cyber / professional services: consultants–utilization–contracts questions; no mobility leakage
- Uber mobility: drivers–trips–take_rate questions; no professional-services leakage

<img src="docs/evidence/ai-discovery-advisor/discovery-cyber-interview.webp" alt="Cyber discovery interview" />
<img src="docs/evidence/ai-discovery-advisor/discovery-cyber-assumptions.webp" alt="Cyber assumptions" />
<img src="docs/evidence/ai-discovery-advisor/discovery-uber-interview.webp" alt="Uber discovery interview" />
<img src="docs/evidence/ai-discovery-advisor/discovery-uber-assumptions.webp" alt="Uber assumptions" />
