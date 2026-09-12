# V3 Financial Trust Re-validation

Aggregate: **PASS** (5/5)

Requirement: never expose raw `Payback: null` / `IRR: null` to end users.

## Residential — **PASS**
- NPV hand `-39208109.9` vs engine `-39208109.9` → PASS
- IRR display: `3.8%` (raw=0.0376)
- Payback display: `39.7 months` (years=3.31, available=True)
- No raw null: `True`
- Persistence display fields: `True`
- Chat: Financial analysis complete. Review the results panel for details (NPV: -39208109.9, IRR: 3.8%, Payback: 39.7 months).

## Data Center — **PASS**
- NPV hand `-168689958.29` vs engine `-168689958.29` → PASS
- IRR display: `-14.5%` (raw=-0.1453)
- Payback display: `Payback period cannot be calculated for these cash flows.` (years=None, available=False)
- No raw null: `True`
- Persistence display fields: `True`
- Warnings visible: ['CAPEX looks unusually low for a 20 MW data center (~SAR 1,250,000/MW). Expected range about SAR 160,000,000–400,000,000.']
- Soft CAPEX warning PASS=True
- Chat: Financial analysis complete. Review the results panel for details (NPV: -168689958.29, IRR: -14.5%, Payback: Payback period cannot be calculated for these cash flows.).

## Cybersecurity Services — **PASS**
- NPV hand `19556674.79` vs engine `19556674.79` → PASS
- IRR display: `382.4%` (raw=3.8243)
- Payback display: `3.2 months` (years=0.27, available=True)
- No raw null: `True`
- Persistence display fields: `True`
- Chat: Financial analysis complete. Review the results panel for details (NPV: 19556674.79, IRR: 382.4%, Payback: 3.2 months).

## SaaS — **PASS**
- NPV hand `2649859.92` vs engine `2649859.92` → PASS
- IRR display: `86.6%` (raw=0.8664)
- Payback display: `14.2 months` (years=1.18, available=True)
- No raw null: `True`
- Persistence display fields: `True`
- Chat: Financial analysis complete. Review the results panel for details (NPV: 2649859.92, IRR: 86.6%, Payback: 14.2 months).

## Uber Mobility — **PASS**
- NPV hand `3971632.65` vs engine `3971632.65` → PASS
- IRR display: `25.3%` (raw=0.2529)
- Payback display: `25.6 months` (years=2.13, available=True)
- No raw null: `True`
- Persistence display fields: `True`
- Chat: Financial analysis complete. Review the results panel for details (NPV: 3971632.65, IRR: 25.3%, Payback: 25.6 months).
