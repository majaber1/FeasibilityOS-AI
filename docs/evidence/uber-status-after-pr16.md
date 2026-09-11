# Uber study status after PR16 (updated)

- study_id: `study_7373f1139f96`
- phase: **ANALYZED**
- archetype: `services` / model `general_v1`
- financial generated: **YES** (analysis_complete=True, npv=-12170907.43, capex=5000000.0)
- risk generated: **NO** (decision_risks=0) — last attempt 2026-09-10T22:05Z still Groq TPD 429 (~44m)
- verdict generated: **NO** (`None`)
- persistence: GET reloads ANALYZED + financial; full-pipeline refresh N/A until risk/verdict
- SaaS leakage at discovery: CAC/LTV in missing_information

## Companion studies (discovery only so far)
- Residential `study_6c7b908df981`: real_estate / real_estate_v1 — land/BOQ/ASP — no SaaS markers
- Data center `study_11bc143d2d39`: data_center / data_center_v1 — kW/occupancy/power — no SaaS markers

## Overall
**NOT COMPLETE** — see docs/evidence/AI_FEASIBILITY_WORKFLOW_VALIDATION.md
