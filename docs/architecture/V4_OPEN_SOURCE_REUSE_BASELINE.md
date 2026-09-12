# V4 Open Source Reuse Baseline

**Status:** Architecture preparation only — **no feature implementation**  
**V3 status:** **CLOSED and FROZEN**  
**Verified release:** `v3.0.0`  
**Frozen commit:** `33e216e2ed939b065bca0357c3855184e219a68d`  
**Date (UTC):** 2026-09-12  

### Binding rules

1. Do **not** perform any further V3 preview, release-candidate, or deployment work.
2. Do **not** implement Phase 7+ functionality in this document’s PR — paths below are **ownership reservations**.
3. External libraries sit **behind our adapters/interfaces** only.
4. No external source may bypass the existing Knowledge Layer.
5. No external tool may directly mutate Financial, Risk, or Decision engine outputs.
6. V3 core remains regression-protected.

Related prior gate (audit): `docs/architecture/V4_OSS_COMPATIBILITY_AUDIT.md` (when merged). This baseline **locks reuse decisions** and **code ownership**.

---

## 1. KEEP EXISTING (do not replace)

| Layer | Keep | V3 home (frozen) | Reuse rule |
|-------|------|------------------|------------|
| Study orchestration | **LangGraph** | `ai_engine/orchestrator.py`, `ai_engine/models/study_state.py` | Only orchestrator. Extend with nodes/tools; do not add another agent framework. |
| Observability | **Langfuse** | `ai_engine/config.py` `get_langfuse()`; `requirements.txt` | Productize existing stub (instrumentation). Do not swap vendors. |
| Knowledge / RAG | **Existing Knowledge Layer** | `ai_engine/knowledge/*`; `backend/app/api/v2/knowledge.py`; `backend/app/services/knowledge_service.py`; tables `knowledge_documents`, `knowledge_chunks`, `knowledge_evidence` | Own ingest, chunk, embed, retrieve, evidence pack. Never replace with LlamaIndex/Haystack/etc. |
| Cross-study learning store | **Existing Study Memory** | `ai_engine/knowledge/memory.py`; `StudyMemory` / `study_memories` | Do not add Mem0/Zep unless a proven gap appears later. |
| API | **Existing FastAPI backend** | `backend/app/` | New V4 surface area mounts under reserved packages below. |
| UI | **Existing Next.js frontend** | `apps/web/` (or current web app root on frozen tree) | UX patterns may be inspired by OpenBcon; no AGPL copy. |
| Data | **Existing PostgreSQL** | SQLAlchemy + Alembic | Prefer same DB; pgvector only as POC behind gates. |

---

## 2. PHASE 7 — ADOPT (with constraints)

### 2.1 `modelcontextprotocol/python-sdk` (`mcp`)

| Field | Decision |
|-------|----------|
| Role | MCP **protocol / server / client foundation only** |
| Adopt? | **YES** |
| Own behind | `backend/app/integrations/mcp/` |
| Must not | Become a second agent runtime; mutate financial/risk/decision state directly |
| Feeds | Research tools → Source Connectors → Knowledge Layer |

### 2.2 `vancoder1/ai-business-planner` (selective pattern reference)

| Field | Decision |
|-------|----------|
| Role | **Pattern reference only** from its MCP research implementation |
| Adopt code? | **NO** — do not import its Node architecture or vendor the repo |
| Patterns to mirror (re-implement in Python) | `search_web` pattern; `read_page` pattern; caching; content cleanup; **source-first research policy** |
| Own behind | `backend/app/integrations/research/` (+ later `ai_engine/research/` in Phase 8) |
| Interface rule | Equivalent behavior behind **our** existing Python/FastAPI interfaces and MCP tool schemas |

### 2.3 `pgvector/pgvector` + `pgvector` Python bindings

| Field | Decision |
|-------|----------|
| Role | Scalable vector similarity **inside existing Postgres** |
| Adopt? | **POC first** — promote only if extension works on our Postgres **and** regression/performance gates pass |
| Own behind | Knowledge Layer storage/retrieve adapters (no parallel vector product) |
| Replace? | JSON float[] + Python cosine **only after** dual-run confidence |
| Must not | Force a new database or break tenant isolation |

### 2.4 `Unstructured-IO/unstructured`

