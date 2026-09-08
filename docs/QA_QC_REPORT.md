# QA/QC report — 2026-08-14

| Check | Result |
|---|---|
| `npm ci --prefer-offline --no-audit` | PASS, 392 packages |
| `npm run lint` | PASS |
| `npm run typecheck` | PASS |
| `npm run build` | PASS, 22 generated routes |
| `python -m pytest -q --basetemp=.pytest-final-tmp` | PASS, 194 tests |

The migration-gate subprocess test now preserves the Windows host environment so Winsock/asyncio can initialize; migration settings remain explicitly overridden by the probe.

Not executed: live PostgreSQL migration, Docker stack, public deployment, or browser E2E because no production endpoint/credentials were recorded.
