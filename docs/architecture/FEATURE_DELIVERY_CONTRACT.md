# Feature Delivery Contract

Locked: 2026-09-04. Mandatory for every feature from this point forward.
Read alongside `docs/architecture/SAUDI_BUSINESS_MASTER_ARCHITECTURE.md`.

## The core rule

**Backend pass is not feature pass.** A model, migration, service, API
endpoint, and passing unit tests are implementation *components*, not a
completed feature. A feature is complete only when the target user can
actually perform the promised business task through the real application.

Before marking anything complete, ask: **can the target user actually
perform the promised business task in the real Saudi Business
application?** If no, it is not complete -- regardless of how much backend
work is done or how green the test suite is.

None of the following, alone or combined, constitute a complete feature:

- a database table exists
- a model exists
- a service exists
- an endpoint exists
- unit tests pass
- mock/fixture data works
- a UI placeholder exists
- documentation says PASS

## Allowed status values

Use only these. Never report a generic "PASS".

- `NOT_STARTED`
- `BACKEND_ONLY` — API/service/engine exists and is tested, no real frontend path
- `FRONTEND_ONLY` — UI exists but isn't wired to a real backend (should be rare/temporary)
- `PARTIAL` — some but not all Definition-of-Done requirements below are met
- `LOCAL_PASS` — full vertical slice verified in a local dev environment
- `PREVIEW_PASS` — verified against a deployed preview environment
- `PRODUCTION_PASS` — verified in production
- `BLOCKED` — cannot proceed (missing secret, external dependency, etc.)
- `FAIL` — implemented but broken

Do not claim `PREVIEW_PASS` or `PRODUCTION_PASS` without actually testing
against that environment.

## Definition of Done (for `LOCAL_PASS`)

All applicable items must be true.

**Architecture**: Master Architecture and this contract reviewed. Feature's
Wave identified. Layer identified. Parent resource identified. No
architecture drift (or an approved ADR covers the drift).

**Backend**: real API/service implemented. Validation works. Authorization
works. Ownership isolation works. Errors are explicit, not swallowed.

**Persistence**: if data should survive, verify save → refresh → (browser
close where applicable) → logout → login → reopen.

**Frontend**: a real application entry point exists (not a route that 404s
or a stub). Includes, as applicable: working controls, loading state,
success state, error state, empty state, saved state, navigation.

**Wiring**: the actual path is verified end to end: UI → API → domain
service → database → deterministic engine → response → UI. Not assumed
from reading the code -- exercised.

**Real data**: features promising market evidence, funding programs,
franchises, opportunities, licensing, or Saudi statistics cannot reach
product PASS backed by fixtures or fabricated data. Fixtures are
TEST-ONLY, never shipped as the feature's real data source.

**AI**: if the AI provider is unavailable, the feature is disabled or shows
"not configured" -- never a faked AI result.

**Tests**: appropriate mix of unit, API, database, ownership, integration,
browser/E2E as the feature warrants.

**Build**: applicable gates pass (`pytest`, `npm run typecheck`, `npm run
lint`, `npm run build`).

**Browser verification**: for user-facing features, run the actual app
where the environment permits. Verify: page loads, controls work, API
calls work, no critical console error, no critical runtime error,
persistence works, navigation works.

**Deployment**: if preview wasn't tested, don't claim `PREVIEW_PASS`. If
production wasn't tested, don't claim `PRODUCTION_PASS`.

## Pacing rule

At most one backend-heavy dependency may temporarily exist ahead of its
UI. Before starting another backend-only engine, catch up the real
vertical slice for what's already built. Do not let technical phases run
far ahead of actual user experience.
