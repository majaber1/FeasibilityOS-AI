# Saudi Business — Feature Inventory & Verification Classification

## Document Control

- **Document ID:** SB-GOV-FEATURES-001
- **Title:** Feature Inventory & Verification Classification
- **Version:** GOV-0.1
- **Status:** DRAFT
- **Owner:** Project Governance Authority
- **Created Date:** 2026-09-06
- **Last Updated:** 2026-09-06
- **Related Requirements:** Requirements reconstruction pending
- **Related ADRs:** Architecture/CR review pending
- **Supersedes:** None
- **Change Summary:** Evidence-based feature inventory using the Master Governance verification taxonomy

---

## 1. Classification Rule

This governance-era inventory uses only the Master Governance statuses:

- `NOT_IMPLEMENTED`
- `PARTIAL`
- `IMPLEMENTED_NOT_VERIFIED`
- `VERIFIED_UNIT`
- `VERIFIED_INTEGRATION`
- `VERIFIED_WITH_MOCKS_ONLY`
- `VERIFIED_LIVE_E2E`
- `PRODUCTION_READY`
- `BLOCKED`
- `DEPRECATED`

The older locked `FEATURE_DELIVERY_CONTRACT.md` uses a different delivery vocabulary (`LOCAL_PASS`, `PREVIEW_PASS`, etc.). That historical contract is not rewritten. For this inventory, the governance taxonomy above is authoritative.

`PRODUCTION_READY` requires production-shaped evidence and is not inferred from code/tests/build success.

---

## 2. Evidence Baseline

Audited product-code baseline:

`0566ef527820b7f37240b4008ee8e68cc68e1d29`

Last user-run local verification available before governance adoption:

- focused financial health / borrowing capacity: 35 passed
- full backend regression: 530 passed
- frontend typecheck: PASS
- frontend lint: PASS
- frontend build: PASS

Repository contains browser journey scripts and historical browser evidence, but this inventory does not promote a capability to `VERIFIED_LIVE_E2E` merely because a script exists.

Final full-lifecycle browser certification is still open.

---

## 3. Cross-Cutting Foundation

| Capability | Status | Evidence / Reason |
|---|---|---|
| Registration / login backend | VERIFIED_INTEGRATION | Auth APIs and targeted auth tests exist. |
| HTTP-only web session proxy | VERIFIED_INTEGRATION | Current Next session login/proxy implementation is present; final production verification pending. |
| Project ownership authorization | VERIFIED_INTEGRATION | Server-derived owner authorization and ownership tests exist. |
| Project CRUD | VERIFIED_INTEGRATION | API + `/projects` UI + tests. |
| Project archive/restore | VERIFIED_INTEGRATION | API + UI + tests. |
| Permanent project workspace | VERIFIED_INTEGRATION | `/projects/{id}` route exists and loads persisted project/study. |
| Permanent study workspace | VERIFIED_INTEGRATION | `/projects/{projectId}/studies/{studyId}` route, ownership consistency and reload behavior exist. |
| Study optimistic concurrency revision | VERIFIED_INTEGRATION | `expected_revision` conflict behavior exists and is tested. |
| Full study/business snapshot versioning | PARTIAL | Assumption versions and revision exist; no complete study snapshot/history UX. |
| Full refresh/logout-login persistence across lifecycle | BLOCKED | Partial evidence exists but complete all-artifact certification is not complete. |
| Production deployment verification | BLOCKED | Production state not verified by this governance audit. |

---

## 4. Wave 1 — Professional Feasibility

