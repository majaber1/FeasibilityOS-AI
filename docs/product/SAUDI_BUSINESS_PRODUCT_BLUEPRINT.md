# Saudi Business — Launch, Decision & Funding OS

Positioning update as of 2026-09-02. Supersedes the "feasibility wizard"
framing in earlier docs; does not replace `docs/architecture/CURRENT_STATE_AUDIT.md`,
which remains the authoritative implementation-state record.

## What this product is

Not a feasibility-study generator, an AI chat interface, a PDF generator, or
a static funding directory. Saudi Business is the persistent workspace where
a Saudi entrepreneur or company answers, in order:

هل الفكرة تستحق التنفيذ؟ · كم سيكلف المشروع؟ · ما الافتراضات الحساسة؟ · ماذا
يحدث في السيناريو المحافظ؟ · هل المشروع قابل للتمويل؟ · كم يمكن أن أتحمل من
تمويل؟ · كم فجوة التمويل؟ · ما أفضل هيكل تمويلي؟ · ما البرامج أو الجهات
الأقرب لحالتي؟ · لماذا أنا مؤهل أو غير مؤهل؟ · ما الضمانات أو البيانات
الناقصة؟ · ما التراخيص المطلوبة؟ · ما الذي أفعله بعد ذلك؟

## Canonical journey

```
IDEA / EXISTING BUSINESS → UNDERSTAND → VALIDATE → STUDY → EVIDENCE →
ASSUMPTIONS → FINANCIAL MODEL → SCENARIOS → DECISION → FUNDING CAPACITY →
FUNDING READINESS → FUNDING MATCHING → FINANCING STRUCTURE → LICENSING →
ACTION PLAN → REPORT → VERSION HISTORY
```

Every step is a persistent record under the existing `Project → Study`
aggregate (`docs/architecture/CURRENT_STATE_AUDIT.md`), not a wizard step
that disappears on refresh.

## Four entry points, one architecture

All four converge into the same `Project`/`Study`. None re-collects data the
system already has.

1. **لدي فكرة مشروع** ("أنا أفكر بمشروع حضانة أطفال في الرياض") — one
   sentence → Quick Idea Check → Business Profile → Project → Study →
   Evidence → full feasibility.
2. **أريد دراسة جدوى** — user already knows activity/location/investment/
   customer → Business Profile → Project → Study → Evidence → Assumptions →
   Financial Model → Scenarios → Decision.
3. **أبحث عن تمويل** — planned or existing business → reuse stored profile/
   study data → Funding Readiness → Funding Gap → Eligibility → Matches.
4. **لدي شركة وأريد تمويل مشروع أو توسع** — the major differentiator.
   Existing company financials/documents/collateral in → structured
   extraction → Company Financial Profile → Financial Health → Project
   Feasibility → Borrowing Capacity → Collateral Profile → Funding Gap →
   Funding Readiness → Lender/Program Matching → Recommended Financing
   Structure → Application Readiness.

## Benchmarks (patterns only, never content/branding)

- **LivePlan** — feasibility workflow, financial forecasting, scenario
  planning, plan-vs-assumptions thinking, persistent business workspace.
- **Lendio** — funding readiness, qualification, lender/program matching,
  explaining *why* a match applies, not re-asking for known data.
- **Saudi official ecosystem** — GASTAT, Saudi Open Data, Saudi Business
  Center, Ministry of Commerce, ZATCA, Monsha'at, HRSD, MISA, MODON, Balady,
  sector regulators — authoritative source for evidence, licensing, and
  funding-program facts. Never fabricated; see `app/services/source_registry.py`.

## Non-negotiable rules

- **AI is not the source of truth.** It clarifies, extracts, classifies,
  explains, summarizes, flags gaps, suggests (labeled) assumptions. It never
  invents financial facts, Saudi statistics, funding eligibility, collateral
  values, lender policy, or regulations, and never calculates authoritative
  financial metrics.
- **Calculations are deterministic**, implemented in code
  (`financial-engine/`, `backend/app/services/`), not by an LLM. Same input
  → same output, always.
- **Funding results are estimates, not approvals.** Use
  `ESTIMATED_CAPACITY / POTENTIALLY_ELIGIBLE / POSSIBLY_ELIGIBLE /
  NEEDS_INFORMATION / NOT_ELIGIBLE / REQUIRES_LENDER_UNDERWRITING` — never
  "you are approved."

## Domain model — target vs. implemented

```
Project
 └── Study
      ├── Business Profile            [missing]
      ├── Company Financial Profile   [missing]
      ├── Uploaded Documents          [partial — Document model exists, no extraction]
      ├── Extracted Financial Facts   [missing]
      ├── Quick Idea Check            [missing]
      ├── Evidence                    [DONE — evidence_items + source registry]
      ├── Assumptions                 [DONE — study_assumptions, versioned]
      ├── Financial Model             [partial — deterministic engine exists, not
      │                                 wired to Assumptions]
      ├── Scenarios                   [partial — SensitivityScenario model exists
      │                                 but uses blanket % deltas, not explicit
      │                                 assumption overrides; needs replacing]
      ├── Decision                    [missing]
      ├── Funding Capacity            [missing]
      ├── Collateral Profile          [missing]
      ├── Funding Readiness           [missing]
      ├── Funding Matches             [partial — FundingProgram/FundingMatch exist,
      │                                 scoring is a simple heuristic, not the
      │                                 rule-trace model in Phase 19]
      ├── Financing Structure         [missing]
      ├── Licensing                   [missing — MultazimRequirement is a
      │                                 different, GRC-facing product]
      ├── Action Plan                 [missing]
      ├── Reports                     [partial — PDF/DOCX export exists, not
      │                                 persisted as a reopenable artifact,
      │                                 Arabic shaping unreliable]
      └── Version History             [partial — study.revision is optimistic
                                        concurrency only, no snapshot history]
```

Introduce remaining entities in dependency order with additive migrations;
never rewrite `0001`–`0010`.

## Implementation order

Phase numbers match `SAUDI_BUSINESS_PHASED_AUTONOMOUS_IMPLEMENTATION_PROMPT_V2`
(0–29): baseline → blueprint (this doc) → quick idea check → business
profile → document intake → company financial profile → evidence (done) →
source authority (done) → assumptions (done) → workspace integration
(partial) → deterministic feasibility engine hardening → company financial
health → scenarios (rebuild) → decision → funding gap → borrowing capacity →
collateral → funding readiness → verified funding programs → funding
matching → financing structure → licensing → AI advisor → action plan →
Arabic report → report persistence → version history → golden journeys →
production validation.
