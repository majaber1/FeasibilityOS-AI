# V2 Study Engine — Minimal HTTP API Sequence

Source of truth: `backend/app/api/v2/study_engine.py`, `backend/app/api/v2/knowledge.py`,
`backend/app/api/auth.py`, `ai_engine/orchestrator.py`, and e2e coverage in
`tests/test_e2e_full_journey.py`, `tests/test_discovery_advisor_api.py`,
`tests/test_archetype_e2e_scenarios.py`.

Phase machine (orchestrator):

```
DRAFT → ARCHETYPE_CLASSIFICATION → NEEDS_INFORMATION → EVIDENCE_REVIEW
  → ASSUMPTIONS_REVIEW → READY_FOR_ANALYSIS → ANALYZED → DECISION_READY → REPORT_READY
```

`POST …/message` and most approve/confirm handlers call `run_study_step`, which
routes by `state.phase` (`READY_FOR_ANALYSIS`→financial, `ANALYZED`→risk,
`DECISION_READY`→decision). `REPORT_READY` is terminal (`END`).

---

## 0. Auth

### Register

```http
POST /auth/register
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "password": "Journey@Test1!",
  "full_name": "optional",
  "role_key": "entrepreneur",
  "locale": "ar"
}
```

| Field | Required | Notes (from `RegisterIn`) |
|---|---|---|
| `email` | yes | Normalized lower-case |
| `password` | yes | 8–128 chars, ≥1 letter, ≥1 digit, not common |
| `full_name` | no | max 200 |
| `role_key` | no | default `entrepreneur`; public allowlist only: `entrepreneur`, `consultant`, `investor`, `franchise_owner` |
| `locale` | no | default `ar`; `ar` \| `en` only |

**Response:** `201` `UserOut` — `{ id, email, full_name, role_key, locale, email_verified }`.  
Register does **not** return a JWT.

### Login

```http
POST /auth/login
Content-Type: application/json
```

```json
{ "email": "user@example.com", "password": "Journey@Test1!" }
```

**Response:** `200`

