# Service Boundaries

## Principle

Every major capability in Saudi Business behaves as an independent product/service.
Services share a common Business context when the user explicitly links them,
but never require each other.

## Service Module Structure

Each service follows this pattern:

```
backend/app/api/<service>.py     — API router
backend/app/models.py            — DB models (service-specific tables)
apps/web/app/tools/<service>/    — Frontend pages
```

## Cross-Service Rules

1. **No forced dependencies**: Feasibility does not require Qualification. Funding does not require Feasibility.
2. **Explicit import**: "Import from Feasibility Study" button, not automatic.
3. **Source tracking**: When importing, show source record, imported fields, and timestamp.
4. **Independent APIs**: Each service has its own API prefix (`/api/feasibility`, `/api/proposals`, etc.)
5. **Independent DB tables**: Each service owns its tables. Shared context lives in `projects` table.

## Service APIs

| Service | Prefix | Auth Required | Public Endpoints |
|---------|--------|---------------|-----------------|
| Projects | `/projects` | Yes | No |
| Feasibility | `/feasibility` | Yes | No |
| Financial | `/financial` | Mixed | `/evaluate`, `/sensitivity` public; `/analyses` authenticated |
| Funding | `/funding` | No | `/match` |
| Proposals | `/proposals` | Yes | `/from-study/{id}` preview |
| Qualification | `/api/qualification` | Yes | No |
| Opportunities | `/opportunities` | No | List/filter |
| Franchises | `/franchises` | No | List |
| Auctions | — | — | **Removed from the product. `/tools/auctions` explains this; there is no catalog API.** |
| Reports | `/reports` | Yes | `/investor-package` |
| Notifications | `/notifications` | Yes | No |
| Analytics | `/analytics` | Yes | Allowlisted event types only |
| Entitlements | `/entitlements` | Yes | Demo provider enables tools; no fake checkout |