| Field | Decision |
|-------|----------|
| Role | **Fallback extractor only** |
| Adopt? | Only for document types where existing `pypdf` / `python-docx` / `openpyxl` extraction **demonstrably fails** (fixture-proven) |
| Own behind | Optional branch in Knowledge extract adapter |
| Must not | Become default parse path or pull OCR platform into core request path without an explicit worker decision |

### 2.5 LlamaIndex

| Field | Decision |
|-------|----------|
| Role | **Connectors / readers only** when a specific connector materially reduces effort |
| Adopt? | Selective, case-by-case |
| Must not | Replace Knowledge Layer, ownership of chunk/embed/retrieve, or Evidence Pack contracts |

---

## 3. REFERENCE ONLY

### `adm73/OpenBcon`

| Allowed inspiration | Forbidden |
|---------------------|-----------|
| Source administration UX | Copying AGPL code |
| Data source sync UX | Relicensing / vendoring AGPL modules into our tree |
| Readiness workflow patterns | Replacing our Study Engine UX wholesale |
| Matching patterns | AGPL-derived backend logic |
| Strategic report UX patterns | Dual-licensing contamination |

UI/product patterns only. Implementation remains first-party under our license.

---

## 4. DO NOT ADD

Explicit rejects for V4 preparation:

- CrewAI  
- AutoGen  
- Haystack  
- Mem0  
- Zep  
- Another RAG framework (as platform)  
- Another agent framework (LangGraph stays sole orchestrator)  

---

## 5. Complete reuse matrix

| Component | Decision | Mode | Owns / integrates at | Touches V3 core? |
|-----------|----------|------|----------------------|------------------|
| LangGraph | KEEP | Runtime | `ai_engine/orchestrator.py` | Already core — extend only |
| Langfuse | KEEP | Instrument | `ai_engine/config.py` → call sites later | Additive traces |
| Knowledge Layer | KEEP | Platform | `ai_engine/knowledge/*` | Protected |
| Study Memory | KEEP | Platform | `ai_engine/knowledge/memory.py` | Protected |
| FastAPI | KEEP | Platform | `backend/app` | Mount new routers |
| Next.js | KEEP | Platform | Web app | Additive UX |
| PostgreSQL | KEEP | Platform | Existing DB | Optional extension |
| MCP python-sdk | ADOPT | Foundation | `backend/app/integrations/mcp/` | New package only |
| vancoder1/ai-business-planner | PATTERN | Re-implement | `backend/app/integrations/research/` | No Node import |
| pgvector | POC→ADOPT? | Storage adapter | Knowledge retrieve/embed path | Gated migration |
| unstructured | FALLBACK | Extract adapter | Knowledge extract | Optional |
| LlamaIndex readers | OPTIONAL | Connector adapter | Source/ingest adapters | Narrow only |
| OpenBcon | REFERENCE | UX patterns | Frontend design notes | No code copy |
| CrewAI / AutoGen / Haystack / Mem0 / Zep | REJECT | — | — | — |

---

## 6. Code ownership & integration paths (reserved)

Paths are **reserved ownership**. Creating empty packages is optional; **implementing behavior is out of scope** for this baseline commit.

### Phase 7 — Saudi sources + MCP + research adapters (backend)

```
backend/app/integrations/mcp/           # official SDK server/client wrappers
backend/app/integrations/research/      # search_web / read_page / cache / cleanup adapters
backend/app/integrations/sources/       # Saudi source connectors (GASTAT, Open Data, …)
backend/app/services/source_registry_service.py
backend/app/api/v2/sources.py           # source admin / sync / readiness APIs
```

### Phase 8 — Research agent nodes (engine)

```
ai_engine/research/
ai_engine/research/nodes/               # LangGraph research nodes calling MCP tools
```

### Phase 9 — Benchmarks

```
ai_engine/benchmarks/
backend/app/services/benchmark_service.py
```

### Phase 10 — Decision intelligence

```
ai_engine/decision_intelligence/
```

### Phase 11 — Committee

```
ai_engine/committee/
```

### Phase 12 — Learning loop extensions

```
ai_engine/learning/                     # extends Study Memory; does not replace it
```

---

## 7. Mandatory architecture

### 7.1 Source → Knowledge → Study

```
Saudi Source
    → Source Connector
    → Validation / Provenance
    → Existing Knowledge Layer
    → Evidence Pack
    → Existing Study Engine
```