```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

### Auth header (all v2 study / knowledge routes)

```http
Authorization: Bearer <access_token>
```

Implemented via FastAPI `HTTPBearer` (`get_current_user`). Missing/invalid token → `401`.  
E2e helpers build headers exactly as:

```python
{"Authorization": f"Bearer {tok}"}
```

---

## 1. Minimal fresh-study sequence

Optional but used in e2e: create a project first (`POST /projects/` with
`name`, `industry`, `investment`, `stage`). Study creation only needs a
`project_id` string — the study engine does not FK-validate it.

### Step A — Create study

```http
POST /api/v2/studies
Authorization: Bearer <token>
Content-Type: application/json
```

```json
{
  "project_id": "<project id or any string>",
  "language": "ar",
  "description": "منصة SaaS لإدارة المشاريع للشركات السعودية"
}
```

| Field | Default | Notes |
|---|---|---|
| `project_id` | required | string |
| `language` | `"ar"` | `"ar"` \| `"en"` |
| `description` | `""` | If non-empty, appended as HumanMessage and `run_study_step` runs discovery |

**Typical response fields:** `study_id`, `phase` (often `ARCHETYPE_CLASSIFICATION` when description triggers discovery), `profile`, `discovery_questions`, `archetype_options`, `assumption_schema`, `messages`, `next_action`, `knowledge_context`, …

Without `description`, study stays `DRAFT` until you `POST …/message` or set archetype.

### Step B — Archetype confirm

Two equivalent paths exist.

**Preferred (e2e):** explicit select + approve

```http
POST /api/v2/studies/{study_id}/archetype
```

```json
{ "archetype": "saas_digital", "approved": true }
```

| Field | Default | Notes |
|---|---|---|
| `archetype` | required | Normalized via `normalize_archetype` |
| `approved` | `true` | If `true`, runs `_finalize_archetype_confirmation` → structured questions / `NEEDS_INFORMATION` (or `EVIDENCE_REVIEW` if no unanswered required Qs) |

Supported archetypes: `saas_digital`, `real_estate`, `data_center`, `industrial`, `retail`, `services`, `other`.

**Alternate:** gate approve while phase is `ARCHETYPE_CLASSIFICATION`

```http
POST /api/v2/studies/{study_id}/approve/archetype
```

```json
{ "approved": true, "feedback": "archetype=real_estate" }
```

`feedback` may contain `archetype=<id>` to override the suggested archetype.
On success: `profile.archetype_confirmed=true`, `discovery_questions` populated,
phase → `NEEDS_INFORMATION` (or `EVIDENCE_REVIEW` if all required answered).

### Step C — Discovery / profile (structured answers)

```http
POST /api/v2/studies/{study_id}/structured-answers
```

```json
{
  "answers": {
    "pricing": 299,
    "target_customers": 500,
    "arr": 1800000,
    "cac": 500,
    "churn": 5
  },
  "ai_estimates": ["ltv", "opex_annual"],
  "mark_answered": true
}
```

| Field | Default | Notes |
|---|---|---|
| `answers` | `{}` | Map of question `id` → value. Numeric poison strings (`confirmed`, `ok`, `yes`, …) are dropped for `NUMBER`/`CURRENCY`/`PERCENT*` |
| `ai_estimates` | `[]` | Question ids to mark answered via AI estimate (no value written into `structured_answers`) |
| `mark_answered` | `true` | Empty explicit answers stay unanswered |

When all **required** questions are satisfied:

- `profile_confirmed = true`
- `profile.archetype_confirmed = true`
- `phase = EVIDENCE_REVIEW`
- `run_study_step` runs the evidence agent

**Alternate profile gate** (if still in `NEEDS_INFORMATION` / `ARCHETYPE_CLASSIFICATION` / `UNDERSTANDING`):

```http
POST /api/v2/studies/{study_id}/approve/profile
```

```json
{ "approved": true }
```

Forces `EVIDENCE_REVIEW` even with gaps (AI is instructed to estimate missing items).

### Step D — Evidence

If evidence is incomplete, nudge the agent:

```http
POST /api/v2/studies/{study_id}/message
```

```json
{ "message": "السوق ينمو 15% والاشتراك 299 ريال", "language": "ar" }
```

`language` is optional. Phase must be `EVIDENCE_REVIEW` for the evidence agent.

**Approve evidence** (requires ≥1 claim; phase must be `EVIDENCE_REVIEW`):

```http
POST /api/v2/studies/{study_id}/approve/evidence
```

```json
{ "approved": true }
```

Side effects (code order):

1. `evidence_approved = true`
2. `phase = ASSUMPTIONS_REVIEW`
3. `_prepare_assumptions_with_knowledge` → tenant Evidence Pack into `state.knowledge_context`
4. `run_study_step` (assumptions agent); empty-guard may call `run_assumptions` directly
5. `_finalize_knowledge_influence` → enriches assumption `knowledge_refs` / `knowledge_influence`

Reject path: `{ "approved": false, "feedback": "…" }` records feedback, does not advance.

### Step E — Assumptions

Optional per-card / edit APIs while in `ASSUMPTIONS_REVIEW`:

| Method | Path | Body |
|---|---|---|
| POST | `/api/v2/studies/{id}/assumptions/edit` | `{ "key", "value", "low?", "base?", "high?", "explanation?" }` |
| POST | `/api/v2/studies/{id}/assumptions/action` | `{ "key", "action": "approve"\|"reject"\|"regenerate", "value?", "explanation?" }` |
| POST | `/api/v2/studies/{id}/assumptions/regenerate` | (no body) — clears all, re-attaches knowledge, rebuilds |

**Study-level approve** (phase `ASSUMPTIONS_REVIEW`; non-empty assumptions; no empty values):

```http
POST /api/v2/studies/{study_id}/approve/assumptions
```

```json
{ "approved": true }
```

Sets `assumptions_approved`, `phase = READY_FOR_ANALYSIS`, then `run_study_step` → **financial** → typically `ANALYZED` with `financial_results`.

### Step F — Financial → Risk → Decision → REPORT_READY

Financial usually runs inside assumptions approve (see above). To advance risk/decision, post any message while in the matching phase (or rely on another `run_study_step` trigger):

```http
POST /api/v2/studies/{study_id}/message
```

```json
{ "message": "قيّم المخاطر" }
```

| Current phase | Agent | Next phase on success |
|---|---|---|
| `READY_FOR_ANALYSIS` | financial | `ANALYZED` |
| `ANALYZED` | risk | `DECISION_READY` (when `risk_assessment_complete`) |
| `DECISION_READY` | decision | `REPORT_READY` |

Example decision nudge:

```json
{ "message": "القرار النهائي" }
```

On `REPORT_READY`, `_remember_study_if_ready` upserts a tenant `StudyMemory` (idempotent).

### Step G — Read final payload

```http
GET /api/v2/studies/{study_id}
```

Inspect: `phase`, `verdict`, `decision_rationale`, `decision_conditions`, `decision_risks`, `financial_results`, `assumptions`, `claims`, `knowledge_context`.

List studies: `GET /api/v2/studies` → `{ "studies": [ { study_id, phase, archetype, verdict, created_at, updated_at } ] }`.

---

## 2. Approve / confirm stages (cheat sheet)

All share body:

```json
{ "approved": true, "feedback": null }
```

(`StudyApprovalRequest`: `approved: bool`, `feedback: Optional[str]`)

| Stage path | Allowed phases | Flag set | Advance |
|---|---|---|---|
| `…/approve/archetype` | `ARCHETYPE_CLASSIFICATION` | (via finalize) | structured Qs / `NEEDS_INFORMATION` |
| `…/approve/profile` | `NEEDS_INFORMATION`, `ARCHETYPE_CLASSIFICATION`, `UNDERSTANDING` | `profile_confirmed` | `EVIDENCE_REVIEW` |
| `…/approve/evidence` | `EVIDENCE_REVIEW` | `evidence_approved` | `ASSUMPTIONS_REVIEW` (+ knowledge retrieve) |
| `…/approve/assumptions` | `ASSUMPTIONS_REVIEW` | `assumptions_approved` | `READY_FOR_ANALYSIS` → financial |

Invalid stage → `400`. Wrong phase → `400` with expected phases.  
Evidence with no claims → `400 "No evidence to approve."`  
Assumptions empty / empty values → `400`.

Dedicated archetype select (not under `/approve/`):

```http
POST /api/v2/studies/{study_id}/archetype
{ "archetype": "<id>", "approved": true }
```

---

## 3. Knowledge API (`/api/v2/knowledge/*`)

Requires DB (`DB_ENABLED`); otherwise `503`. All routes need `Authorization: Bearer …`. Tenant isolation is by `owner_id = user.id`.

### Upload document

```http
POST /api/v2/knowledge/documents
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

| Form field | Required | Notes |
|---|---|---|
| `file` | yes | PDF, DOCX, XLSX/XLS, TXT; max **12 MB** |
| `title` | no | |
| `document_type` | no | metadata override |
| `project_type` | no | e.g. `real_estate`, `data_center` |
| `sector` | no | |
| `year` | no | int |

**Response:** `{ "document": { id, title, source, sector, country, year, document_type, project_type, capex, opex, revenue_model, assumptions, outcome, confidence, visibility, extraction_status, original_filename, content_type, created_at, chunk_count, quality_score, quality_breakdown, reference_count, geography, business_model } }`  
Embeddings are never returned.

### List / get

```http
GET /api/v2/knowledge/documents
GET /api/v2/knowledge/documents/{document_id}
```

GET-by-id also returns `chunks[]` with `id`, `content` (≤500 chars), `importance`, `metadata`.

### Retrieve Evidence Pack

```http
POST /api/v2/knowledge/retrieve
```

```json
{
  "query": "residential compound Riyadh land cost absorption",
  "study_id": "study_abc123",
  "assumption_keys": ["land_cost", "units", "absorption_rate"],
  "top_k": 6,
  "query_profile": {
    "sector": "residential",
    "project_type": "real_estate",
    "geography": "Riyadh",
    "capex": 300000000
  }
}
```

| Field | Default | Constraints |
|---|---|---|
| `query` | required | 3–4000 chars |
| `study_id` | null | optional context |
| `assumption_keys` | null | drives `assumption_hints` |
| `top_k` | `6` | 1–20 |
| `query_profile` | null | similarity / ranking hints |

**Response:** `{ "evidence_pack": { query, comparable_projects, similar_projects, assumption_hints, risk_hints, financial_patterns, citations, hit_count } }`

### Other

| Method | Path | Response |
|---|---|---|
| GET | `/api/v2/knowledge/dashboard` | `{ "dashboard": … }` |
| GET | `/api/v2/knowledge/memories` | `{ "memories": [ { id, source_study_id, archetype, project_type, sector, decision, lessons_learned, summary_text, conditions, influence_summary } ] }` |

---

## 4. How knowledge appears on study payloads

### `knowledge_context` (study-level)

Attached on evidence approve / assumption regenerate / rebuild paths via
`_attach_knowledge_context`, then exposed by `_public_knowledge_context`:

```json
{
  "query": "…",
  "hit_count": 3,
  "comparable_projects": [ /* ≤8 */ ],
  "similar_projects": [ /* ≤8 */ ],
  "assumption_hints": [ /* ≤12 */ ],
  "risk_hints": [ /* ≤8 */ ],
  "financial_patterns": [ /* ≤8 */ ],
  "citations": [ /* ≤12 */ ]
}
```

**Gotcha — persistence:** `StudyStateRow` / `_row_to_dict` do **not** store
`knowledge_context`. It is present on the **response of the request that
attached it** (e.g. evidence approve). A later `GET /api/v2/studies/{id}` may
return `"knowledge_context": null` even though influence was applied. Prefer
reading influence from assumptions (below), or call `POST /api/v2/knowledge/retrieve` again.

Auto-retrieve query is built from archetype (+ expansion vocabulary), sector,
recent messages, structured answers, and schema keys — failures never block the study.

### `similar_projects`

Inside `knowledge_context` / Evidence Pack. Built by
`ai_engine.knowledge.similarity.build_similar_projects` (same-sector /
geography preference). Cards typically include document/memory ids, titles,
similarity scores/reasons (see retrieve pack builder).

### `knowledge_influence` (per assumption)

After `_finalize_knowledge_influence` → `enrich_assumption_influence`:

Assumptions that already have `knowledge_refs` gain:

```json
{
  "key": "land_cost",
  "value": "…",
  "knowledge_refs": [ /* enriched with reason, confidence, source_document, match_reasons */ ],
  "knowledge_confidence": 0.72,
  "knowledge_influence": {
    "reason": "Similar project evidence",
    "confidence": 0.72,
    "source_count": 2
  }
}
```

These fields live on assumption objects in the study payload `assumptions[]`
and **are** persisted via `assumptions_json`. UI (`AssumptionReviewPanel`)
reads `a.knowledge_influence.reason`.

On `REPORT_READY`, study memory `influence_summary` records counts + similar
projects for later learning (`GET /api/v2/knowledge/memories`).

---

## 5. Archetype gotchas (`services` / `real_estate` / `data_center`)

### Shared

- Classification must be **confirmed** before structured discovery (`ARCHETYPE_CLASSIFICATION` gate). Skipping confirmation leaves the study stuck.
- SaaS-only keys (`cac`, `churn`, `arr`, `mrr`, `ltv`, …) are stripped / rejected on non-SaaS archetypes (`assert_no_saas_leakage`). Editing an assumption with a leaked SaaS key → `400`.
- Discovery question `id`s equal schema `key`s — use those ids in `structured_answers.answers` / `ai_estimates`.
- Payload always includes `archetype_options` + `assumption_schema` for the current archetype (and `services_variant` when set).

### `services`

- Default variant is **`professional`** (MSSP / consulting / agency).
- **`mobility`** only when ride-hailing / marketplace signals appear (Uber, drivers, take rate, trips, …) via `detect_services_variant`.
- Professional keys: `consultants_headcount`, `utilization_rate`, `active_contracts`, `monthly_recurring_contracts`, `delivery_cost_monthly`, `gross_margin`, `initial_investment`.
- Mobility keys: `take_rate`, `monthly_trips`, `drivers`, `driver_cac`, `avg_trip_value`, `monthly_fixed_opex`, `initial_investment`.
- Do **not** mix: mobility keys must not appear on professional studies (`assert_no_mobility_on_professional`). `driver_cac` is mobility-specific, not SaaS CAC.
- Confirming archetype with `services` stores `profile.services_variant` and selects the matching question/schema set.

### `real_estate`

- Expected keys: `land_cost`, `construction_boq`, `units`, `selling_price`, `absorption_rate`, `financing`, optional `loan_to_cost`.
- Knowledge auto-query expands with residential/occupancy/absorption vocabulary.
- Must not receive SaaS metrics (CAC/ARR/MRR/churn).

### `data_center`

- Expected keys: `mw_capacity`, `rack_count`, `pue`, `power_cost`, `occupancy`, `pricing_per_kw`, `capex_total`, optional `opex_annual` (+ schema select fields for model/tier as defined in `DATA_CENTER_SCHEMA`).
- Knowledge expansion uses MW / PUE / rack / colocation terms.
- Same SaaS anti-leakage rules as real estate.

Golden scenario coverage: `tests/test_archetype_e2e_scenarios.py` (`uber`/`cybersecurity_mssp` → services, `residential` → real_estate, `datacenter` → data_center).

---

## 6. Curl sketch (happy path)

```bash
BASE=http://localhost:8000
EMAIL="demo_$(date +%s)@example.com"
PASS='Journey@Test1!'

