# CR-2026-09-10 — V2 AI Study Semantic Recovery (Phase A)

Status: APPROVED  
Date: 2026-09-10  
Approver: Project owner via Cursor Phase A execution order  
Baseline: `0f60a678e1007ce090135d47c2be1df789e68e62`  
Branch: `feat/v2-ai-study-semantic-recovery`  
Related ADR: `0001-v2-evidence-assumption-semantic-separation`

## Product direction

Saudi Business is an AI-first autonomous feasibility platform. Manual data entry is an optional fallback, never the default journey. Preferred missing-information handling is **Research available information**; provisional estimates are a fallback; manual completion is optional for confidential/unavailable data. Primary product CTA direction: **Generate AI Study Draft / إنشاء مسودة دراسة بالذكاء الاصطناعي**. Human pauses remain limited to Profile, Evidence+Assumptions, and Final Decision gates.

## Change summary

Semantically repair V2 AI Study so Evidence is source-backed only and AI estimates are Assumptions only. Replace Confirm Profile with three explicit information-gate choices (Research preferred). Guard transitions. Add honest empty/degraded Evidence states and required item actions. Preserve PRs #16–#20 behavior that remains valid. Do not block Phases B–F autonomous research. Do not redesign into a manual form builder.

## Boundaries

- No production merge/deploy in Phase A.
- No CrewAI/Dify/Flowise/Langflow or second orchestrator.
- Do not stop/delete/merge Vercel projects `saudi-business-web` or `feasibilityos-ai`.
- Never manufacture Evidence.
- Do not redesign the product into a manual form builder.

## Implementation scope

Phase A only per `docs/execution/SAUDI_BUSINESS_V2_AI_RECOVERY_EXECUTION.md`.

## Exit criteria

Phase A acceptance gate plus AI-first CTA hierarchy:

- Research preferred among exception choices; primary CTA label direction is **Generate AI Study Draft / إنشاء مسودة دراسة بالذكاء الاصطناعي**.
- Manual path remains optional fallback, not the default journey.
- Implementation must not block Phases B–F autonomous research workflow.
- Acceptance tests encode AI-first principles (no synthetic Evidence; Research ≠ Manual ≠ Provisional).
