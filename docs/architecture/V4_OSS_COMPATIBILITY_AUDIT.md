# V4 OSS Compatibility Audit — Phase 7 Gate

**Status:** AUDIT ONLY — no Phase 7 implementation  
**Baseline:** frozen `v3.0.0` @ `33e216e2ed939b065bca0357c3855184e219a68d`  
**Date (UTC):** 2026-09-12  
**Rule:** Do not duplicate existing capability. Do not replace LangGraph or the custom Knowledge Layer.

---

## 1. Purpose

Before any Phase 7 (Saudi Sources / MCP / retrieval hardening) work:

1. Confirm what V3 already owns.
2. Decide ADOPT / HOLD / REJECT for a short OSS candidate list.
3. Sketch the Phase 7 target architecture that **extends** V3 instead of reinventing it.

---

## 2. Inventory of existing V3 capabilities

| # | Capability | Status | Evidence (paths / symbols) | Notes |
|---|------------|--------|----------------------------|-------|
| 1 | LangGraph study orchestration | **PRESENT** | `ai_engine/orchestrator.py` (`StateGraph`, `build_graph`, `run_study_step`); `ai_engine/models/study_state.py`; `requirements.txt` `langgraph>=0.2.0` | Phase-routed graph: discovery → evidence → assumptions → financial → risk → decision. One node per invoke (API-driven advance). **LangGraph is already the study orchestrator.** |
| 2 | Knowledge ingestion | **PRESENT** | `ai_engine/knowledge/ingest.py`; `backend/app/api/v2/knowledge.py`; `backend/app/services/knowledge_service.py`; migrations `0028_knowledge_intelligence.py` | Tenant-scoped upload → extract → chunk → embed → persist `knowledge_documents` / `knowledge_chunks`. |
| 3 | Document extraction | **PRESENT** | `ai_engine/knowledge/extract.py`; deps `pypdf`, `python-docx`, `openpyxl` | PDF / DOCX / XLSX / TXT. Heuristic metadata extract. **No OCR.** Scanned PDFs → empty/partial text. |
| 4 | Chunking | **PRESENT** | `ai_engine/knowledge/chunking.py` `chunk_text(max_chars=900, overlap=120)` | Custom paragraph-aware overlapping chunker. |
| 5 | Embeddings | **PRESENT (MVP)** | `ai_engine/knowledge/embeddings.py` `embed_text`, `EMBED_DIM=256` | **Deterministic local SHA-256 n-gram hash projection** → L2-normalized `float[]`. Not a neural embedding model. Documented upgrade path: swap `embed_text()` only. |
| 6 | Embedding storage + retrieval | **PRESENT (MVP)** | DB: `knowledge_chunks.embedding` / `study_memories.embedding` as **JSON**; `ai_engine/knowledge/retrieve.py` | Full owner-scope load + **Python cosine similarity** ranking (+ importance / quality boosts). No ANN index, no `pgvector`. |
| 7 | Evidence / citations | **PRESENT** | `retrieve.build_evidence_pack`; assumption `knowledge_refs`; `KnowledgeEvidence` rows; `ai_engine/agents/evidence.py` (study evidence claims) | Evidence packs cite `document_id` / `chunk_id` / `study_memory_id`. Separate study-ledger evidence agent also exists. |
| 8 | Similar-project logic | **PRESENT** | `ai_engine/knowledge/similarity.py` `score_project_similarity`, `build_similar_projects` | Multi-factor score → `similarity_pct` + `reasons[]` (retrieval + sector + geography + model + capex + quality). |
| 9 | Study memory | **PRESENT** | `ai_engine/knowledge/memory.py`; model `StudyMemory` / table `study_memories`; columns `conditions`, `influence_summary` (0029) | Written on study completion / report-ready path; retrieved as `kind=study_memory` hits. **Not** LangGraph checkpointer memory. |
| 10 | Langfuse | **PARTIAL** | `requirements.txt` `langfuse>=2.0.0`; `ai_engine/config.py` `get_langfuse()` | Factory returns client if `LANGFUSE_PUBLIC_KEY` set. **No call sites**, no CallbackHandler / traces on LangGraph or LLM paths. Configured stub only. |
| 11 | MCP | **ABSENT** | No `mcp` / `modelcontextprotocol` deps or server/client code | Pricing copy may mention MCP; **no implementation**. |