# Auth
curl -sS -X POST "$BASE/auth/register" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}"
TOK=$(curl -sS -X POST "$BASE/auth/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | jq -r .access_token)
AUTH="Authorization: Bearer $TOK"

# Knowledge (optional, before assumptions)
curl -sS -X POST "$BASE/api/v2/knowledge/documents" -H "$AUTH" \
  -F "file=@./sample.pdf" -F "project_type=real_estate" -F "sector=residential"
curl -sS -X POST "$BASE/api/v2/knowledge/retrieve" -H "$AUTH" \
  -H 'Content-Type: application/json' \
  -d '{"query":"Riyadh residential compound absorption","top_k":6}'

# Study
SID=$(curl -sS -X POST "$BASE/api/v2/studies" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"project_id":"proj_demo","language":"en","description":"Residential compound 400 villas near Riyadh"}' \
  | jq -r .study_id)

curl -sS -X POST "$BASE/api/v2/studies/$SID/archetype" -H "$AUTH" \
  -H 'Content-Type: application/json' \
  -d '{"archetype":"real_estate","approved":true}'

curl -sS -X POST "$BASE/api/v2/studies/$SID/structured-answers" -H "$AUTH" \
  -H 'Content-Type: application/json' \
  -d '{"answers":{"land_cost":80000000,"construction_boq":220000000,"units":400,"selling_price":1800000,"absorption_rate":80,"financing":"Mixed (equity + debt)"},"ai_estimates":[]}'

curl -sS -X POST "$BASE/api/v2/studies/$SID/approve/evidence" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"approved":true}'