### 7.2 Research via LangGraph + MCP

```
Existing LangGraph
    → Research Agent (Phase 8 nodes)
    → MCP Tools (Phase 7 integrations/mcp)
    → Source Connectors (Phase 7 integrations/sources)
    → (back through Validation / Provenance → Knowledge Layer)
```

### 7.3 Hard invariants

1. **No external source bypasses Knowledge Layer** — connector output becomes knowledge documents/chunks (or explicit rejected/quarantined records), then evidence.
2. **No external tool directly modifies Financial, Risk, or Decision output** — tools may supply evidence/context only; engines remain authoritative.
3. **Adapters own OSS** — `mcp`, pgvector client, unstructured, LlamaIndex readers never leak into engine math modules.
4. **V3 regression shield** — Financial Trust, Owner Gate, and knowledge unit tests remain green before any Phase 7 merge.

---

## 8. Conflicts with current V3 code

| Topic | Conflict / tension | Resolution in V4 |
|-------|--------------------|------------------|
| Embeddings | V3 uses hash vectors in **JSON** + Python cosine | Keep until pgvector POC + gates; dual-write if migrating |
| Extraction | V3 `pypdf` / `python-docx` / `openpyxl` cover MVP types | Unstructured only after fixture failure proof |
| Langfuse | Dependency present but **uninstrumented** | Instrument existing helper; do not add a second APM |
| MCP marketing vs code | Product copy may imply MCP; **no implementation** | Real MCP lives only under `integrations/mcp/` |
| Study Memory vs “memory products” | StudyMemory already stores conditions / influence | Reject Mem0/Zep; extend via `ai_engine/learning/` later |
| Agent frameworks | LangGraph already orchestrates | Reject CrewAI/AutoGen/etc. |
| RAG frameworks | Custom Knowledge Layer is RAG | Reject Haystack / LlamaIndex-as-platform |
| vancoder1/ai-business-planner | Node-oriented reference | Re-implement `search_web` / `read_page` / cache / cleanup / source-first patterns in Python adapters only |
| OpenBcon | AGPL | UX reference only — no code copy |
| Path reservations | `backend/app/integrations/**` **does not exist** on V3 | Create when Phase 7 starts; absent today is expected |

**No blocking code conflict** prevents Phase 7 prep. Main risks are **duplication** (second RAG/agent stack) and **license** (OpenBcon AGPL) — both forbidden by this baseline.

---

## 9. Already partially implemented? (approved OSS)

| Approved OSS / pattern | Already in V3? | Detail |
|------------------------|----------------|--------|
| MCP python-sdk | **No** | Absent from deps and code |
| vancoder1/ai-business-planner patterns (`search_web`, `read_page`, caching, content cleanup, source-first) | **No** as MCP research suite | Generic HTTP/LLM usage may exist elsewhere; **not** these MCP research adapters |
| pgvector | **No** | JSON embeddings only; no `vector` type / extension usage |
| unstructured | **No** | Not in requirements; extractors are pypdf/docx/openpyxl |
| LlamaIndex connectors | **No** | Zero LlamaIndex usage |
| LangGraph | **Yes — full** | Keep |
| Langfuse | **Yes — partial** | Dep + `get_langfuse()` only |
| Knowledge Layer | **Yes — full MVP** | Keep |
| Study Memory | **Yes — full** | Keep |

---

## 10. Out of scope for this commit

- Installing MCP / pgvector / unstructured / LlamaIndex packages  
- Creating the reserved directories or API routes  
- Connector implementations  
- Research agent nodes  
- DB migrations for `vector` columns  
- Frontend source-admin screens  

Next engineering step after acceptance: Phase 7 scaffold PRs that create reserved packages and interfaces **without** changing Financial / Risk / Decision math.

---

## 11. Sign-off checklist

- [x] V3 frozen commit identified: `33e216e2ed939b065bca0357c3855184e219a68d`  
- [x] Keep list locked (LangGraph, Langfuse, Knowledge, Study Memory, FastAPI, Next.js, Postgres)  
- [x] Phase 7 adopt list locked with constraints  
- [x] Reject list locked  
- [x] Ownership paths reserved for Phases 7–12  
- [x] Mandatory source/research architectures recorded  
- [x] No implementation in this baseline commit  