### Architecture findings — verification

| Finding | Verified? |
|---------|-----------|
| LangGraph is already the study orchestrator | **Yes** |
| Knowledge Layer is custom and already implemented | **Yes** |
| Documents already use pypdf / python-docx / openpyxl | **Yes** (`pypdf`, `python-docx` via `docx`, `openpyxl`) |
| Embeddings are deterministic local hash vectors | **Yes** |
| Embeddings stored as JSON; ranked with Python cosine | **Yes** |
| Study memory already exists | **Yes** |
| Langfuse dependency/config exists but may not be fully instrumented | **Yes** — stub only |
| MCP appears not implemented | **Yes** |

---

## 3. Gaps that Phase 7 actually needs (vs duplication risk)

| Needed for Phase 7 | Already covered by V3? | Real gap |
|--------------------|------------------------|----------|
| Study agent orchestration | LangGraph | None — do not add another agent framework |
| Ingest / chunk / evidence pack / study memory | Custom Knowledge Layer | None — do not replace with LlamaIndex “stack” |
| PDF/DOCX/XLSX text extraction | pypdf / python-docx / openpyxl | Optional gap **only** if complex/scanned docs fail demonstrated fixtures |
| Semantic retrieval at scale | Hash + JSON + O(n) Python cosine | **Scale + quality** gap for larger corpora / better recall |
| Saudi official source connectors + tool protocol | Absent | **MCP + Source Connector Interface** |
| Observability of agent/LLM/tool runs | Langfuse stub | Instrumentation gap (productize existing dep first) |
| Cross-study learning memory | StudyMemory | No Mem0/Zep unless a concrete gap is proven later |

---

## 4. OSS candidate evaluation

### A. `modelcontextprotocol/python-sdk` (`mcp` on PyPI)

| Dimension | Assessment |
|-----------|------------|
| Capability already present? | **No** |
| Exact gap | No standard protocol for exposing Saudi source tools (GASTAT, SAMA, municipal, Open Data, etc.) to the LangGraph research/evidence path |
| Integration point | New thin MCP server(s) wrapping **Source Connector Interface**; LangGraph research/evidence nodes call MCP **tools** (not a second orchestrator) |
| Dependencies | `mcp` (MIT); std transport (stdio/SSE/HTTP as chosen) |
| Vercel impact | Prefer **stdio/local or sidecar** for connectors; avoid long-lived MCP process inside serverless if possible. Tool calls from API route / worker with short timeouts |
| DB impact | None required for protocol; connector caches may use existing tables later |
| Migration risk | **Low** if additive (new package + adapters). **High** if agents are rewritten around MCP |
| License | **MIT** |
| Reuse benefit | Official client/server foundation; ecosystem tool interop; clear boundary for Saudi sources |
| Complexity introduced | Medium (auth, rate limits, provenance, sandboxing per source) |
| **Decision** | **ADOPT** (foundation only — Phase 7) |

---

### B. `pgvector` / `pgvector-python`