curl -sS -X POST "$BASE/api/v2/studies/$SID/approve/assumptions" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"approved":true}'

curl -sS -X POST "$BASE/api/v2/studies/$SID/message" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"message":"Assess risks"}'
curl -sS -X POST "$BASE/api/v2/studies/$SID/message" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"message":"Final decision"}'

curl -sS "$BASE/api/v2/studies/$SID" -H "$AUTH" | jq '{phase,verdict,knowledge_context,assumptions:[.assumptions[]|{key,knowledge_influence}]}'
```

Evidence/assumptions approve may fail if the AI step has not yet produced
`claims` / non-empty assumption values — send a `…/message` first or use
`ai_estimates` / edit endpoints as in the e2e suites.

---

## 7. Reference map

| Concern | Code |
|---|---|
| Study routes / payloads | `backend/app/api/v2/study_engine.py` |
| Knowledge upload/retrieve | `backend/app/api/v2/knowledge.py` |
| Auth JWT | `backend/app/api/auth.py` |
| Phase routing | `ai_engine/orchestrator.py` |
| Schemas / leakage | `ai_engine/archetypes/schemas.py` |
| Influence enrichment | `ai_engine/knowledge/influence.py` |
| Full API journey (mocked LLM) | `tests/test_e2e_full_journey.py` |
| Discovery + AI estimates | `tests/test_discovery_advisor_api.py` |
| RE / DC / services scenarios | `tests/test_archetype_e2e_scenarios.py` |
