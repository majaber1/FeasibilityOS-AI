# Runtime Environment Baseline

## Source Control

Repository:
majaber1/saudi-business

Branch:
feat/ai-decision-workspace-v1

Validated Commit:
5a21321

## Local Environment

Frontend:
Next.js

Backend:
FastAPI

Database:
PostgreSQL

Docker:
Local validation only

## Deployment Flow

```text
Local Validation
        |
        v
GitHub
        |
        v
Vercel
```

## Rules

- GitHub is source of truth
- Docker is local only
- No production architecture changes
- No direct Vercel manual modifications
- Validate before deployment
