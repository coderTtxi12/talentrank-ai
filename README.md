# Orbio

A production-oriented **hiring stack** for high-volume, operations-sensitive screening—conversational intake, deterministic gates, post-chat sentiment, and **listwise LLM tournaments** aggregated with **Plackett–Luce** so recruiters get the top candidates.

The repo is a **multi-service monorepo**: FastAPI API, two background workers, a candidate **Next.js** chat, and a recruiter **Vite** dashboard, orchestrated with **Docker Compose**. **PostgreSQL** is the system of record; **Redis** holds hot session state; **Chroma** (volume-backed) powers RAG over an employer knowledge base.

> [!IMPORTANT]
> **Video demo (Loom)** — end-to-end walkthrough of screening chat, workers, and listwise + placket-luce ranking:
>
> **[https://www.loom.com/share/760780865a824aca8799c0f81b0a11a0](https://www.loom.com/share/760780865a824aca8799c0f81b0a11a0)**

---

## 🚀 Run locally

**Docker Compose** is the supported path (see **Docker quick start** below). Use your **OpenAI API key**.

| Surface | URL (defaults) |
|--------|----------------|
| Candidate chat (Next.js) | http://localhost:3000 |
| Recruiter dashboard (Vite + nginx) | http://localhost:5174 |
| API | http://localhost:8000 |
| Health | http://localhost:8000/api/v1/health |

You can exercise:

- Multi-turn screening chat with tool calling and KB search  
- Candidate persistence, hard filters, and sentiment worker (`NOTIFY` on completion)  
- Listwise ranking jobs and Plackett–Luce persistence (worker + API)  

---

## 🎯 Overview

**The system:**

1. **Parses screening conversations** through a ReAct-style agent (tools + structured `state_updates`).  
2. **Persists** durable rows in Postgres and keeps **low-latency session state** in Redis.  
3. **Runs deterministic hard filters** after completion—cheap disqualification before optional LLM sentiment.  
4. **Runs listwise mini-tournaments** (orchestrator + sub-agent) over ranking cards loaded from Postgres.  
5. **Fits Plackett–Luce** on observed orders and writes **ranking results** for ops and audit.

---

## 🏗️ Architecture

### System components

```text
┌─────────────────────┐
│  frontend-chat      │  Next.js (candidate)
│  (port 3000)        │  - Screening UI
└──────────┬──────────┘
           │
           │ HTTP (NEXT_PUBLIC_API_URL → API host:port)
           ▼
┌─────────────────────┐
│  FastAPI API        │  Python — chat, candidates, jobs, health
│  (port 8000)        │  - Session + screening services
└──────────┬──────────┘  - Enqueues listwise jobs (Postgres row + NOTIFY)
           │
           ├──────────────────────┬──────────────────────┐
           ▼                      ▼                      ▼
┌─────────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│ Redis               │ │ Chroma (volume) │ │ PostgreSQL          │
│ (port 6380 host)    │ │ RAG embeddings  │ │ (port 5433 host)    │
│ Hot session / TTL   │ │ Company KB      │ │ NOTIFY → workers    │
└─────────────────────┘ └─────────────────┘ └─────────────────────┘
           ▲
           │ also used by API (state, locks, etc.)

┌─────────────────────┐     ┌─────────────────────────────┐
│ sentiment-analysis  │     │ listwise-plackett-luce      │
│ worker              │     │ worker                      │
│ LISTEN completes    │     │ claims listwise jobs        │
└──────────┬──────────┘     └──────────────┬──────────────┘
           │                               │
           └───────────────┬───────────────┘
                           ▼
                  ┌─────────────────┐
                  │  PostgreSQL     │
                  └─────────────────┘

┌─────────────────────┐
│ frontend-dashboard  │  Vite SPA + nginx (recruiter)
│ (port 5174)         │
└──────────┬──────────┘
           │
           └──────────────────────────► FastAPI
```

### Data flow (screening → sentiment → ranking)

1. **Candidate** talks to **frontend-chat**; each turn hits **FastAPI** → **screening agent** (OpenAI + tools).  
2. **Agent** may call **RAG** (`search_company_info`) backed by **Chroma**; **state** updates go to **Redis** (fast) and are reconciled to **Postgres** (durable messages + candidate fields).  
3. On **completion**, Postgres fires **`NOTIFY candidate_completed`** → **sentiment worker**: **hard filters** first; if still eligible, **sentiment LLM** → upsert results.  
4. Operator (or automation) calls **`POST /api/v1/jobs/listwise`** → job row + **`NOTIFY listwise_job_pending`** → **listwise worker** claims job, runs **orchestrator** / **sub-agent** tournaments, **fits PL**, persists **`ranking_results`**.  
5. **Dashboard** calls the same API for recruiter workflows.

### System diagram


```text
                          ┌──────────────────────────────────────┐
                          │           Screening (chat)            │
  Candidate               │                                       │
     │                    │   Next.js chat ──► FastAPI API ──────┤
     └───────────────────►│                         │             │
                          │            Screening agent (LLM)       │
                          │                 │    │    │           │
                          │                 ▼    ▼    ▼           │
                          │            Chroma   Redis  PostgreSQL  │
                          └─────────────────┬──────────────────────┘
                                            │
                    NOTIFY                  │
             candidate_completed            │
                                            ▼
                          ┌──────────────────────────────────────┐
                          │      Sentiment worker               │
                          │  Hard filters ──► (pass) Sentiment   │
                          │                  LLM ───────────────┼──► PostgreSQL
                          └──────────────────────────────────────┘

                          ┌──────────────────────────────────────┐
                          │   Listwise + Plackett–Luce           │
  FastAPI ──► POST        │   NOTIFY listwise_job_pending        │
  /jobs/listwise ────────►│        │                              │
                          │   Listwise worker                    │
                          │        ├─► Orchestrator LLM           │
                          │        ├─► Sub-agent (tournaments)    │
                          │        └─► PL fit ──► ranking_results┼──► PostgreSQL
                          └──────────────────────────────────────┘

  Recruiter dashboard (Vite + nginx) ───────────────────────────► FastAPI
```

---

## 🤖 The screening agent

### Why tool-calling + RAG?

Template-style “map everything to one SQL string” breaks down when:

- The bot must **negotiate** missing fields, explain policy, and stay on-brand.  
- Answers need **grounded company facts** (zones, policy snippets) without stuffing the whole handbook into the prompt.

**Orbio’s approach:** a **ReAct-style loop** (reason → call tools → merge structured `state_updates`) with **OpenAI tool calling**, plus **`search_company_info`** over a **Chroma** collection built from the knowledge base.

### How a turn works (conceptual)

```text
┌─────────────────────────────────────────────────────────────┐
│ 1. User message + rolling context (Redis-capped history)     │
└───────────────────────────────┬─────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Model may call tools: KB search, structured state updates │
└───────────────────────────────┬─────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Services merge fields → Redis (hot), Postgres (durable)  │
└───────────────────────────────┬─────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Response envelope: reply, flags, completion hints        │
└─────────────────────────────────────────────────────────────┘
```

**Why this works better than a single-shot extractor:**

- Handles **multi-turn** clarification and corrections.  
- Keeps **latency-sensitive** state off the critical DB path during the chat.  
- Produces an **auditable** transcript and structured snapshot for downstream workers.

---

## 📊 Listwise ranking + Plackett–Luce

### Why not only fixed weights?

In the real world there is **no stable, perfect score or weight formula**: vacancy urgency, service zones, and “who we need on the phone today” **change every week**; trade-offs between dimensions (availability vs. start date vs. experience) are **not honestly linear**; and any fixed set of coefficients eventually **lies** the moment operations or policy shifts.

A spreadsheet-style score is still useful as a **cheap filter**, but it cannot track that moving target without constant manual retuning.

**Listwise + PL** sidesteps “the one true formula” by treating the LLM as a source of **noisy group comparisons** over small pools; many tournaments plus **Plackett–Luce** fitting yield **stable latent utilities** and a traceable path from raw orders to ranking, grounded in the **current** job context in the prompt. Methodology and weight-vs-PL comparison.

### Cost / control tradeoff

- **Pros:** Adapts when the vacancy narrative changes; avoids frozen weights that go stale as soon as reality moves.  
- **Cons:** More **LLM spend** than a hand-tuned formula; at scale you may use a **hybrid** (cheap pre-score → PL only on top *N*) as described in the same doc.

---

## 🔄 Async workers: Postgres `NOTIFY`

### The problem

The API should not **block** on sentiment or listwise work; candidates still expect snappy chat responses.

### The solution

- **Durable intent** lives in **Postgres** (job row, candidate status transitions).  
- Triggers emit **`NOTIFY`** so workers **wake** without Redis as the primary task queue.  
- Workers **claim** jobs with **conditional updates** to avoid double execution.

### Tradeoff

`NOTIFY` is a **signal**, not a replayable queue.

---

## ⚙️ Docker quick start (Compose)

Use this path only—frontends and API are built and run by Compose; no separate `npm run dev` steps.

### Prerequisites

- **Docker** and **Docker Compose**  
- **OpenAI API key** in `backend/.env` (embeddings for the KB loader use the same settings as the app)

### Steps

```bash
# 1. Root: ports, LOG_LEVEL, NEXT_PUBLIC_API_URL (browser → API), …
cp .env.example .env

# 2. Backend: secrets and model names (Compose overrides DATABASE_URL / REDIS_URL inside containers)
cp backend/.env.example backend/.env
# Set at least OPENAI_API_KEY and OPENAI_MODEL. For RAG embeddings the loader uses
# OPENAI_EMBEDDING_MODEL (default: text-embedding-ada-002) if you do not override it.

# 3. Start the stack
docker compose up --build

# 4. Database schema (wait until `api` is healthy)
docker compose exec api alembic upgrade head

# 5. Load the knowledge base into Chroma (RAG / search_company_info)
#    Runs in the `api` container: same deps, .env, and /app/.chroma volume as the live API
docker compose exec api python scripts/load_grupo_sazon_kb.py
```

### Default ports (host)

| Service | Port | Description |
|--------|------|-------------|
| API | 8000 | FastAPI |
| Candidate frontend | 3000 | Next.js |
| Recruiter dashboard | 5174 | Vite behind nginx |
| PostgreSQL | 5433 | Mapped from container 5432 |
| Redis | 6380 | Mapped from container 6379 |

Workers (`sentiment-analysis-worker`, `listwise-plackett-luce-worker`) start with the same compose file; they read `backend/.env`, with `DATABASE_URL` pointed at the `postgres` service on the internal network.

## 📁 Project structure

```text
orbio/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── .env.example
│   ├── alembic/                    # Migrations
│   ├── app/
│   │   ├── api/routes/             # chat, candidates, jobs, ranking, health, …
│   │   ├── core/                   # config, database, redis, logging
│   │   ├── models/                 # Pydantic + SQLAlchemy
│   │   ├── schemas/                # Request/response DTOs
│   │   ├── services/               # chat, screening_state, vector_store, …
│   │   └── workers/
│   │       ├── sentiment_analysis/
│   │       └── listwise_plackett_luce/
│   ├── docs/                       # Allowlisted docs + KB text (.gitignore)
│   ├── prompts/                    # Prompts + schema hints
│   ├── scripts/
│   │   ├── load_grupo_sazon_kb.py  # Chroma / KB loading
│   │   └── test_semantic_search.py
│   └── workers/                    # Worker Docker entrypoints
├── frontend-chat/                  # Next.js candidate app
├── frontend-dashboard/             # Vite recruiter app (+ nginx in Docker)
└── …
```

---

## 📝 Key scripts and operations

Migrations and KB loading are in **Docker quick start** above.

### Semantic search smoke test (optional)

After loading the KB, from the host:

```bash
docker compose exec api python scripts/test_semantic_search.py
```

Useful to sanity-check retrieval against the Chroma collection.

---

## 🛠️ Technology stack

| Layer | Choices |
|--------|---------|
| API | **FastAPI**, **SQLAlchemy**, **Alembic**, **Pydantic** |
| LLMs | **OpenAI** (chat + tools + worker-specific prompts) |
| Data | **PostgreSQL 16**, **Redis 7**, **Chroma** (local volume in compose) |
| Candidate UI | **Next.js** |
| Recruiter UI | **Vite** + **nginx** in Docker |
| Orchestration | **Docker Compose** |
| LLM observability | **LangSmith** (optional)—traces for AI Agents, RAG tools, sentiment, and listwise (`LANGSMITH_*` in `backend/.env`; see [`backend/.env.example`](backend/.env.example)) |

### LLM observability (LangSmith)

Screening chat, RAG tool calls, sentiment, and listwise orchestration are **multi-step LLM workflows**. **LangSmith** gives you **end-to-end traces** so you can see **which** model turn, tool payload, or worker span misbehaved—not only the final HTTP error.

It integrates with the OpenAI clients in this repo via `wrap_openai` and `@traceable`: **latency**, **token usage**, **nested spans** across the agent loop and workers, and **prompt/output inspection** for debugging regressions or comparing model versions—without hosting your own trace store. Enable it with `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, and `LANGSMITH_PROJECT` (and related vars) as in `backend/.env.example`.

### Why these choices?

- **FastAPI:** typed routes, quick iteration, good fit for LLM-backed services and health checks.  
- **Postgres + NOTIFY:** simple async handoff without mandatory cloud queue. 
- **Redis on the hot path:** session latency and auxiliary primitives (locks, idempotency) without overloading OLTP for every token.  
- **Separate worker images:** different scaling and failure modes for sentiment vs listwise CPU/IO profiles.  
- **LangSmith off by default:** zero cost and no external dependency until you opt in for development or staging visibility into LLM behavior.

---

## 🔮 Future improvements

- Replace or supplement `NOTIFY` with a **durable queue** for high-throughput deployments  
- **Managed vector store** if Chroma on a single volume becomes a bottleneck  
- **Hybrid ranking** (cheap linear pre-rank → PL on top *N*) for cost/latency  
- **Metrics / APM** (e.g. Prometheus, OpenTelemetry) for RED dashboards alongside LangSmith

---

## 📚 More documentation

| Topic | Document |
|--------|-----------|
| PostgreSQL schema & relationships | [`backend/docs/POSTGRESQL_DESIGN.md`](backend/docs/POSTGRESQL_DESIGN.md) |
| Phase 1 screening flow (stages, agents, reflection) | [`backend/docs/Phase1_Conversation_Design.md`](backend/docs/Phase1_Conversation_Design.md) |
| Employer public KB text (RAG / prompts) | [`backend/docs/GRUPO_SAZON_PUBLIC_INFO_ES.txt`](backend/docs/GRUPO_SAZON_PUBLIC_INFO_ES.txt) |
| Listwise + Plackett–Luce methodology | [`backend/docs/listwise+plackett-luce.pdf`](backend/docs/listwise+plackett-luce.pdf) |

Other repo docs:

| Topic | Document |
|--------|-----------|
| HTTP conventions | [`backend/ENDPOINT_RULES.md`](backend/ENDPOINT_RULES.md) |
