# V3.0.0 Production Smoke

**Aggregate:** PASS
**Expected / merge SHA:** `33e216e2ed939b065bca0357c3855184e219a68d`
**API:** https://feasibilityos-ai.vercel.app
**Web:** https://saudi-business-web.vercel.app
**Finished:** 2026-09-12T15:56:04Z

| Scenario | Pass | Phase | Classification | NPV | IRR display | Payback display | CAPEX warn | Persistence |
|----------|------|-------|----------------|-----|-------------|-----------------|------------|-------------|
| Residential | True | REPORT_READY | real_estate | 54194378.64 | 132.9% | 9.1 months | False | True |
| Data Center | True | REPORT_READY | data_center | 55374833.73 | 105.1% | 12.5 months | True | True |
| Cybersecurity Services | True | REPORT_READY | services | 45255045.1 | 1075.6% | 1.2 months | False | True |
| SaaS | True | REPORT_READY | saas_digital | 680883.29 | 34.3% | 22.9 months | False | True |
| Uber Mobility | True | REPORT_READY | other | -1526239.07 | IRR cannot be calculated for these cash flows. | Payback period cannot be calculated for these cash flows. | False | True |

## Checks

All five scenarios: classification, discovery/assumptions, financial, risk, decision, report, no user-facing IRR/Payback null/UNKNOWN, NPV rendered, persistence after re-login. Data Center CAPEX soft warning observed.