| Capability | Status | Evidence / Reason |
|---|---|---|
| Project / idea record | VERIFIED_INTEGRATION | Persistent Project API/UI. |
| Business Profile | VERIFIED_INTEGRATION | Real `BusinessProfileTab` + persisted API. |
| Market Evidence registry / evidence items | VERIFIED_INTEGRATION | Dedicated evidence API/UI and tests exist. |
| Assumption provenance | VERIFIED_INTEGRATION | USER / EVIDENCE_DERIVED / AI_SUGGESTED / DEFAULT explicitly modeled. |
| Assumption versioning | VERIFIED_INTEGRATION | New version retires prior active row instead of overwrite. |
| Deterministic feasibility engine | VERIFIED_INTEGRATION | Deterministic calculator + persisted result + regression tests. |
| Assumptions-driven financial calculation | VERIFIED_INTEGRATION | `compute-from-assumptions` requires required assumptions and records versions used. |
| NPV / IRR / ROI / Payback presentation | VERIFIED_INTEGRATION | Real Financial Analysis workspace and local manual evidence. |
| Legacy three-step feasibility wizard | PARTIAL | Functional but architecturally/product-wise conflicting; hardcoded synthetic inputs and no back navigation. |
| Scenario engine backend | VERIFIED_INTEGRATION | Scenario service/model/tests exist in repository history/current schema. |
| Scenario customer workspace | PARTIAL | Visible `Scenarios` study tab currently falls back to generic notes. |
| Decision engine backend | VERIFIED_INTEGRATION | Dedicated decision API/service and tests exist. |
| Decision lifecycle UX | PARTIAL | Decision is not exposed as one clear canonical dedicated study navigation step in the inspected workspace. |
| Professional Arabic feasibility PDF | BLOCKED | Arabic PDF glyph rendering is broken with Helvetica; observed `nnnn`. |
| DOCX feasibility report | PARTIAL | Generation exists, but Arabic complex-script/font policy and full content quality are not production certified. |
| Reopenable immutable report history | PARTIAL | Report metadata exists; report bytes are regenerated and Report/Version tabs are placeholders. |
| Wave 1 overall | PARTIAL | Core deterministic feasibility works, but customer lifecycle/version/report defects prevent complete certification. |

---

## 5. Wave 2 — Funding Intelligence

| Capability | Status | Evidence / Reason |
|---|---|---|
| Company financial profile | VERIFIED_INTEGRATION | Dedicated API/model/tests. |
| Financial health | VERIFIED_INTEGRATION | Deterministic service/API; missing periods now explicit `NO_PERIODS_RECORDED`. |
| Funding gap | VERIFIED_INTEGRATION | Dedicated service/API/UI integration. |
| Borrowing capacity | VERIFIED_INTEGRATION | Deterministic service/API; missing periods return `INSUFFICIENT_DATA`. |
| Collateral profile | VERIFIED_INTEGRATION | Dedicated API/service/model. |
| Funding readiness | VERIFIED_INTEGRATION | Dedicated deterministic readiness service/API/UI. |
| Funding program registry | IMPLEMENTED_NOT_VERIFIED | 12-program structured registry exists; live source/rule freshness was not independently verified by this audit. |
| Funding deterministic matching | VERIFIED_INTEGRATION | Persistent funding UI/service/test coverage exists; semantics distinguish missing information. |
| Financing structure | VERIFIED_INTEGRATION | Dedicated service and workspace integration exist. |
| Legacy wizard funding matcher | PARTIAL | Separate simplified path includes hardcoded `has_technical_team=true`; not authoritative. |
| External lender/program production truth | BLOCKED | Requires live current-source verification and production evidence. |
| Wave 2 overall | PARTIAL | Strong implementation, but external source freshness and legacy-flow conflict prevent production certification. |

---

## 6. Wave 3 — Opportunities & Franchise

| Capability | Status | Evidence / Reason |
|---|---|---|
| Structured opportunity registry | VERIFIED_INTEGRATION | Service/data model/provenance logic exists. |
| Franchise opportunity support | VERIFIED_INTEGRATION | Registry/UI/browser scenario support exists. |
| Source provenance model | VERIFIED_INTEGRATION | Source owner, official URL, field provenance, verification states and data version exist. |
| Prevent client self-certification as VERIFIED_CURRENT | VERIFIED_INTEGRATION | Service rejects client/admin self-promotion. |
| Opportunity filtering/browse UI | VERIFIED_INTEGRATION | Real `/opportunities` workflow and browser script coverage exists. |
| Deterministic opportunity fit | VERIFIED_INTEGRATION | Dedicated matching service and tests. |
| Opportunity → Study lineage | VERIFIED_INTEGRATION | Study payload/UI lineage and source transfer implementation exist. |
| Browser golden journey artifact | IMPLEMENTED_NOT_VERIFIED | Playwright journey exists; current-audit execution against the current environment was not performed. |
| Demo seed opportunities/franchises | VERIFIED_WITH_MOCKS_ONLY | Explicitly labelled demo/illustrative; must remain test/demo only. |
| Live primary-source freshness | BLOCKED | Automated live primary-source verification is explicitly not active; audit did not independently verify external freshness. |
| Same-project full-lifecycle Wave 3 acceptance | BLOCKED | Final cross-wave certification remains open. |
| Wave 3 overall | PARTIAL | Real implementation exists, but live source and current full-lifecycle evidence are incomplete. |