| Dimension | Assessment |
|-----------|------------|
| Capability already present? | Retrieval **yes** (custom); vector index / SQL distance **no** |
| Exact gap | JSON float[] + full-scan cosine will not scale; hash embeddings also limit recall quality |
| Integration point | 1) Confirm Postgres host supports `CREATE EXTENSION vector` (Neon/compatible). 2) Alembic: `vector(N)` column (or dual-write). 3) Keep Knowledge Layer API; swap storage/ranking in `embeddings.py` + `retrieve.py`. 4) Optionally upgrade `embed_text()` to a real embedding provider **separately** |
| Dependencies | DB extension `vector`; Python `pgvector` (or raw SQL). Embedding model choice is orthogonal |
| Vercel impact | Low for app bundle; DB plan must enable extension |
| DB impact | Extension + migration; backfill embeddings; index (IVFFlat/HNSW) |
| Migration risk | **Medium** — schema change + backfill. Mitigate with dual-write / feature flag |
| License | pgvector extension: **PostgreSQL License**; Python package typically permissive (verify pinned version at adopt time) |
| Reuse benefit | Standard ANN inside existing Postgres — no new vector SaaS |
| Complexity introduced | Medium (ops, dimension discipline, re-embed when model changes) |
| **Decision** | **HOLD → ADOPT when** (a) extension confirmed on production Postgres **and** (b) corpus size / recall quality justifies migration. Do **not** adopt before connector work if current corpus remains small |

**Gate checklist before ADOPT:**

1. `SHOW server_version;` + `CREATE EXTENSION IF NOT EXISTS vector;` on staging/prod-like DB.
2. Measure chunk count / p95 retrieve latency under owner scope.
3. Decide embedding dimensionality + model (hash MVP can stay temporarily in `vector` column, but neural embeddings unlock most of the value).

---

### C. Unstructured-IO / `unstructured`

| Dimension | Assessment |
|-----------|------------|
| Capability already present? | Text extraction for common office formats **yes** |
| Exact gap | Complex layouts, scanned PDFs, messy HTML — **only if** current extractors fail **demonstrated** fixtures |
| Integration point | Optional fallback inside `ai_engine/knowledge/extract.py` when `extraction_status=partial/failed` |
| Dependencies | Heavy (`unstructured` + often system libs / models). Apache-2.0 |
| Vercel impact | **High risk** — large deps, native libs, cold start; may force a separate worker |
| DB impact | None |
| Migration risk | Low if strictly optional fallback; high if it becomes default path |
| License | **Apache-2.0** |
| Reuse benefit | Better parsing for hard documents |
| Complexity introduced | High (deps, OCR, ops) |
| **Decision** | **REJECT for default path / HOLD as optional fallback** — adopt **only** after failing fixture set proves pypdf/docx/openpyxl insufficient |

---

### D. LlamaIndex

| Dimension | Assessment |
|-----------|------------|
| Capability already present? | Full ingest/chunk/retrieve/evidence layer **yes** (custom) |
| Exact gap | Possibly individual **readers/connectors** for niche file types or remote sources — not a platform gap |
| Integration point | **Only** as isolated reader/connector adapters feeding **existing** `ingest_bytes` / Knowledge Document schema. Never as VectorStoreIndex owning retrieval |
| Dependencies | `llama-index-core` + per-reader packages — MIT/Apache mix; pin carefully |
| Vercel impact | Medium–high if core stack pulled in; keep optional extras |
| DB impact | None if not used as vector store |
| Migration risk | **High** if “replace Knowledge Layer”; **Low** if single reader import |
| License | Generally **MIT** for core (confirm per subpackage) |
| Reuse benefit | Niche connectors only |
| Complexity introduced | High abstraction surface if adopted broadly |
| **Decision** | **REJECT as framework / HOLD for individual connectors** — evaluate a specific reader only when it materially reduces work vs a thin custom connector |

---

### Explicit non-candidates (this gate)

| Candidate | Decision | Reason |
|-----------|----------|--------|
| New agent frameworks (CrewAI, AutoGen, etc.) | **REJECT** | LangGraph already orchestrates studies |
| Mem0 / Zep | **REJECT (for now)** | `StudyMemory` already covers completed-study learning + retrieval; no proven gap |
| Replacing Knowledge Layer with LlamaIndex RAG | **REJECT** | Duplicates Phase 6; breaks evidence/citation contracts |
| Adopting Unstructured as default parser | **REJECT** | Existing extractors sufficient until proven otherwise |

---

