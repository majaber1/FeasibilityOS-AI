# Final decision-loop validation (Uber / services)

**Status: PASS**  
**Study:** `study_7373f1139f96`  
**Workspace:** https://saudi-business-web.vercel.app/projects/14/studies/study_7373f1139f96/workspace  
**Captured:** 2026-09-10

This run proves the human-in-the-loop path: challenge assumption → recalc financials → update verdict → persist report.

---

## 1. Previous state (assumptions_version = 1)

| Field | Value |
|-------|-------|
| Verdict | **NO_GO** |
| NPV | **-4,057,142.86** SAR (−4.06M) |
| Phase | `REPORT_READY` |
| `take_rate` | `0.30` |

Source: live study snapshot before challenge; also recorded in `financial_change.previous_npv`.

---

## 2. Changed assumptions (exact)

Human challenge message forced recalculation with a revised take rate. Persisted history recorded these key changes between v1 and v2:

| Key | Before | After |
|-----|--------|-------|
| `take_rate` | `0.30` | `0.35` |
| `monthly_rides_year1` | `10000` | `120000` |
| `monthly_fixed_opex` | `0.00` | `300000` |
| `promo_burn_pct` | `0.00` | `10` |

Unchanged in the same pass (examples): `average_trip_value` = `40`, `driver_acquisition_cost`, `initial_investment`.

`assumptions_version`: **1 → 2**  
History length after loop: **2** (assumption bump + financial_results stamp)

---

## 3. New state (assumptions_version = 2)

| Field | Value |
|-------|-------|
| Verdict | **GO_WITH_CONDITIONS** |
| NPV | **+11,200,000** SAR (+11.2M) |
| IRR | **2.6288** (= **262.9%**) |
| Payback | **3.4** months |
| Δ NPV | **+15,257,142.86** |
| Phase | `REPORT_READY` |
| `take_rate` | `0.35` |

`financial_change.explanation` (persisted):

> NPV recalculated under assumptions_version=2. Prior NPV at earlier version was -4057142.86. Changed keys: monthly_fixed_opex, monthly_rides_year1, promo_burn_pct, take_rate.

---

## 4. Why the decision changed

1. **Human challenge** revised unit economics (notably take rate 30%→35% and much higher year-1 ride volume).
2. **Financial engine recalculated** under the new assumption set → NPV flipped from deeply negative (−4.06M) to strongly positive (+11.2M), with IRR 262.9% and short payback.
3. **Decision agent re-scored** against the new financials + still-material risks (licensing, competition, promo burn, opex). Positive returns support investment, but residual risks require controls → **GO_WITH_CONDITIONS** (not unconditional GO).
4. **Not a phase-only update:** report body, `financial_change`, assumption history, and verdict all persisted and reload on GET / refresh.

Conditions attached to the new verdict include (among others): MoT/CITC licensing within 3 months, driver CAC / supply ratio controls, promo spend capped at 10% of revenue, 20% contingency reserve, and opex held near SAR 300k/month.

---

## 5. Browser evidence (human-in-the-loop)

| Evidence | Artifact |
|----------|----------|
| Direct workspace URL loads (not hard Vercel 404) | `01-workspace-before-login.webp` |
| Post-login workspace: Report Ready + **GO_WITH_CONDITIONS** | `02-workspace-after-login-full-view.webp` |
| Financials + risks + decision visible | `03-financial-risks-decision.webp` |
| Assumption version history + NPV −4.06M → +11.2M | `04-npv-change-history.webp` |
| Refresh persistence | `05-after-refresh-persistent.webp` |
| End-to-end demo video | `uber-workspace-demo.mp4` |
| API machine record | `decision_loop_uber.json` |

All under `/opt/cursor/artifacts/report-ready-verification/`.

### Gates shown in UI

- Assumptions changed (v2 + changed keys listed)
- Financial recalculated (NPV / IRR / payback + Δ)
- Verdict updated (`NO_GO` → `GO_WITH_CONDITIONS`)

---

## Acceptance

**PASS — final decision-loop validation complete** for Uber study `study_7373f1139f96`.
