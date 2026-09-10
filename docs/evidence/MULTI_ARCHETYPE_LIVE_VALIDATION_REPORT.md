# Multi-Archetype AI Feasibility — LIVE Validation Report

Generated: `2026-09-10T23:23:27.135196+00:00`
API: `https://feasibilityos-ai.vercel.app`
**Overall: PASS**

## Gate matrix

| Scenario | Classification | Type-adaptive assumptions | Financial | Risks | Verdict | Persistence | No SaaS bleed | Result |
|---|---|---|---|---|---|---|---|---|
| Uber / ride-hailing (services) | `services` | True | True | True | `NO_GO` | True | True | **PASS** |
| Residential real estate | `real_estate` | True | True | True | `NO_GO` | True | True | **PASS** |
| Data center | `data_center` | True | True | True | `NO_GO` | True | True | **PASS** |

## Uber / services
- Phase `REPORT_READY`, verdict `NO_GO`
- Assumptions: average_trip_value, take_rate, monthly_rides_year1, driver_acquisition_cost, promo_burn_pct, monthly_fixed_opex, initial_investment
- NPV: -4057142.86
- Risks (5): Regulatory licensing challenges under Vision 2030; Supply‑side acquisition of drivers/providers; Intense price wars eroding margins; Safety and insurance compliance requirements; Weak unit economics and insufficient cash runway
- Persistence stable: True

## Residential / real_estate
- Phase `REPORT_READY`, verdict `NO_GO`
- Assumptions: land_cost, construction_boq, unit_count, asp_per_unit, annual_absorption_units, sales_period_years, initial_investment
- Required coverage: {'land': True, 'construction_or_boq': True, 'units': True, 'sales': True, 'financing_or_investment': True}
- NPV: -788520863.7
- SaaS key hits: none

## Data center
- Phase `REPORT_READY`, verdict `NO_GO`
- Assumptions: it_load_mw, price_per_kw_month, year1_occupancy, year3_occupancy, year5_occupancy, pue, power_tariff_per_kwh, initial_investment, annual_opex_ex_power, rack_count, discount_rate, debt_pct, interest_rate
- Required coverage: {'mw': True, 'racks': True, 'utilization': True, 'pue': True, 'capex': True, 'opex': True}
- NPV: -946455883.75
- SaaS key hits: none

## Cross-study differentiation
- Uber vs residential assumptions differ: True
- Residential vs DC assumptions differ: True
- Uber vs DC assumptions differ: True

## Method notes
- Live GET×2 persistence checked per study.
- SaaS bleed judged on **current assumption keys + profile gaps** (not historical chat that may include “No CAC/LTV” disclaimers or pre-redesign Q&A).
- Evidence snapshots: `/opt/cursor/artifacts/workflow-validation/*_final.json` and `*_persistence.json`.
