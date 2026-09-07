# Saudi Business — Product / UX Design Review

## Document Control

- **Document ID:** SB-GOV-DESIGN-001
- **Title:** Product / UX Design Review
- **Version:** GOV-0.1
- **Status:** DRAFT
- **Owner:** Project Governance Authority
- **Created Date:** 2026-09-06
- **Last Updated:** 2026-09-06
- **Related Requirements:** Requirements reconstruction pending
- **Related ADRs:** Architecture review / CR package pending
- **Supersedes:** None
- **Change Summary:** Read-only design review focused on real customer journeys, editability, persistence, truth semantics and Arabic experience

---

## 1. Review Objective

Evaluate whether a real Saudi Business user can understand and operate the product without knowing the internal architecture.

This review focuses on the actual experience around:

`Register → Create Project → Create/Continue Study → Edit → Assumptions → Calculate → Validate → Decide → Launch → Growth → Reopen`

No design remediation is implemented by this review.

Severity values:

- `BLOCKER`
- `CRITICAL`
- `HIGH`
- `MEDIUM`
- `LOW`

---

## 2. Executive UX Finding

Saudi Business currently exposes **two competing mental models**:

1. A modern persistent `Project → Study Workspace` model.
2. A legacy `/feasibility/new` three-step wizard model.

The persistent workspace is aligned with the approved product architecture. The legacy wizard is not.

This duality is the primary reason a user can complete a calculation but then be unable to understand how to return, edit the project, edit the financial assumptions, or know whether "New Study" creates a new record or changes the existing one.

The product should have one canonical customer lifecycle, not two competing creation/edit models.

---

## 3. Journey Review

| Journey Step | Observed Experience | Severity | Assessment |
|---|---|---:|---|
| Register / Login | Real authentication flow exists; current web path uses HTTP-only session cookie through same-origin proxy. | MEDIUM | Functional architecture exists; production session behavior still needs final verification. |
| Create Project | `/projects` supports creation, but estimated investment is prefilled with `100000`. | HIGH | A business number should not appear as an unexplained default. |
| Open Project | Permanent `/projects/{id}` route exists. | LOW | Good improvement. |
| Edit Project | Edit exists on `/projects`, but project-detail workspace does not expose a clear edit action. | HIGH | Users reasonably expect project editing from the project itself. |
| Start / Continue Study | Project workspace reuses an existing study or creates one. | LOW | Correct direction. |
| Legacy New Study | `/feasibility/new` coexists and exposes different semantics. | CRITICAL | Competing flow creates user confusion and data-risk. |
| Business Profile | Real editable persisted form exists in study workspace. | MEDIUM | Capability exists but discoverability is poor. |
| Assumptions | Real add/version/retire behavior exists. | MEDIUM | Technically strong, but "edit" mental model is unclear. |
| Financial Inputs | Modern assumptions-based analysis exists, but legacy cash-flow inputs also exist. | CRITICAL | Two input models can produce different user expectations and provenance. |
| Calculate | Deterministic calculation works. | HIGH | Result quality depends on preventing synthetic/default inputs. |
| Results | Metrics are visible; old wizard has no back/edit path. | HIGH | Results are a dead end in the legacy flow. |
| Validation | Real workspace exists. | MEDIUM | Needs complete lifecycle certification with real evidence. |
| Decision | Backend capability exists, but dedicated visible study `Decision` navigation is not clearly represented as its own canonical tab in the inspected workspace. | HIGH | Decision needs clear lifecycle placement and version linkage. |
| Launch | Real Launch & Actuals component exists. | MEDIUM | Needs complete lifecycle certification. |
| Growth | Real Growth OS component exists. | MEDIUM | Needs complete lifecycle certification and state chronology verification. |
| Report | Visible study Report tab is a placeholder while download is exposed elsewhere. | CRITICAL | UI promises more than it delivers; Arabic output is broken. |
| Version History | Visible tab is a placeholder. | HIGH | Product architecture promises persistent version history. |
| Reopen / Refresh | Permanent study route restores study, but complete artifact-level refresh/logout-login persistence is not yet certified. | HIGH | Core SaaS requirement remains open. |

