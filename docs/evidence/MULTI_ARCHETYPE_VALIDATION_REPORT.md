# Multi-Archetype AI Feasibility Validation Report

**Overall: PASS**  
Generated: 2026-09-10  
API: `https://feasibilityos-ai.vercel.app`  
Evidence dir: `/opt/cursor/artifacts/workflow-validation/`

## Blocker handled (not a stop)

- Production primary model `openai/gpt-oss-120b` hit **Groq TPD 429**.
- Used configured fallback `GROQ_MODEL_FAST` / `openai/gpt-oss-20b`.
- Deployed agent context truncation (decision/risk/assumptions/financial) to avoid 413 TPM overflows on long threads.
- Added code-level 429→FAST fallback in `ai_engine/config.py`.
- Restored `GROQ_MODEL_PRIMARY=openai/gpt-oss-120b` after runs (fallback remains in code).

---

## Scenario results

| Scenario | Result | Classification | Financial | Risk | Verdict | Persistence | SaaS bleed |
|----------|--------|----------------|-----------|------|---------|-------------|------------|
| 1) Uber ride-hailing | **PASS** | `services` | YES | YES (3) | `NO_GO` | YES (2× GET) | N/A (marketplace drivers) |
| 2) Residential compound | **PASS** | `real_estate` | YES | YES (4) | `NO_GO` | YES | **none** |
| 3) Data center | **PASS** | `data_center` | YES | YES (9) | `DEFER` | YES | **none** |

---

## 1) Uber Ride-Hailing — PASS

- **Study:** `study_7373f1139f96`
- **Classification:** `services` / marketplace ride-hailing
- **Questions / gaps (discovery):** regulatory TGA, unit economics, driver/rider acquisition (not SaaS subscription pack as primary model)
- **Assumptions:** `initial_investment`, `average_trip_value`, `take_rate`, `monthly_rides_year1_average`, `promo_discount_burn`, `driver_acquisition_cost`, `monthly_fixed_opex`, `variable_cost_per_ride`, …
- **Financial:** `analysis_complete=true`, CAPEX present, NPV ≈ **-12.17M SAR**
- **Risks (persisted):**
  1. Regulatory licensing delay/denial (TGA)
  2. Financial runway exhaustion (promo burn / thin margins)
  3. Intense price competition from Careem/Uber
- **Verdict:** `NO_GO` — negative NPV / no payback under base case; critical risks uncured
- **Persistence:** refresh GET #1 and #2 both `DECISION_READY` / `NO_GO` / 3 risks / financial complete
- **Evidence:** `uber_e2e_final.json`, `uber_after_risk.json`, `uber_verdict_attempt.json`

## 2) Residential Real Estate — PASS

- **Study:** `study_6c7b908df981`
- **Classification:** `real_estate` / `real_estate_v1`
- **Questions:** land, BOQ, ASP, absorption, Wafi/permits, financing (not CAC/LTV/churn)
- **Assumptions:** `land_cost`, `construction_boq`, `soft_costs`, `unit_count`, `asp_per_unit`, `annual_absorption_units`, `contingency_pct`, `equity_pct`, `target_irr`, `discount_rate`
- **Financial:** complete (sell-through / construction model)
- **Risks:** 4 real-estate risks persisted
- **Verdict:** `NO_GO`
- **SaaS bleed:** **none**
- **Persistence:** stable across reopen GETs
- **Evidence:** `scenario_report.json` residential block; traces `trace_study_6c7b908df981_*.json`

## 3) Data Center — PASS

- **Study:** `study_11bc143d2d39`
- **Classification:** `data_center` / `data_center_v1`
- **Assumptions:** `it_load_mw`, `price_per_kw_month`, `year1/3/5_occupancy`, `pue`, `power_tariff_per_kwh`, `initial_investment`, `annual_opex_ex_power`, `rack_count`, `debt_pct`, `interest_rate`, …
- **Financial:** `analysis_complete=true`, CAPEX 900M, NPV ≈ **-946M SAR**, IRR ≈ **-76.6%**
- **Risks:** 9 infrastructure risks persisted
- **Verdict:** `DEFER`
- **SaaS bleed:** **none**
- **Persistence:** stable `DECISION_READY` / `DEFER` / 9 risks / financial complete
- **Evidence:** `datacenter_e2e_final.json`

---

## Cross-archetype differentiation (required)

| Driver family | Uber | Residential | Data center |
|---------------|------|-------------|-------------|
| Land / BOQ / units / ASP / absorption | no | **yes** | no |
| MW / kW price / PUE / racks / occupancy | no | no | **yes** |
| Take-rate / trips / promo burn | **yes** | no | no |
| SaaS CAC/LTV/MRR pack | no (as primary model) | **absent** | **absent** |

Workflow **does** change questions, assumptions, financial drivers, risks, and decision framing by project type.

---

## Code changes supporting validation

- `ai_engine/archetypes.py` — catalogs for services/retail/industrial/franchise + RE/DC/SaaS
- Agents bound to catalogs (discovery/assumptions/risk/decision)
- Financial deterministic builders for RE + DC (not marketplace-only)
- Groq 429 → FAST fallback wrapper
- Truncated LLM context on decision/risk/assumptions/financial explain paths
