# Knowledge Intelligence Layer — Architecture (Phase 6)

Status: DESIGN FOR IMPLEMENTATION (MVP)  
Date: 2026-09-11  
Baseline freeze: PR #25 merged (`a067961`) — Discovery Advisor on production  

This document designs the **Knowledge Intelligence Layer**. It does **not**
replace or redesign the approved engines. It adds a retrieval + evidence
layer that feeds those engines.

## Non-goals

- Not a generic chatbot or free-form Q&A product.
- Not a replacement for Archetype, Discovery Advisor, Assumption, Financial,
  Risk, Decision, or Report engines.
- Not a second database or a new multi-tenant product boundary.
- Not enterprise OCR/document-management in MVP (minimal extractors only).

## Approved engines (frozen)

```
Archetype Engine
Discovery Advisor
Assumption Engine
Financial Engine
Risk Engine
Decision Engine
Report Engine
```

Knowledge sits **beside** them and injects evidence-backed context.

---

## 1. Knowledge Layer architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     Knowledge Intelligence Layer                   │
│                                                                    │
│  Ingestion ──► Extraction ──► Normalization ──► Metadata           │
│       │                                              │             │
│       └──────────► Chunking ──► Embeddings ──► Vector Store        │
│                                              │                     │
│                                    Retrieval │ Ranking             │
│                                              ▼                     │
│                                         Evidence Pack              │
│                                              │                     │
│                                    Feedback ◄┘ (study memory)      │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (context only — never replaces engines)
┌──────────────────────────────────────────────────────────────────┐
│ Archetype → Discovery → Assumptions → Financial → Risk → Decision  │
│                         ↑ Knowledge Retrieval injects here         │
│                           Report Engine ← Study Memory write-back  │
└──────────────────────────────────────────────────────────────────┘
```

### Design principles

1. **Advisor, not chat.** Knowledge answers “what have we learned from
   comparable projects?” — not open conversation.
2. **Evidence or silence.** Every knowledge-backed claim must cite a real
   document/chunk/study memory id. No fabricated citations.
3. **Tenant isolation first.** Owner/org scoping on every knowledge row;
   retrieval never crosses tenants.
4. **Reuse persistence.** Same Postgres + SQLAlchemy + Alembic patterns as
   `study_states_v2` / `documents`. No duplicate database.
5. **Deterministic engines stay deterministic.** Knowledge may bias
   assumption estimates and risk notes; financial math remains code.

---

## 2. Data flow

```
Documents (PDF / DOCX / XLSX / study memory)
        ↓
Extraction (text + tables + light heuristics / LLM structured extract)
        ↓
Normalization (sector, country, year, project_type, currency SAR)
        ↓
Metadata (Knowledge Document record)
        ↓
Chunking (semantic sections: assumptions, financials, risks, outcomes)
        ↓
Embeddings (vector per chunk; stored with owner scope)
        ↓
Retrieval (query from new project profile + discovery answers)
        ↓
Evidence ranking (similarity × source trust × recency × archetype fit)
        ↓