---

## 4. Detailed Findings

### DR-UX-001 — Two competing feasibility experiences

**Severity:** CRITICAL

**Observed:**

- `/projects/{id}/studies/{studyId}` is a persistent workspace.
- `/feasibility/new` is a standalone wizard.

**Impact:** Users do not know which flow is authoritative. Product behavior differs depending on how the study is entered.

**Required governance action:** CR proposal to establish one canonical study lifecycle and define legacy-route retirement/redirect/compatibility behavior.

---

### DR-UX-002 — Synthetic numbers look like customer data

**Severity:** CRITICAL

The legacy wizard preloads specific revenues, costs, investment, fixed-cost, variable-cost and discount-rate values.

Manual UAT confirmed these exact values were visible to the user even though the saved assumptions workspace had no assumptions.

**Impact:** Financial output can look authoritative even though the input did not come from the user or evidence.

**Required behavior:** Empty/unknown or explicitly labeled example placeholders; no silent numeric business assumptions.

---

### DR-UX-003 — Step circles imply navigation but are not clickable

**Severity:** HIGH

The 1/2/3 step indicators look navigable but are static list items.

There is no explicit Back/Edit action from cash-flow/results steps.

**Impact:** user reaches results and cannot correct an earlier mistake through the same flow.

---

### DR-UX-004 — "New Study" does not mean new study

**Severity:** CRITICAL

`resetWizard()` returns the UI to step 1 but retains project context and current field values.

The backend returns the existing study for a linked project because one-study-per-project behavior is enforced.

**Impact:** the user can believe a new study is being created while actually continuing/modifying/recalculating the existing record.

This is a destructive-confusion risk even though the backend idempotency prevents duplicates.

---

### DR-UX-005 — Project file is hidden in study terminology

**Severity:** HIGH

The real business profile is under the study workspace tab `ملف المشروع`.

A user naturally expects Project Profile to be accessible from the project page itself.

**Impact:** capability exists but appears missing.

---

### DR-UX-006 — Project edit exists in the wrong place only

**Severity:** HIGH

`/projects` contains a project edit form; `/projects/{id}` does not surface edit.

**Impact:** user must leave the project workspace to edit the project root record.

---

### DR-UX-007 — Assumption versioning is technically correct but not user-obvious

**Severity:** MEDIUM

Assumptions are versioned by posting a new value with the same key and retiring the old row.

The UI offers `Add assumption` and `Retire`, but no explicit `Edit` action that explains a new version will be created.

**Impact:** users may create duplicate keys accidentally or fail to understand history semantics.

---

### DR-UX-008 — Financial model has two competing input sources

**Severity:** CRITICAL

Modern workspace:

`Persisted StudyAssumptions → compute-from-assumptions → deterministic engine`

Legacy wizard:

`Hardcoded/preloaded cash-flow fields → step_2 JSON → compute`

**Impact:** two calculations can appear to be the same product feature while having different provenance, validation and version behavior.

---

### DR-UX-009 — Visible placeholder tabs overstate product completeness

**Severity:** HIGH

Tabs such as Advisor, Scenarios, Risks, Compliance & Licensing, Report and Version History currently render a generic notes field rather than their named capability.

**Impact:** users see a polished navigation structure and reasonably assume those functions are implemented.

**Required behavior:** real implementation, explicit `Not available / Planned`, or remove from production navigation until governed completion.

---

### DR-UX-010 — Source verification fallbacks fabricate certainty

**Severity:** CRITICAL

When opportunity lineage properties are missing, the UI may substitute:

- `VERIFIED_CURRENT`
- `1.0.0`
- `2026-09-04`

**Impact:** missing metadata can become fake provenance.

**Required behavior:** `UNKNOWN`, `NOT_AVAILABLE`, or hidden field with explicit missing-data state.

---

### DR-UX-011 — Legacy funding flow contains uncollected assumptions

**Severity:** HIGH

Legacy wizard funding matching sends `has_technical_team=true` without collecting that fact from the user.

**Impact:** funding ranking can be influenced by data not supplied by the user.