---

## 7. Wave 4 — Validation OS

| Capability | Status | Evidence / Reason |
|---|---|---|
| Validation cycles | VERIFIED_INTEGRATION | Dedicated migration/service/API/UI/tests. |
| Validation hypotheses | VERIFIED_INTEGRATION | Real persisted model/workspace. |
| Evidence/result handling | VERIFIED_INTEGRATION | Real validation flow and evidence semantics. |
| Critical-hypothesis gating | VERIFIED_INTEGRATION | Guardrails exist and historical/current-cycle semantics were hardened. |
| GO / PIVOT / validation decisions | VERIFIED_INTEGRATION | Persisted decision behavior exists. |
| Real non-simulated evidence acceptance | BLOCKED | Test data cannot substitute for real external/customer evidence when certifying actual GO. |
| Complete current lifecycle browser proof | BLOCKED | Needs one uninterrupted current-commit acceptance journey. |
| Wave 4 overall | PARTIAL | Functional implementation exists; final real-evidence/live-lifecycle certification remains open. |

---

## 8. Wave 5 — Launch & Actuals

| Capability | Status | Evidence / Reason |
|---|---|---|
| Launch readiness/gating | VERIFIED_INTEGRATION | Dedicated service/API/UI/tests and validation decision linkage. |
| Launch milestones/tasks | VERIFIED_INTEGRATION | Persisted launch workspace capability exists. |
| Actual launch state/date | VERIFIED_INTEGRATION | Persisted lifecycle state exists. |
| Actual periods/metrics | VERIFIED_INTEGRATION | Actuals data model/service/UI exists. |
| Forecast vs Actual | VERIFIED_INTEGRATION | Service/UI implementation exists. |
| Variance analysis | VERIFIED_INTEGRATION | Deterministic handling exists; missing baseline is represented as unavailable. |
| Reforecast | VERIFIED_INTEGRATION | Persisted reforecast functionality exists. |
| Immutable linkage to approved study/version | PARTIAL | Full study snapshot/version model is incomplete. |
| Full refresh/relogin acceptance | BLOCKED | Cross-artifact persistence certification remains open. |
| Wave 5 overall | PARTIAL | Strong implementation but not production-certified as one lifecycle. |

---

## 9. Wave 6 — Growth OS

| Capability | Status | Evidence / Reason |
|---|---|---|
| Business Health | VERIFIED_INTEGRATION | Deterministic service/API/UI and missing-data states exist. |
| Growth scenarios / What-if | VERIFIED_INTEGRATION | Persisted scenario service/model/UI exists. |
| Risk detection | VERIFIED_INTEGRATION | Growth service/UI logic exists. |
| Funding context in growth | VERIFIED_INTEGRATION | Stale funding context issue was remediated in prior product baseline. |
| Growth decisions | VERIFIED_INTEGRATION | Persisted decisions linked to scenarios by migration `0024_wave6_integrity`. |
| Current validation cycle gating | VERIFIED_INTEGRATION | Newer current validation state prevents stale historical GO from incorrectly authorizing downstream action. |
| Decision chronology full browser proof | BLOCKED | Final full-lifecycle chronology verification remains open. |
| Wave 6 overall | PARTIAL | Implementation exists and is regression-tested, but final full lifecycle is not certified. |

---

## 10. AI / Knowledge / Agent Capabilities

