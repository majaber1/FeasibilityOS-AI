# Archetype-specific assumption schemas

## Problem
Assumption collection previously used SaaS questions (CAC, churn, ARR/MRR) for every project.

## Architecture
1. **Mandatory archetype classification** (`ARCHETYPE_CLASSIFICATION`) before assumptions.
2. **Archetype schemas** in `ai_engine/archetypes/` (`saas_digital`, `real_estate`, `data_center`, `industrial`, `retail`, `services`, `other`).
3. **Structured questions** (yes/no, select, numeric) generated from each schema.
4. **Assumption agent** fills only schema keys; AI fills are labeled `AI Estimated Assumption` / `ai_estimated=true`.
5. **Anti-leakage gate** strips SaaS keys from non-SaaS archetypes.
6. **Review gate** stays on `ASSUMPTIONS_REVIEW` until user approves / edits / regenerates.

## Flow
`DRAFT → ARCHETYPE_CLASSIFICATION → NEEDS_INFORMATION (structured Qs) → EVIDENCE_REVIEW → ASSUMPTIONS_REVIEW → READY_FOR_ANALYSIS → ANALYZED → DECISION_READY → REPORT_READY`

## API
- `POST /api/v2/studies/{id}/archetype`
- `POST /api/v2/studies/{id}/structured-answers`
- `POST /api/v2/studies/{id}/assumptions/edit`
- `POST /api/v2/studies/{id}/assumptions/regenerate`
- `POST /api/v2/studies/{id}/approve/{archetype|profile|evidence|assumptions}`

## DB
Migration `0026_archetype_schemas` adds:
- `discovery_questions_json`
- `structured_answers_json`
- `assumptions_version`

## Golden scenarios
| Scenario | Archetype | Variant | Expected keys |
|---|---|---|---|
| Cybersecurity / MSSP / consulting | `services` | `professional` (default) | consultants_headcount, utilization_rate, active_contracts, monthly_recurring_contracts, delivery_cost_monthly, gross_margin |
| Uber ride-hailing | `services` | `mobility` | take_rate, monthly_trips, drivers, driver_cac |
| Residential compound | `real_estate` | — | land_cost, construction_boq, units, selling_price, absorption_rate, financing |
| Data center | `data_center` | — | mw_capacity, rack_count, pue, occupancy, power_cost, capex_total |

Default `services` schema is **professional**. Mobility keys appear only when `services_variant=mobility` (ride-hailing / marketplace supply signals).
