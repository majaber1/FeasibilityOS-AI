# 0001 — V2 Evidence / Assumption Semantic Separation

Status: APPROVED  
Date: 2026-09-10  
Authority: Cursor Phase A execution order for Saudi Business V2 AI Study recovery  
Related CR: `CR-2026-09-10-v2-ai-study-semantic-recovery`

## Product Direction (locked)

Saudi Business is an **AI-first autonomous feasibility and business-decision platform**.
It must **not** become a manual feasibility-study form builder.

Primary journey:

1. User provides a short project description and optionally uploads documents.
2. AI classifies and understands the project.
3. AI creates and executes a research plan.
4. AI researches market, competitors, customers, pricing, regulations, sector benchmarks and official Saudi sources.
5. AI stores **only source-backed findings** as Evidence (citations, dates, authority metadata).
6. AI derives/proposes explicit Assumptions where verified data is unavailable.
7. Deterministic engines calculate the financial model and scenarios.
8. AI challenges results, identifies risks and composes the decision.
9. Funding is evaluated only after financial need is confirmed.
10. The system produces a versioned decision and feasibility report.

The user's normal role is limited to: Approve, Reject, Edit, Ask Why, Request Alternative, Regenerate, and upload private documents when public information is unavailable.

Governed human approval gates (only):

1. Project Profile approval
2. Evidence and Assumptions approval
3. Final Decision approval

Primary CTA (product direction for subsequent phases; Phase A preserves the direction):

- EN: **Generate AI Study Draft**
- AR: **إنشاء مسودة دراسة بالذكاء الاصطناعي**

Missing-information options are **exception-handling choices**, not the default product:

| Choice | Role |
|---|---|
| Research available information | **Preferred / default** |
| Create a provisional study using explicit estimates | Fallback when verified information is unavailable |
| Complete information manually | Optional path for confidential/unavailable data |

An unavailable provider must produce an honest degraded state. That is **not** the target successful outcome. Later phases must prove a functioning provider and research tools collect real source-backed evidence.

Phase A repairs Evidence/Assumption semantics **without** redesigning the product around manual data entry and **without** blocking the autonomous research workflow required in Phases B–F.

## Problem

After Confirm Profile, the V2 study engine stored AI-generated estimates as Evidence claims (`source_type=ai_assumption`), violating product trust rules and the Feature Delivery Contract. Users could not distinguish researched facts from planning estimates. The single Confirm CTA also blurred autonomous research with provisional estimation.

## Current Architecture

`SAUDI_BUSINESS_MASTER_ARCHITECTURE.md` separates Research/Evidence engines from Assumptions and requires provenance/trust governance. The V2 LangGraph path conflated the two by writing provisional estimates into `claims[]`.

## Reason Change Is Needed

Fitting Confirm-fill into Evidence without sources breaks the architecture’s trust layer. Replacing Confirm with three explicit gate choices — with Research as preferred — aligns V2 with Evidence vs Assumptions separation and the AI-first journey, without a second orchestration runtime.

## Proposed Change

1. Invariant: **NO SOURCE → NOT EVIDENCE**.
2. Remove synthetic Evidence fallback from the Evidence agent.
3. Persist `gate_choice` and `evidence_status` on V2 study state.
4. Information gate choices (exception handling around the AI-first flow):
   - `research` (**preferred/default**) → Evidence agent; source-backed claims only; empty/degraded if none
   - `provisional` (fallback) → Assumption agent; provisional assumptions only
   - `manual` (optional) → stay `NEEDS_INFORMATION`
5. Claim `source_type` limited to source-backed values; `ai_assumption` removed from Evidence.
6. Assumption gains `origin` including `provisional_estimate`, plus critical approval before continuing.
7. Continue LangGraph + PostgreSQL only.
8. Preserve autonomous research path for Phases B–F (no manual-form redesign).

## Alternatives

- Keep ai_assumption claims but hide them in UI — rejected.
- Second orchestration product — rejected.
- Make Manual the primary path — rejected (violates AI-first direction).
- Delete Confirm without research/provisional paths — rejected.

## Data Impact

Additive columns on `study_states_v2`: `gate_choice`, `evidence_status`, `workflow_meta_json`.

## API Impact

New `POST /api/v2/studies/{id}/information-gate`. Item-action endpoint for Edit/Approve/Reject/Regenerate/Ask Why/Request Alternative.

## Security Impact

No auth model change. Preserve session-cookie BFF. Ownership isolation unchanged.

## Migration Impact

Additive only. Feature-branch/preview first. No production migration in Phase A.

## Backward Compatibility

Ambiguous Confirm replaced by three choices with Research preferred. Old “Confirm fills Evidence with estimates” removed.

## Risks

- Empty/degraded Evidence may look broken until later phases add real research tools.
- Provisional studies may be mistaken for researched studies — mitigated by origin labeling.
- Over-emphasizing Manual would regress AI-first UX — mitigated by CTA hierarchy.

## Workflow requirements (Phases A–F continuity)

1. Default product journey remains autonomous research after a short description (+ optional uploads).
2. Phase A information-gate is exception handling around that journey; Research is preferred among the three choices.
3. Only three governed human approval gates may pause the workflow: Project Profile, Evidence+Assumptions, Final Decision.
4. Research path must remain callable and must never write non-source-backed rows into Evidence.
5. Phase A must not introduce APIs, UI flows, or model constraints that force manual form-building as the happy path for Phases B–F.