| Capability | Status | Evidence / Reason |
|---|---|---|
| AI Advisor user experience | NOT_IMPLEMENTED | `Advisor` tab is generic notes; no governed live AI advisor path established. |
| Market AI agent | NOT_IMPLEMENTED | One-line conceptual agent doc only. |
| Financial AI agent | NOT_IMPLEMENTED | Deterministic engine exists; no governed AI agent implementation evidenced. |
| Risk AI agent | NOT_IMPLEMENTED | Conceptual doc only. |
| Funding AI agent | NOT_IMPLEMENTED | Funding is deterministic; conceptual agent doc is not implementation. |
| Document AI agent | NOT_IMPLEMENTED | Report generation is deterministic; no governed LLM document agent path evidenced. |
| Agent orchestration | NOT_IMPLEMENTED | No approved execution graph/budgets/observable production path established. |
| LLM provider/model wiring | NOT_IMPLEMENTED | No audited production AI provider path established in current product flow. |
| Prompt/version registry | NOT_IMPLEMENTED | No governed prompt version system evidenced. |
| AI run persistence/observability | NOT_IMPLEMENTED | No product-level AI-run trace established. |
| AI evaluation suite | NOT_IMPLEMENTED | No governed reusable AI quality evaluation established. |
| RAG execution pipeline | NOT_IMPLEMENTED | `knowledge-base/rag_pipeline.md` is conceptual only. |
| Knowledge Workspace | NOT_IMPLEMENTED | Cross-cutting capability is not started; it is not Wave 7. |

---

## 11. Security / Operations / Platform

| Capability | Status | Evidence / Reason |
|---|---|---|
| Same-origin authenticated backend proxy | VERIFIED_INTEGRATION | Implemented in Next route handler. |
| Basic request structured logging | VERIFIED_INTEGRATION | Request ID/status/duration logging exists. |
| In-process request metrics | VERIFIED_UNIT | Counters exist; no production metrics backend evidence. |
| Distributed observability/alerting | NOT_IMPLEMENTED | Not evidenced. |
| Cloudflare R2 document adapter | IMPLEMENTED_NOT_VERIFIED | Adapter exists; configuration/live environment unknown. |
| Backup/restore operational proof | NOT_IMPLEMENTED | No current recovery-test evidence established by audit. |
| Disaster recovery proof | NOT_IMPLEMENTED | No current DR-test evidence established by audit. |
| Production SLO/alerting | NOT_IMPLEMENTED | Governance operations baseline not yet created/approved. |
| Security production readiness | BLOCKED | Formal current threat model/security gate not yet complete. |

---

## 12. Governance Capability

| Capability | Status | Evidence / Reason |
|---|---|---|
| Master Governance Standard adoption | VERIFIED_INTEGRATION | Project-specific governance standard exists. |
| Current-state baseline | VERIFIED_INTEGRATION | Governance baseline document exists. |
| Workspace audit | IMPLEMENTED_NOT_VERIFIED | This audit document created; awaiting baseline approval. |
| Design review | IMPLEMENTED_NOT_VERIFIED | Design review created; awaiting baseline approval. |
| Feature inventory | IMPLEMENTED_NOT_VERIFIED | This inventory created; awaiting baseline approval. |
| Requirements reconstruction | NOT_IMPLEMENTED | Next governance activity. |
| Traceability matrix | NOT_IMPLEMENTED | Next governance activity. |
| Formal architecture baseline freeze | NOT_IMPLEMENTED | Cannot freeze before review/approval. |
| Governance manifest | NOT_IMPLEMENTED | Required later in existing-project baseline sequence. |
| Governance dashboard | NOT_IMPLEMENTED | Correctly deferred until baseline approval; not a current defect. |

---

## 13. Product-Level Acceptance Status

### Core findings

- The repository is no longer an empty/mock prototype; substantial persistent deterministic implementation exists.
- The product is not production ready.
- The main acceptance blocker is the coexistence of a modern persistent workspace with a legacy one-way feasibility wizard containing synthetic inputs and conflicting study semantics.
- Arabic reporting is not acceptable for production.
- AI is not currently a real governed product capability.
- External opportunity/funding truth requires current live verification before production claims.
- Final complete lifecycle E2E is still open.

### Overall classification

**Saudi Business overall: `PARTIAL`**

**Production readiness: `BLOCKED` / NO-GO**

No major wave or entire product is classified `PRODUCTION_READY` by this baseline inventory.

---

## 14. Next Governance Work

Before implementation remediation begins:

1. reconstruct functional/non-functional requirements and acceptance criteria
2. create traceability matrix
3. complete current-vs-target architecture review
4. create formal CR proposals for the critical findings
5. define remediation backlog and gate entry criteria
6. complete testing/security/operations/cost baselines
7. build governance manifest
8. present baseline approval package
9. STOP for approval

No product remediation is authorized by this feature inventory itself.
