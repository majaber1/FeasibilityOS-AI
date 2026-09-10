# AI Feasibility Workflow Validation (Multi-Archetype)

**Status: NOT COMPLETE** — do not treat PR16 / single Uber financial success as done.

Validation branch: `cursor/validate-ai-feasibility-workflow-1831`  
Date: 2026-09-10  
Production API: `https://feasibilityos-ai.vercel.app`  
Artifacts: `/opt/cursor/artifacts/workflow-validation/`

---

## Verdict

| Gate | Result |
|------|--------|
| Uber financial after PR16 | PASS |
| Uber risk generated | FAIL (blocked — Groq TPD 429) |
| Uber verdict generated | FAIL (not reached) |
| Uber persistence after refresh (full pipeline) | PARTIAL (GET persists ANALYZED + financial; risk/verdict absent) |
| Residential discovery type-specific | PASS (`real_estate` / `real_estate_v1`, no SaaS markers) |
| Data center discovery type-specific | PASS (`data_center` / `data_center_v1`, no SaaS markers) |
| Residential full pipeline (assumptions→financial→risk→verdict) | NOT RUN (rate limit + incomplete by design until Uber risk clears) |
| Data center full pipeline | NOT RUN |
| Same SaaS questions on all project types | **FAIL on Uber/services**; PASS on RE+DC discovery |
| Overall workflow validated | **NO** |

---

## 1. Current architecture diagram

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  Web (saudi-business-web)                                                │
│  /projects/{id}/studies/{study_id}/workspace                             │
│  session cookie / Bearer → AI API                                        │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  FastAPI  backend/app/api/v2/study_engine.py                             │
│  POST /api/v2/studies          create + first discovery step             │
│  POST /api/v2/studies/{id}/message                                       │
│  POST /api/v2/studies/{id}/approve/{profile|evidence|assumptions}        │
│  GET  /api/v2/studies/{id}     hydrate / persistence                     │
│  Persist: StudyStateRow (JSON state + messages)                          │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  LangGraph orchestrator  ai_engine/orchestrator.py                       │
│  StateGraph(StudyState) — ONE node per HTTP step, then END               │
│                                                                          │
│  phase → node:                                                           │
│    DRAFT|UNDERSTANDING|NEEDS_INFORMATION → discovery                     │
│    EVIDENCE_REVIEW                       → evidence                      │
│    ASSUMPTIONS_REVIEW                    → assumptions                   │
│    READY_FOR_ANALYSIS                    → financial                     │
│    ANALYZED                              → risk                          │
│    DECISION_READY                        → decision                      │
│    FUNDING_READY                         → END                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent flow

```text
User description
    │
    ▼
[discovery]  classify archetype + missing_info + next_questions
    │  ARCHETYPE_QUESTIONS catalog ONLY for:
    │    saas_digital | real_estate | data_center
    │  EMPTY catalog for: services | retail | industrial | franchise
    │  User confirms profile (approve/profile) OR answers gaps
    ▼
[evidence]   extract claims / source_type
    │  User approves evidence
    ▼
[assumptions] generic prompt + "Project: {archetype}/{sector}" string
    │  User approves assumptions
    ▼
[financial]  LLM extract drivers → deterministic NPV/IRR/payback
    │  Fallback builder biased to marketplace (ATV × take_rate × rides)
    │  PR16 fixed str.format JSON brace crash
    ▼
[risk]       generic risk taxonomy (market/regulatory/ops/financial/external)
    ▼
[decision]   verdict + rationale + conditions + risks
    ▼
FUNDING_READY (terminal)
```

Each agent call uses Groq (`openai/gpt-oss-120b` for heavy steps). Shared org TPD quota gates all studies.

---

## 3. Data flow

```text
Project (POST /projects/)
  └─ study create {project_id, language, description}
       └─ StudyState
            profile {archetype, sector, stage, decision_goal, missing_information, recommended_model}
            claims[]
            assumptions[{key,value,low,base,high,confidence,source}]
            financial_results {capex, revenue_projections, cost_projections, npv, irr, scenarios, warnings}
            risks / decision_risks[]
            verdict, decision_rationale, decision_conditions
            phase, next_action, messages[], error
       └─ DB row keyed by study_id (reloadable via GET)
```

UI workspace hydrates from GET; approve endpoints mutate phase gates without re-running prior nodes incorrectly when `profile_confirmed`.

---