Evidence Pack → AI Analysis (Assumption / Risk / Decision prompts)
```

MVP shortcuts (explicit):

- Embeddings: local deterministic hash-projection vectors (no external
  embedding API required). Upgrade path to provider embeddings later.
- OCR: not required for MVP; scanned PDFs may yield empty text and are
  stored with `extraction_status=partial`.
- Parser: `pypdf` + `python-docx` + `openpyxl` text extraction.

---

## 3. Components

| Component | Responsibility | MVP |
|-----------|----------------|-----|
| Document ingestion | Upload + store blob/ref + create Knowledge Document | Yes |
| OCR | Image/PDF OCR | No (stub status) |
| Parser | PDF/DOCX/XLSX → plain text/tables | Yes |
| Metadata extraction | project_type, sector, assumptions, metrics, risks, outcomes | Yes (heuristics + optional LLM) |
| Vector storage | Chunk embeddings in Postgres JSON / ARRAY | Yes (same DB) |
| Knowledge retrieval | Query → ranked chunks + documents | Yes |
| Evidence ranking | Score + filter + dedupe + cite | Yes |
| Knowledge feedback loop | On `REPORT_READY`, write Study Memory | Yes |

### Evidence Pack (runtime contract)

Returned to engines (never raw embeddings to the UI):

```json
{
  "query": "Build 20MW data center in Riyadh",
  "comparable_projects": [
    {
      "document_id": "...",
      "title": "...",
      "project_type": "data_center",
      "similarity": 0.81,
      "source": "tenant_upload|study_memory|market_source"
    }
  ],
  "assumption_hints": [
    {
      "key": "initial_occupancy",
      "suggested_value": "35%",
      "confidence": 0.78,
      "evidence_ids": ["ev_..."],
      "rationale": "Median of 5 similar data center studies"
    }
  ],
  "risk_hints": [],
  "financial_patterns": [],
  "citations": [
    {
      "claim": "Initial occupancy often starts near 30–40% for greenfield colo",
      "source_title": "...",
      "document_id": "...",
      "chunk_id": "...",
      "confidence": 0.78
    }
  ]
}
```

Rules:

- Empty pack is valid (system continues without knowledge).
- UI may show citations; must never show embedding arrays.
- Citations must resolve to stored `document_id` / `chunk_id` / `study_memory_id`.

---

## 4. Connection to existing engines

```
Knowledge Layer
        |
        v
Archetype          (optional: soft hints only; user still confirms)
        |
        v
Discovery Advisor  (unchanged interview UX)
        |
        v
Knowledge Retrieval  ← NEW gate before Assumption Generation
        |
        v
Assumption Engine  (prompt + seeded values include Evidence Pack;
                    each assumption records source provenance)
        |
        v
Financial Engine   (unchanged math; may read knowledge notes as commentary)
        |
        v
Risk Engine        (may append knowledge-backed risk hints with citations)
        |
        v
Decision Engine    (may cite comparable outcomes; never invent studies)
        |
        v
Report Engine      (renders sources; triggers Study Memory write-back)
```

### Assumption source provenance (required)

Every generated assumption must declare one of:

| Source kind | Meaning |
|-------------|---------|
| `user_input` | From discovery / user edit |
| `ai_estimate` | Model estimate without retrieved evidence |
| `knowledge_reference` | Estimate grounded in retrieved evidence |
| `rule_fallback` | Deterministic schema default |

Example UI copy:

```
Assumption: Initial occupancy = 35%
Source: AI estimate based on 5 similar data center studies
Confidence: 78%
References: [Study A title], [Study B title]
```

Extend `Assumption` fields (non-breaking):

- `origin` gains `knowledge_reference` (alongside existing values)
- `knowledge_refs: list[{document_id, chunk_id?, title, similarity}]`
- `knowledge_confidence: float | null` (0–1 when knowledge-backed)

---

## 5. Data model (logical)

Reuse Postgres. New tables under the same Alembic chain. Scope every row
with `owner_id` (+ optional `organization_id`) matching `Document` /
`Project` patterns. V2 studies continue to key by `user_id` string; knowledge
APIs map `current_user.id` → `owner_id`.

### Knowledge Document

| Field | Type | Notes |
|-------|------|-------|
| id | UUID/str PK | |
| owner_id | int FK users | tenant isolation |
| organization_id | int? FK | optional org scope |
| title | str | |
| source | str | upload / url / study_memory / market |
| sector | str? | |
| country | str | default `SA` |
| year | int? | |
| document_type | str | feasibility_study, regulation, market_report, … |
| project_type | str? | maps toward archetype |
| capex | JSON/num? | normalized SAR when known |
| opex | JSON/num? | |
| revenue_model | str/JSON? | |
| assumptions | JSON | extracted assumption map |
| outcome | JSON? | go/no-go, IRR, etc. |
| confidence | float | extraction confidence |
| storage_ref | str? | reuse object storage pattern |
| extraction_status | str | pending/ready/partial/failed |
| visibility | str | `private` (default) \| `org` \| `platform` (admin only) |

### Knowledge Chunk

| Field | Type | Notes |
|-------|------|-------|
| id | UUID/str PK | |
| document_id | FK | |
| owner_id | int | denormalized for isolation filters |
| content | text | searchable |
| embedding | JSON float[] | never exposed to clients |
| metadata | JSON | section, page, keys |
| importance | float | 0–1 |

### Evidence Record

| Field | Type | Notes |
|-------|------|-------|
| id | UUID/str PK | |
| owner_id | int | |
| study_id | str? | v2 study that consumed it |
| claim | text | |
| source_document_id | FK? | |
| source_chunk_id | FK? | |
| source_study_memory_id | FK? | |
| confidence | float | |
| related_project | str? | label |
| created_at | ts | |

### Study Memory

| Field | Type | Notes |
|-------|------|-------|
| id | UUID/str PK | |
| owner_id | int | only visible to owning tenant |
| source_study_id | str | v2 study_id |
| archetype | str | |
| assumptions | JSON | approved set |
| financial_outcome | JSON | snapshot metrics |
| decision | JSON | verdict, conditions |
| risks | JSON | |
| lessons_learned | text/JSON | |
| project_type / sector / country | | for retrieval |
| embedding / summary_text | | retrieval index |

**No duplicate databases.** Tables live beside `study_states_v2` and
`documents`.

---

## 6. API surface (MVP)

Prefix: `/api/v2/knowledge` (auth required)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/documents` | Upload PDF/DOCX/XLSX → ingest |
| GET | `/documents` | List owner-scoped docs |
| GET | `/documents/{id}` | Metadata (no embeddings) |
| POST | `/retrieve` | Body: query, archetype?, study_id? → Evidence Pack |
| POST | `/studies/{study_id}/retrieve` | Study-contextual retrieval |
| GET | `/memories` | List study memories for owner |