---

### DR-UX-012 — Report experience is not production quality in Arabic

**Severity:** CRITICAL

User-visible Arabic PDF output rendered Arabic labels/text as `nnnn`.

Code uses Helvetica for PDF even when Arabic shaping is enabled.

**Impact:** a core Arabic deliverable is unusable and undermines trust in the entire study.

---

### DR-UX-013 — Report history is implied but not operational

**Severity:** HIGH

Report metadata is written, but the feasibility download path generates fresh bytes each time. The visible Report/Version History workspace tabs are placeholders.

**Impact:** user cannot reliably reopen "the report used for decision X" as an immutable artifact.

---

### DR-UX-014 — Current project investment may be semantically ambiguous

**Severity:** HIGH

Project investment is displayed as budget and reused in several places, but its provenance/origin is not always visible.

**Impact:** user-entered estimate can visually resemble a verified funding need/official budget.

**Required behavior:** label project-level estimate as user input/assumption when that is its origin.

---

### DR-UX-015 — Lifecycle navigation is capability-oriented, not decision-oriented

**Severity:** MEDIUM

The study sidebar contains many technical/product sections but does not clearly guide a non-technical business owner through:

`What do I need to do now? → What is blocked? → What changed? → What decision can I make?`

**Impact:** users can see many tabs without understanding next action.

A future UX remediation should preserve architecture but improve lifecycle progression/status/navigation.

---

## 5. Arabic / Localization Review

### Positive

- Arabic-first labels exist broadly.
- Direction/alignment is considered in several UI/report paths.
- Arabic/English switching is built into core frontend components.

### Gaps

- PDF font coverage fails Arabic.
- Internal English domain/status codes are still visible in some areas (`business_decision`, `completed`, `UNKNOWN`, etc.).
- Some bilingual labels are technical rather than customer-oriented.
- Full RTL/accessibility keyboard/browser verification has not been established in this audit.

Arabic product quality: **PARTIAL / NOT PRODUCTION CERTIFIED**.

---

## 6. Empty, Loading and Failure States

### Positive patterns observed

- Many components expose explicit loading/error states.
- Funding financial-health/borrowing-capacity missing data now uses valid domain states rather than normal-navigation 404s.
- Business profile and assumptions expose save/error states.

### Gaps

- Placeholder tabs do not distinguish `not implemented` from `empty data`.
- Legacy wizard defaults eliminate empty-state truth and replace it with synthetic numbers.
- External source freshness failure/degradation is not uniformly exposed to the user across all data-driven capabilities.

---

## 7. Persistence / Reopen UX Review

The permanent study route is a significant improvement.

However a production SaaS workflow should let the user visibly answer:

- What study/version am I editing?
- What changed since the last calculation?
- Which assumptions produced this result?
- Which evidence supported the decision?
- Which version was approved for launch?
- Which actuals are being compared to which forecast?

Current UI only partially answers these.

Overall persistence UX: **PARTIAL**.

---

## 8. Proposed UX Acceptance Journey

After governance approval/remediation, the mandatory customer journey should be verified as one coherent path:

`Register → Create Project → Open Project → Edit Project → Open Existing Study → Edit Business Profile → Add/Edit Versioned Assumptions → Calculate → Review Versioned Result → Validate → Record Evidence → Decision → Launch → Actuals → Reforecast → Growth → Refresh → Logout/Login → Reopen Same Project/Study/Version Context`

Acceptance must include:

- no unexplained default business numbers
- no accidental duplicate/overwrite ambiguity
- no placeholder screen presented as completed capability
- no unexpected 4xx/5xx
- no critical console error
- persisted state after refresh and relogin
- source/evidence provenance remains truthful
- Arabic report renders correctly

---

## 9. Design Review Decision

**Current customer-experience readiness: NO-GO.**

The product contains substantial working capability, but the dual study flows, synthetic default inputs, misleading `New Study` semantics, placeholder tabs, provenance fallbacks and Arabic report failure are too material for production certification.

The correct next action is governed requirements/CR design, not ad-hoc UI patching.

No remediation was implemented in this review.
