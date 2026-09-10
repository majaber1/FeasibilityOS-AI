# 0001 — V2 Evidence / Assumption Semantic Separation

Status: APPROVED  
Date: 2026-09-10  
Authority: Cursor Phase A execution order for Saudi Business V2 AI Study recovery  
Related CR: `CR-2026-09-10-v2-ai-study-semantic-recovery`

## Problem

After Confirm Profile, the V2 study engine stored AI-generated estimates as Evidence claims (`source_type=ai_assumption`), violating product trust rules and the Feature Delivery Contract (“never a faked AI result” for market evidence). Users could not distinguish researched facts from planning estimates.

## Current Architecture

`SAUDI_BUSINESS_MASTER_ARCHITECTURE.md` separates Research/Evidence engines from Assumptions and requires provenance/trust governance. Wave 1 Evidence is source-backed; Assumptions are planning inputs. The V2 LangGraph path conflated the two by writing provisional estimates into `claims[]`.

## Reason Change Is Needed

Fitting Confirm-fill into Evidence without sources breaks the architecture’s trust layer. Extending Confirm into three explicit gate choices aligns V2 with the locked Evidence vs Assumptions separation without introducing a second orchestration runtime.

## Proposed Change

1. Invariant: **NO SOURCE → NOT EVIDENCE**.
2. Remove synthetic Evidence fallback from the Evidence agent.
3. Persist `gate_choice` and `evidence_status` on V2 study state.
4. Information gate choices:
   - `manual` → stay `NEEDS_INFORMATION`
   - `research` → Evidence agent; source-backed claims only; empty/degraded if none
   - `provisional` → Assumption agent; provisional assumptions only; claims untouched/empty of estimates
5. Claim `source_type` limited to source-backed values for Evidence panels; `ai_assumption` removed from Evidence.
6. Assumption gains `origin` including `provisional_estimate`.
7. Continue LangGraph + PostgreSQL only.

## Alternatives

- Keep ai_assumption claims but hide them in UI — rejected (still pollutes Evidence counts/API).
- Second orchestration product (CrewAI/Dify/etc.) — rejected (locked architecture).
- Delete Confirm entirely without provisional path — rejected (users need estimate path as Assumptions).

## Data Impact

Additive columns on `study_states_v2`: `gate_choice`, `evidence_status`, `workflow_meta_json`. Existing `ai_assumption` claims filtered from Evidence on read/write; provisional path writes Assumptions instead.

## API Impact

New `POST /api/v2/studies/{id}/information-gate`. Profile approve no longer fabricates Evidence. Item-action endpoint for Edit/Approve/Reject/Regenerate/Ask Why/Request Alternative. Payload exposes `evidence_status` and assumption `origin`.

## Security Impact

No auth model change. Preserve session-cookie BFF. Ownership isolation unchanged.

## Migration Impact

Additive only. Preview/feature-branch first. Rollback drops new columns. No production migration in Phase A.

## Backward Compatibility

Ambiguous single Confirm button replaced by three choices. Old “Confirm fills Evidence with estimates” behavior intentionally removed.

## Risks

- Empty Evidence may look “broken” until copy explains degraded/empty honestly.
- Provisional studies may be mistaken for researched studies — mitigated by `origin=provisional_estimate` and UI labeling.