## 4. Live study evidence (production)

### A) Uber / Uper Ride — `study_7373f1139f96` (project 14)

| Field | Value |
|-------|-------|
| Account | `uber_ai_fill_1788980900@example.com` |
| Archetype / model | `services` / `general_v1` |
| Financial | YES — `analysis_complete=true`, NPV ≈ -12.17M SAR, CAPEX 5M |
| Assumptions | trip value, take-rate, rides, promo burn, driver CAC, fixed opex… |
| Risk | NO — `decision_risks=[]` |
| Verdict | NO — `null` |
| Persistence | GET returns ANALYZED + financial_results |
| Blocker | Groq TPD 429 (~40–45 min waits); risk message returns error on state |

Discovery `missing_information` included **“Customer Acquisition Cost (CAC) and Lifetime Value (LTV) assumptions”** — SaaS framing for a ride-hailing marketplace.

### B) Residential compound — `study_6c7b908df981` (project 20)

| Field | Value |
|-------|-------|
| Archetype / model | `real_estate` / `real_estate_v1` |
| Questions | land cost, BOQ, ASP, absorption, Wafi, financing, permits |
| SaaS markers (CAC/LTV/churn/MRR/subscription) | **none** |
| Pipeline past discovery | not completed (quota) |

### C) Data center — `study_11bc143d2d39` (project 21)

| Field | Value |
|-------|-------|
| Archetype / model | `data_center` / `data_center_v1` |
| Questions | $/kW/mo, occupancy ramp, power tariff, OPEX, Tier/permits, competitors |
| SaaS markers | **none** |
| Pipeline past discovery | not completed (quota) |

---

## 5. Failed scenarios

1. **Uber incomplete after PR16** — financial works; risk + verdict do not complete under shared Groq TPD; cannot claim end-to-end Uber success.
2. **Services archetype catalog gap** — `ARCHETYPE_QUESTIONS` has no `services` (or retail/industrial/franchise) entries → free-form LLM; Uber injected SaaS CAC/LTV language.
3. **`recommended_model` not enforced** — `general_v1` vs `real_estate_v1` / `data_center_v1` / `saas_v1` is a label; assumption/risk/decision prompts are archetype-agnostic; financial fallback hardcodes marketplace take-rate math.
4. **Cross-type full validation incomplete** — RE and DC discovery differ correctly, but assumptions/financial/risk/decision parity across three archetypes is unproven live.
5. **Operational single-tenant LLM quota** — one org TPD starves multi-study validation and production concurrency.

---

## 6. Required fixes (redesign, not cosmetic)

### Stop / redesign triggers (confirmed)

- Same SaaS *framing* appears for non-SaaS when archetype lacks a catalog (Uber/`services`).
- Downstream agents do not bind decision logic to project type beyond a context string.

### Required work

1. **Expand `ARCHETYPE_QUESTIONS`** for `services`, `retail`, `industrial`, `franchise` (and mobility/marketplace subcategory or map ride-hailing → dedicated set: take-rate, GMV, driver supply — not CAC/LTV SaaS).
2. **Bind assumption templates by `recommended_model`** — required keys per model (RE: land/BOQ/ASP/absorption; DC: MW/$/kW/PUE/occupancy; SaaS: ARPU/CAC/churn; marketplace: ATV/take-rate/rides).
3. **Financial model templates by archetype** — replace marketplace-only assumption→cashflow fallback with pluggable builders; reject wrong driver sets.
4. **Risk + decision catalogs by archetype** — TGA/driver supply vs Wafi/absorption vs interconnection/PUE, not one generic list.
5. **Enforce phase completeness** — do not surface ANALYZED as “AI fill done” without risk+verdict; expose pipeline checklist in UI.
6. **LLM capacity** — separate keys/tiers or queue so validation and production do not collapse on TPD 429.
7. **Automated multi-archetype golden tests** — assert question/assumption key sets differ; fail CI if SaaS markers appear on RE/DC studies.

---

## 7. What is explicitly NOT done

- Marking the AI feasibility workflow “complete”
- Accepting one Uber financial run as validation
- Full residential or data-center financial → risk → verdict → refresh evidence
- Proof that assumption/financial/risk/decision *logic* (not just discovery questions) diverges by type under live LLM

Next: when Groq TPD resets, finish Uber risk→verdict→refresh, then drive residential and data-center studies through the same gates and refresh the matrix.
