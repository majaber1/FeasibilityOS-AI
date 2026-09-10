# Saudi Business — V2 AI Study Recovery Execution

Status: PHASE A IN PROGRESS  
Baseline commit: `0f60a678e1007ce090135d47c2be1df789e68e62`  
Feature branch: `feat/v2-ai-study-semantic-recovery`  
Authority: Cursor Phase A execution order (2026-09-10)

## Related documents

- `docs/architecture/SAUDI_BUSINESS_MASTER_ARCHITECTURE.md` (locked)
- `docs/architecture/FEATURE_DELIVERY_CONTRACT.md` (locked)
- `docs/00-governance/SAUDI_BUSINESS_MASTER_GOVERNANCE_STANDARD.md`
- `docs/architecture/adr/0001-v2-evidence-assumption-semantic-separation.md`
- `docs/00-governance/change-requests/CR-2026-09-10-v2-ai-study-semantic-recovery.md`

## Deployment linkage (immutable)

| Vercel project | Responsibility |
|---|---|
| `saudi-business-web` | Next.js UI + BFF proxy `/api/backend` |
| `feasibilityos-ai` | FastAPI + LangGraph AI engine + PostgreSQL persistence |

Do not stop, delete, replace, or merge these projects.

## AI-first product principle

Saudi Business is an **AI-first autonomous** feasibility and business-decision platform.
It must not become a manual feasibility-study form builder.

Primary CTA direction (preserved for Phases B–F; Phase A does not replace the full autonomous draft yet):

- EN: **Generate AI Study Draft**
- AR: **إنشاء مسودة دراسة بالذكاء الاصطناعي**

Human pauses are limited to: (1) Project Profile approval, (2) Evidence and Assumptions approval, (3) Final Decision approval.
User actions otherwise: Approve, Reject, Edit, Ask Why, Request Alternative, Regenerate, upload private documents.

Missing-information options are **exception handling**, not the default product:

1. **Research available information** — preferred/default  
2. **Create a provisional study using explicit estimates** — fallback when verified data is unavailable  
3. **Complete information manually** — optional for confidential/unavailable data  

Unavailable providers → honest degraded Evidence. Degraded is not the target success outcome; later phases must prove real source-backed research.

## Critical invariant

```text
NO SOURCE → NOT EVIDENCE
```

AI-generated estimates, benchmarks, forecasts, defaults, and planning values are **Assumptions only**. They must never be stored, counted, or displayed as Evidence.

## Preserved working fixes

PRs #16–#20 remain in force: financial format safety, AI-filled payload hydration, Confirm advancement semantics (replaced by three-choice gate), session cookie auth on approve/hydrate.

## Locked runtime

- Orchestration: existing LangGraph only (no CrewAI/Dify/Flowise/Langflow/second runtime)
- Persistence: PostgreSQL `study_states_v2`
- Auth: HTTP-only session cookie via BFF

## Phase A — Semantic Repair (this branch)

Phase A preserves the AI-first product direction while repairing Evidence/Assumption semantics.
It must **not** redesign the product around manual data entry and must **not** block the autonomous research workflow required in Phases B–F.

1. Separate Evidence and Assumptions across model, API, agents, UI, tests.
2. Remove synthetic Evidence fallback.
3. Replace ambiguous Confirm with three **exception-handling** choices (Research preferred):
   - **Research available information** (preferred/default) → Evidence Agent, source-backed claims only; maps toward primary CTA **Generate AI Study Draft / إنشاء مسودة دراسة بالذكاء الاصطناعي**
   - **Create provisional study using estimates** (fallback) → Assumption Agent, provisional assumptions only
   - **Complete missing information myself** (optional) → remain `NEEDS_INFORMATION`
4. Guarded, persisted transitions; illegal jumps rejected. Human pauses remain limited to Profile, Evidence+Assumptions, and Final Decision.
5. Honest empty/degraded Evidence states (degraded ≠ target success).
6. Item actions: Edit, Approve, Reject, Regenerate, Ask Why, Request Alternative.
7. Preserve chat hydration, cookie auth, AR/EN session continuity.
8. Feature-branch only — no production merge.

## Later phases (do not start automatically)

Phases B–F implement and prove autonomous research tools that collect real source-backed market and competitor evidence. Phase A must leave the Research path and LangGraph orchestration unblocked for that work.

## Acceptance (Phase A)

Evidence contains no AI-generated assumptions; provisional estimates appear only under Assumptions; three choices behave differently with Research preferred in UX hierarchy; transitions persisted; E2E + provider-failure paths proven; AI-first principle documented in ADR/CR/workflow requirements/tests; preview evidence for both Vercel projects; production untouched; Research path remains open for Phases B–F.
