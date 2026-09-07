# Saudi Business Risk Register

## Document Control

- **Document ID:** SB-GOV-RISK-001
- **Title:** Risk Register
- **Version:** GOV-0.1
- **Status:** DRAFT
- **Owner:** Project Governance Authority
- **Created Date:** 2026-09-06
- **Last Updated:** 2026-09-06
- **Related Requirements:** Pending reconstruction
- **Related ADRs:** Pending inventory
- **Supersedes:** None
- **Change Summary:** Initial governance risk register

---

| Risk ID | Severity | Risk | Current Status | Evidence / Next Action |
|---|---|---|---|---|
| SB-RISK-001 | HIGH | Existing study/project edit lifecycle is unclear to users | OPEN | Confirm in formal design review; likely requires governed CR |
| SB-RISK-002 | HIGH | `New Study` vs existing-study behavior may create duplicate/ambiguous records | OPEN | Trace actual frontend/API/DB behavior before remediation |
| SB-RISK-003 | HIGH | Study/business-record versioning and lineage are not yet formally governed | OPEN | Assess current DB/model behavior and propose ADR/CR if needed |
| SB-RISK-004 | HIGH | Arabic PDF output may be unreadable (`nnnn`) | OPEN | Audit report-generation stack/fonts; do not fix during read-only audit |
| SB-RISK-005 | HIGH | Final full lifecycle E2E certification under governance is incomplete | OPEN | Build evidence-based E2E plan after baseline audit |
| SB-RISK-006 | MEDIUM | Local Wave 3 catalog/acceptance data may be absent | OPEN | Inventory seeds/fixtures/catalog sources and provenance |
| SB-RISK-007 | MEDIUM | Validation certification requires real non-simulated evidence | OPEN | Define approved evidence/test dataset strategy without fabricating evidence |
| SB-RISK-008 | HIGH | Security/operations/cost readiness have not yet been assessed under the new standard | OPEN | Complete baseline assessments before production readiness decision |
