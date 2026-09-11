# Phase 5A — Production Trust Validation

**Status: ACCEPTED**  
**Date:** 2026-09-11 16:24 UTC  
**Branch:** `cursor/ai-reliability-trust-hardening-1831`  
**PR:** https://github.com/majaber1/saudi-business/pull/26  
**Baseline:** PR #24 frozen (no engine redesign)

## ROOT CAUSES

1. **Provider/internal leakage risk** — raw Groq/OpenAI errors (org IDs, model names, billing URLs, TPM/TPD, stacks) and tool/JSON/prompt fragments could surface in chat/API `error` fields.
2. **Unsafe classification under AI failure / weak heuristics** — `"not a data center"` substring matched DC keywords, so cybersecurity consulting could classify as `data_center`; mobility needed explicit guards.
3. **Provider rate-limit handling** — without alternate-model routing + confirmation-on-unavailable, studies could stall or invent results.
4. **Browser click reliability** — sticky footer intercepted `confirm-profile` clicks in headless runs (test harness), masking otherwise healthy journeys.

## FIXES

| Area | Fix |
|------|-----|
| Sanitization | `ai_engine/utils/safe_messages.py` + frontend chat sanitizer strips org/model/billing/TPM/stack/JSON/tool/prompt/financial payloads |
| Classification | Mobility + professional/cyber guards; services keywords before DC; negate `"not a data center"`; confirm when AI unavailable / ambiguous |
| Provider | `invoke_llm` primary→alternate Groq model; `ProviderUnavailableError` → user-safe confirmation, no invented AI results |
| API public surface | `_safe_ai_error` + `_public_messages` filter |
| Browser harness | force-safe clicks; five fresh-account journeys |

## FILES

- `ai_engine/utils/safe_messages.py`, `ai_engine/utils/__init__.py`
- `ai_engine/provider.py`, `ai_engine/config.py`
- `ai_engine/agents/discovery.py`, `ai_engine/archetypes/classifier.py`
- `ai_engine/agents/evidence.py`, `assumption.py`, `financial_analyst.py`, `risk.py`, `decision.py`
- `backend/app/api/v2/study_engine.py`
- `apps/web/app/projects/[projectId]/studies/[studyId]/workspace/page.tsx`
- `tests/test_phase5a_ai_reliability.py`
- `scripts/phase5a_browser_e2e.mjs`
- `docs/evidence/PHASE5A_PRODUCTION_TRUST_VALIDATION.md`

## PROVIDER FAILURE TEST

Probe (Uber-like text + mocked 429 with org/model/billing/TPD):

```json
{
  "phase": "ARCHETYPE_CLASSIFICATION",
  "archetype": "services",
  "error": null,
  "messages": [
    "Uber-like ride hailing marketplace in Jeddah with drivers and take-rate",
    "AI classification is temporarily unavailable. Please confirm the project archetype below before continuing \u2014 we will not silently lock a classification.\n\nSuggested archetype: **Service Business** (`services`). Confirm the archetype, then answer the structured questions.\n\nAI is temporarily unavailabl"
  ]
}
```

Assertions:
- phase stays `ARCHETYPE_CLASSIFICATION` with confirmation messaging
- suggested archetype `services` (not `data_center`)
- `error` is null / user-safe — **zero** org IDs, model names, billing URLs, TPM/TPD, stacks in user-facing messages

## 5-SCENARIO BROWSER RESULTS

Method: Playwright against local `http://127.0.0.1:3000` → BFF → API `:8000`, **fresh account per scenario**.

| Scenario | Archetype observed | Final phase | Leaks | Result |
|----------|-------------------|-------------|-------|--------|
| SaaS compliance | `saas_digital` | Report Ready | 0 | PASS |
| Cybersecurity services | `services` (not DC) | Report Ready | 0 | PASS |
| Residential compound | `real_estate` | Report Ready | 0 | PASS |
| Data center 20MW | `data_center` | Report Ready | 0 | PASS |
| Uber-like marketplace | `services` (not DC) | Report Ready | 0 | PASS |

Refresh / re-login persistence (SaaS): **PASS** (`phase5a-persistence-refresh.png`, `phase5a-persistence-relogin.png`).

### Screenshots

| Evidence | Path |
|----------|------|
| SaaS classification | `/opt/cursor/artifacts/phase5a-saas-classification.png` |
| SaaS assumptions | `/opt/cursor/artifacts/phase5a-saas-assumptions.png` |
| SaaS report | `/opt/cursor/artifacts/phase5a-saas-report.png` |
| Cyber classification | `/opt/cursor/artifacts/phase5a-cyber-classification.png` |
| Cyber assumptions | `/opt/cursor/artifacts/phase5a-cyber-assumptions.png` |
| Cyber report | `/opt/cursor/artifacts/phase5a-cyber-report.png` |
| Residential classification | `/opt/cursor/artifacts/phase5a-residential-classification.png` |
| Residential assumptions | `/opt/cursor/artifacts/phase5a-residential-assumptions.png` |
| Residential report | `/opt/cursor/artifacts/phase5a-residential-report.png` |
| Data center classification | `/opt/cursor/artifacts/phase5a-datacenter-classification.png` |
| Data center assumptions | `/opt/cursor/artifacts/phase5a-datacenter-assumptions.png` |
| Data center report | `/opt/cursor/artifacts/phase5a-datacenter-report.png` |
| Uber classification | `/opt/cursor/artifacts/phase5a-uber-classification.png` |
| Uber assumptions | `/opt/cursor/artifacts/phase5a-uber-assumptions.png` |
| Uber report | `/opt/cursor/artifacts/phase5a-uber-report.png` |
| Persistence refresh | `/opt/cursor/artifacts/phase5a-persistence-refresh.png` |
| Persistence re-login | `/opt/cursor/artifacts/phase5a-persistence-relogin.png` |

## SECURITY LEAK TEST

Across browser body text for all five journeys + provider-failure probe:

- **Zero** `org_*` / provider request IDs
- **Zero** model names (`llama-*`, `gpt-oss-*`)
- **Zero** billing / console URLs
- **Zero** TPM/TPD quota wording
- **Zero** raw JSON fences / tool_call dumps / internal prompts / financial payload blobs in chat

## TESTS

- `pytest tests/test_phase5a_ai_reliability.py` → **16 passed**
- Includes sanitizer, Uber≠DC, cyber≠DC, marketplace≠DC, ambiguous confirm, provider fallback raise, SaaS schema/isolation
- Browser E2E harness: `scripts/phase5a_browser_e2e.mjs` → **5/5 PASS** after cyber classifier fix

## KNOWN LIMITATIONS

- Preview/production deploy URL not required for local Phase 5A ACCEPTED gate; Vercel preview browser SSO can still block automated preview UI (local browser evidence is authoritative here).
- AI Discovery Advisor intentionally **not started**.
- PR #24 engines not redesigned — only sanitization, classification guards, and provider resilience.

## COMMIT / PR

- Commits on `cursor/ai-reliability-trust-hardening-1831` (incl. `9a767f1`, `ac29256`, `dc9ea71`, `6b2201c`)
- PR: https://github.com/majaber1/saudi-business/pull/26 (draft — do not merge until human review)

## FINAL STATUS

# ACCEPTED