Ingest pipeline runs inline for MVP (sync extract + chunk + embed).

---

## 7. Feedback loop

When Decision Engine sets `phase = REPORT_READY`:

1. Snapshot approved assumptions, financial results, risks, verdict,
   conditions.
2. Upsert `Study Memory` for `(owner_id, source_study_id)`.
3. Create summary chunk(s) + embedding for future retrieval.
4. Visibility = `private` (same owner only). Future “share to org” is
   out of scope.

Idempotent: re-running decision refreshes the same memory row.

---

## 8. Security

| Control | Implementation |
|---------|----------------|
| Tenant isolation | All queries filter `owner_id == current_user.id` (admin bypass explicit) |
| Document permissions | Upload/list/get/retrieve scoped; no cross-owner joins |
| No leakage | Retrieval SQL always includes owner predicate; platform corpus only if `visibility=platform` **and** flagged separately (MVP: no shared corpus) |
| Source traceability | Evidence records + assumption `knowledge_refs` |
| Embedding privacy | Embeddings column excluded from all response schemas |
| Audit | Optional `AuditLog` on upload/retrieve (reuse existing) |

Hard rule: a user must never receive another user’s study memory, chunk
text, or citation title from a foreign document.

---

## 9. Testing strategy

Browser E2E (local stack):

1. Cybersecurity company (`services`)
2. Residential compound (`real_estate`)
3. Data center 20MW (`data_center`)

Assert:

- Full flow: Classification → Discovery → Knowledge retrieval →
  Assumptions → Financial → Risk → Decision → Report
- Knowledge references appear when corpus has matches
- Assumptions show sources (`user_input` / `ai_estimate` /
  `knowledge_reference`)
- No fake citations (ids resolve)
- No raw embeddings in network/UI
- Cross-tenant retrieve returns empty for foreign docs

Evidence doc: `docs/evidence/PHASE6_KNOWLEDGE_LAYER_VALIDATION.md`

---

## 10. MVP delivery sequence

1. Architecture (this doc) — done before code
2. Alembic `0027_knowledge_intelligence` + models
3. Ingest/parse/chunk/embed/retrieve services under `ai_engine/knowledge/`
4. API router + wire into assumption generation path
5. Study memory write-back on `REPORT_READY`
6. UI: assumption source lines + knowledge refs (minimal)
7. E2E + evidence

---

## 11. Explicit non-changes

- Discovery Advisor UX remains the interview panel.
- Financial formulas remain in Financial Engine code.
- No chatbot panel in the workspace for Phase 6 MVP.
- Master architecture Wave list unchanged; this is a **Data & source layer**
  enrichment under Wave 1 Professional Feasibility, not a new Wave.
