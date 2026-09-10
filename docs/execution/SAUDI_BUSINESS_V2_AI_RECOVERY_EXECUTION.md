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

1. Separate Evidence and Assumptions across model, API, agents, UI, tests.
2. Remove synthetic Evidence fallback.
3. Replace ambiguous Confirm with:
   - Complete missing information myself → remain `NEEDS_INFORMATION`
   - Research available information → Evidence Agent, source-backed claims only
   - Create provisional study using estimates → Assumption Agent, provisional assumptions only
4. Guarded, persisted transitions; illegal jumps rejected.
5. Honest empty/degraded Evidence states.
6. Item actions: Edit, Approve, Reject, Regenerate, Ask Why, Request Alternative.
7. Preserve chat hydration, cookie auth, AR/EN session continuity.
8. Feature-branch only — no production merge.

## Later phases (do not start automatically)

Phase B+ reserved for deeper research tooling, funding readiness hardening, and production release authorization.

## Acceptance (Phase A)

Evidence contains no AI-generated assumptions; provisional estimates appear only under Assumptions; three choices behave differently; transitions persisted; E2E + provider-failure paths proven; preview evidence for both Vercel projects; production untouched.