## 5. Decision summary

| Candidate | Decision |
|-----------|----------|
| MCP Python SDK | **ADOPT** |
| pgvector | **HOLD** (adopt when extension + scale/quality gate pass) |
| Unstructured | **HOLD / REJECT-default** (optional fallback only after fixture proof) |
| LlamaIndex | **REJECT framework; HOLD selective readers** |
| New agent frameworks | **REJECT** |
| Mem0 / Zep | **REJECT** unless StudyMemory gap is demonstrated |

---

## 6. Phase 7 target architecture (design only)

### 6.1 Saudi source → existing Knowledge Layer

```
Saudi Sources (GASTAT, Open Data, SAMA, municipal, registries, …)
        │
        ▼
Source Connector Interface
  - fetch / normalize / schema map
  - auth + rate limit + retry
        │
        ▼
Source Validation / Provenance
  - source_id, retrieved_at, license, URL, checksum
  - trust tier + freshness
        │
        ▼
Existing Knowledge Ingestion  (ai_engine/knowledge/ingest.py)
  - extract → chunk → embed → persist
        │
        ▼
Existing Evidence Pack        (retrieve.build_evidence_pack)
        │
        ▼
Study Engine (LangGraph)      (assumptions / risk / decision consume citations)
```

**Rules**

- Connectors produce documents/metadata; they do **not** invent a second RAG stack.
- Provenance fields must survive into evidence citations.
- Tenant isolation remains on every knowledge row.

### 6.2 LangGraph research agent → MCP tools → connectors

```
Existing LangGraph Study Orchestrator
  (discovery / evidence / assumptions / …)
        │
        │  tool calls (research / evidence enrichment)
        ▼
MCP Client (official python-sdk)
        │
        ▼
MCP Server(s) — Saudi source tools
        │
        ▼
Source Connector Interface → Validation/Provenance → Knowledge Ingestion
```

**Rules**

- MCP exposes **tools**, not a competing agent runtime.
- LangGraph remains the only study orchestrator.
- Tool outputs that become study evidence must pass through Knowledge / Evidence Pack so citations stay real (`document_id` / `chunk_id`).

### 6.3 Suggested Phase 7 sequencing (non-binding)

1. **Source Connector Interface + provenance schema** (internal, no OSS required).
2. **MCP SDK** server/client for 1–2 pilot Saudi sources.
3. Wire LangGraph evidence/research node to MCP tools.
4. Re-evaluate **pgvector** with measured corpus + extension check.
5. Unstructured / LlamaIndex readers only if fixtures demand them.

---

## 7. Non-goals for Phase 7 kickoff

- No rewrite of LangGraph study graph.
- No replacement of Knowledge Layer.
- No default Unstructured/OCR platform.
- No Mem0/Zep.
- No production code changes in this audit PR beyond this document.

---

## 8. Baseline references

| Item | Reference |
|------|-----------|
| Tag / SHA | `v3.0.0` / `33e216e` |
| Orchestrator | `ai_engine/orchestrator.py` |
| Knowledge package | `ai_engine/knowledge/*` |
| Knowledge architecture | `docs/architecture/KNOWLEDGE_INTELLIGENCE_ARCHITECTURE.md` |
| Migrations | `0028_knowledge_intelligence.py`, `0029_knowledge_intelligence_learning.py` |
| Deps | `requirements.txt` (`langgraph`, `langfuse`, `pypdf`, `python-docx`, `openpyxl`) |

---

## 9. Audit verdict

V3 already owns orchestration (LangGraph), knowledge ingest/chunk/embed/retrieve, evidence citations, similar projects, and study memory. The **only clear green-field OSS adopt** for Phase 7 is the **MCP Python SDK**, to standardize Saudi source tools without duplicating the Knowledge Layer. **pgvector** is the right scale path but gated on DB extension + need. **Unstructured** and **LlamaIndex** stay out of the default architecture unless a demonstrated gap forces a narrow, optional adapter.
