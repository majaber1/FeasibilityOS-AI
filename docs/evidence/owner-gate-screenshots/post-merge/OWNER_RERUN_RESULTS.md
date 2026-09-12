# OWNER ACCEPTANCE TEST — Initial Production Run Record

**Date:** 2026-09-12 03:25–03:37 UTC  
**Production URL:** https://saudi-business-web.vercel.app  
**Account:** fresh production test account; identifier redacted from public evidence.  
**Password:** intentionally not stored.

> This file preserves the **initial run chronology**, including the AI Estimate stall. It is not the final OWNER GATE result. The completed late-stage and persistence verification is recorded in `OWNER_LATE_STAGE_LOG.md`, `OWNER_PERSIST_REOPEN.md`, screenshots in this directory, and the canonical `docs/evidence/OWNER_ACCEPTANCE_TEST.md`.

---

## Initial execution summary

| Step | Requirement | Initial-run status | Evidence / Notes |
|------|-------------|--------------------|------------------|
| 1 | Open production URL | PASS | Production URL loaded |
| 2 | Register fresh account | PASS | Account created via UI |
| 3 | Dashboard opens | PASS | Product workspace loaded |
| 4 | Create new project via Projects UI | PASS | Project created with Arabic idea |
| 5 | Confirm idea text visible | PASS | MSSP idea displayed |
| 6 | Start AI feasibility study | PASS | Study workspace opened |
| 7 | Archetype shows friendly labels only | PASS | «أعمال خدمية» shown; raw IDs not exposed as primary labels |
| 8 | Complete AI Discovery | PARTIAL | AI Estimate stalled at 14% during this first run |
| 9 | Use AI Estimate where appropriate | PASS | Estimate action invoked |
| 10 | Assumptions review with visible CTA | BLOCKED IN INITIAL RUN | Discovery had not completed yet |
| 11 | Financial analysis inside study | BLOCKED IN INITIAL RUN | Discovery had not completed yet |
| 12 | Risks reachable from study | BLOCKED IN INITIAL RUN | Discovery had not completed yet |
| 13 | Decision reachable from study | BLOCKED IN INITIAL RUN | Discovery had not completed yet |
| 14 | Report reachable from study | BLOCKED IN INITIAL RUN | Discovery had not completed yet |
| 15 | Refresh persistence | NOT TESTED IN INITIAL RUN | Deferred |
| 16 | Logout via UI | NOT TESTED IN INITIAL RUN | Deferred |
| 17 | Login again | NOT TESTED IN INITIAL RUN | Deferred |
| 18 | Find same project via navigation | NOT TESTED IN INITIAL RUN | Deferred |
| 19 | Reopen study and confirm persistence | NOT TESTED IN INITIAL RUN | Deferred |

---

## Defect observed

### AI Estimate stalled at 14%

The production AI Estimate action began processing but did not complete during the initial run. This is retained as a real production reliability finding.

Actions attempted in the initial run included waiting, retrying the estimate control, and continuing through normal UI options. No API or database shortcut was used to manufacture a pass.

**Impact on this initial run:** late-stage acceptance could not be completed in the same uninterrupted segment.

**Final gate handling:** the owner later completed Discovery through the supported manual-answer path on the same production study, after which Assumptions → Financial → Risks → Decision → Report and logout/reopen persistence were verified through the production UI. See the canonical acceptance report for the final 19/19 result.

---

## Initial screenshot evidence

- `owner-rerun-02-dashboard.png`
- `owner-rerun-03-project.png`
- `owner-rerun-04-study.png`
- `owner-rerun-05-archetype.png`
- `owner-rerun-06-discovery.png`
- `owner-rerun-07-ai-stuck.png`

Additional completion evidence is stored in the same `post-merge/` directory.

---

## Security / evidence hygiene

- Test credentials are not stored in repository evidence.
- Project/study identifiers may appear in screenshots/logs strictly as run evidence; they were not used as hardcoded acceptance shortcuts.
- The authoritative final status is `docs/evidence/OWNER_ACCEPTANCE_TEST.md`.
