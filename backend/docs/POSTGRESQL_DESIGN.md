# PostgreSQL Design

Persistent store for the Grupo Sazón screening platform. Hot-path conversation
state lives in Redis; PostgreSQL
holds everything that must survive process restarts, be queried analytically,
or be auditable under GDPR / EU AI Act / NYC LL-144.

> **Driver / version:** PostgreSQL 16 + `psycopg` 3 (sync) via SQLAlchemy 2.0.
> **Migrations:** Alembic — chain `0001` … `0006` (see [§2 Phases](#2-evolution-in-phases)).
> **Schema source of truth:** [`backend/app/models/database.py`](../app/models/database.py).

---

## 1. Design principles

- **PostgreSQL-native types.** `UUID` PKs (server-generated with `gen_random_uuid()`), `TIMESTAMPTZ` everywhere, `JSONB` for evolving payloads, `ARRAY` for short lists, native `ENUM` for closed sets.
- **Catalogs are tables, not enums.** `service_areas` and `service_zones` evolve without touching Python enums.
- **One table per concern.** `conversations` ≠ `messages` ≠ `jobs` ≠ `ranking_*`.
- **License is a boolean.** Captured via chat (`drivers_license: bool`). **No image, no document, no upload table.** Keeps the system out of GDPR “special category” territory and removes a large class of storage / abuse risk.
- **Workers coordinate through Postgres.** Rows in `jobs` are claimed with conditional updates / `SELECT … FOR UPDATE SKIP LOCKED` where appropriate; **sentiment** and **listwise** paths additionally use **`NOTIFY`** channels (`candidate_completed`, `listwise_job_pending`) so workers wake without polling (see migrations `0002`, `0004` / `0005`).
- **Auditability first.** Each ranking decision should remain traceable from `ranking_runs` + `ranking_tournaments` + `ranking_results.decision_trace` (plus orchestrator summaries where persisted).

---

## 2. Evolution in phases

The schema was **not** frozen at `0001`: later revisions reflect async workers, finer-grained candidate lifecycle, and listwise orchestration persistence.

| Revision | Intent |
|----------|--------|
| **`0001_initial_schema`** | Baseline: catalogs (`service_areas`, `service_zones`), `vacancies`, `candidates`, `conversations` / `messages`, generic **`jobs`** queue (`sentiment`, `ranking`, `nudge`), `sentiment_results`, ranking tables (`ranking_runs`, `ranking_tournaments`, `ranking_results`), `security_events`, `nudges`, `audit_log`. Candidate geography is stored as free-text **`city_zone`** plus slots in **`captured_data`** — there is **no** FK from `candidates` into `service_areas`. |
| **`0002_candidate_completed_notify`** | After **`candidates.is_completed`** flips to true, Postgres **`NOTIFY`s** `candidate_completed` so the sentiment worker can **`LISTEN`** instead of scanning the table. |
| **`0003_candidate_status_pipeline_stages`** | Extends **`candidate_status_enum`** with intermediate stages: `hard_filter`, `sentiment_analysis`, `listwise`, `plackett_luce`, reflecting the multi-step pipeline after chat. |
| **`0004_listwise_job_type_and_notify`** (+ **`0005`** repair) | Adds **`listwise`** to **`job_type_enum`** and a trigger that **`NOTIFY`s** `listwise_job_pending` on insert of listwise jobs for the listwise worker. |
| **`0006_ranking_run_listwise_persistence`** | **`ranking_runs.vacancy_id`** becomes **nullable** (listwise jobs may run without a vacancy); adds **`ranking_runs.orchestrator_output`** and **`ranking_tournaments.llm_trace`** JSONB columns for orchestrator / sub-agent audit data. |

Downstream code (status transitions, worker entrypoints) should be read **together** with this chain: behaviors that look “implicit” often come from triggers or NOTIFY listeners added after the initial revision.

---

## 3. Relationships (foreign keys)

This section replaces the old ASCII entity diagram: it describes **how rows reference each other** as implemented today.

### Catalogs and vacancies

- **`service_zones`** → **`service_areas`**: each zone belongs to exactly one area (`area_id`, `ON DELETE CASCADE`).
- **`vacancies`** → **`service_areas`**: each vacancy is anchored to one area (`area_id`). Operational fields (`urgency`, `critical_shifts`, `ideal_start_days`, …) are what listwise prompts treat as **vacancy context**.

### Candidates — attachment point for chats only

- **`candidates`** carries screening fields (`drivers_license`, **`city_zone`** text, **`platforms`** as `varchar[]`, enums for availability / schedule, etc.). **There is no foreign key** from `candidates` to `service_areas` / `service_zones`; alignment with catalogs is enforced in application logic and hard filters, not via relational joins on the candidate row.
- **`conversations`** → **`candidates`** (optional `candidate_id`, `ON DELETE SET NULL`): every durable chat session may point at a candidate once registration links them.
- **`conversations`** → **`vacancies`** (optional `vacancy_id`, `ON DELETE SET NULL`): ties a screening session to a specific opening when that is known.

### Conversation spine: messages and satellites

- **`messages`** → **`conversations`** (`conversation_id`, `ON DELETE CASCADE`): append-only transcript; `tool_calls` JSONB holds ReAct-style tool payloads.
- **`sentiment_results`** → **`conversations`** (`conversation_id` **unique**, `ON DELETE CASCADE`): **at most one row per conversation**; re-runs upsert the same logical result.
- **`nudges`** → **`conversations`** (`ON DELETE CASCADE`): scheduled re-engagement rows scoped to the session.
- **`security_events`** → **`conversations`** and **`messages`** (both optional FKs, `ON DELETE SET NULL`): records reflection / abuse events while allowing parent rows to be removed or anonymized according to policy.

### Worker queue

- **`jobs`** has **no foreign keys**. Intent is carried in **`payload`** (e.g. `conversation_id`, `vacancy_id`, job id strings). Types include **`sentiment`**, **`ranking`**, **`nudge`**, and **`listwise`** (added in `0004`). This keeps enqueueing cheap and avoids circular dependencies; **integrity is enforced by workers** reading valid ids.

### Ranking (Listwise + Plackett–Luce)

- **`ranking_runs`** → **`vacancies`** (`vacancy_id` **nullable** since `0006`): a run may be tied to a vacancy or represent a job-scoped execution with context only in payload / orchestrator output.
- **`ranking_tournaments`** → **`ranking_runs`** (`run_id`, `ON DELETE CASCADE`): one row per listwise LLM call; **`candidate_ids`** / **`llm_ranking`** are **UUID arrays**, not FK constraints — the model can output orderings that are validated in code.
- **`ranking_results`** → **`ranking_runs`** (`ON DELETE CASCADE`) and **`candidates`** (`candidate_id`): one row per `(run, candidate)` with PL utilities, positions, and **`decision_trace`**. **`(run_id, candidate_id)`** is unique.

### Audit

- **`audit_log`** stores **`entity_type` + `entity_id`** as opaque fields (optional UUID) **without FKs**, so any table can emit a row without migration churn.

### Conventions summary

- **Cascade** on children that should disappear with the parent (`messages`, `ranking_*` children of a run, `nudges`).
- **`SET NULL`** where you may keep history if a person or vacancy link is removed (`conversation.candidate_id` / `vacancy_id`, `security_events` parents).
- **`session_id`** on `conversations` is **not** a FK: it is the shared key with **Redis** for the hot path (see [`REDIS_DESIGN.md`](./REDIS_DESIGN.md)).

---

## 4. Table reference (concise)

### Catalogs

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `service_areas` | Cities (ES + MX) | `code` (unique), `city`, `country`, `active` |
| `service_zones` | Sub-zones inside a city | `area_id` → `service_areas`, `name` (unique per area) |

### Core domain

| Table | Purpose |
|-------|---------|
| `vacancies` | Operational opening: `area_id`, `urgency`, `critical_shifts`, `ideal_start_days`, `headcount`, `status`, … |
| `candidates` | One person screened: contact, `drivers_license`, `city_zone`, `platforms[]`, enums, **`status`** (full pipeline per `0003`), `is_completed`, `slot_uncertain`, … |
| `conversations` | Durable session: `session_id`, optional `candidate_id` / `vacancy_id`, `captured_data` JSONB, `status`, timestamps |
| `messages` | One turn per row: `role`, `content`, `tool_calls`, `security_flagged`, … |

### Workers and post-screening

| Table | Purpose |
|-------|---------|
| `jobs` | Generic queue: `job_type` (`sentiment` \| `ranking` \| `listwise` \| `nudge`), `status`, `payload`, retries, `run_after`, locks |
| `sentiment_results` | 1:1 with `conversations`: `sentiment`, `confidence`, `signals`, `model_version` |
| `ranking_runs` | One ranking execution: optional `vacancy_id`, `rubric_version`, `pool_size`, `top_n`, `orchestrator_output`, … |
| `ranking_tournaments` | Per listwise call: arrays of candidate UUIDs, `llm_ranking`, `confidence`, `llm_trace`, … |
| `ranking_results` | Per candidate in a run: `utility`, `posterior_variance`, `rank_position`, `tournaments_seen`, `decision_trace` |

### Safety and compliance

| Table | Purpose |
|-------|---------|
| `security_events` | Reflection agent / abuse: `attack_type`, `severity`, optional `conversation_id` / `message_id`, `blocked`, `extra` |
| `nudges` | Re-engagement schedule per `conversation_id` |
| `audit_log` | Append-only cross-entity trail (`entity_type`, `entity_id`, `action`, `actor`, `payload`) |

Indexes and partial indexes (e.g. **`ix_jobs_pending_runafter`** for pending jobs by type) are defined in **`0001`** and unchanged unless a later revision says otherwise.

---

## 5. Conventions

- **Primary keys.** UUID v4, server-generated.
- **Timestamps.** Always `TIMESTAMPTZ`. `created_at` defaults to `now()`. `updated_at` uses both `server_default` and `onupdate=func.now()` in SQLAlchemy where present.
- **Soft deletes.** Not used. Closed/abandoned/disqualified states are explicit on `status`.
- **JSONB columns** never replace first-class columns when the field is queried heavily in `WHERE`; they store snapshots, traces, sentiment signals, rubric metadata, security extras, audit payloads.
- **Enums.** Created in baseline migrations and extended with **`ALTER TYPE … ADD VALUE`** where PostgreSQL requires it (`0003`, `0004`); removals are intentionally avoided.

---

## 6. Migrations

```bash
# from backend/
alembic upgrade head
```

- `alembic/env.py` reads `settings.DATABASE_URL` (so secrets stay out of `alembic.ini`).
- Apply **all** revisions through **`0006`** for listwise NOTIFY + nullable vacancy ranking runs + orchestrator persistence.

---

## 7. Containerization

`docker-compose.yml` ships a `postgres:16-alpine` service with a health check (`pg_isready`) and a persistent named volume (`pg_data`). Defaults are overridable via env vars (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`).

```bash
docker compose up -d postgres
alembic upgrade head
```

---

## Troubleshooting

### Connecting as user `postgres`

Our [`docker-compose.yml`](../docker-compose.yml) sets `POSTGRES_USER` (default **`app`**) — there is **no** `postgres` superuser unless you add one. GUI tools (TablePlus, DBeaver, etc.) must use:

- **User:** `app`
- **Password:** same as `POSTGRES_PASSWORD` (default `app` in compose)
- **Host/port/db:** `localhost`, mapped host port (default **5433** → container `5432`), database `app`

Attempts to log in as `postgres` fail with “password authentication failed” / “Role postgres does not exist.”

### `DuplicateObject: type "country_enum" already exists`

This happened when Alembic **created ENUM types** at the start of revision `0001`, then **SQLAlchemy emitted `CREATE TYPE` again** when creating the first table. Revision `0001` was updated so column ENUMs use `create_type=False`; types are created only once.

If your DB is **half-migrated** (types exist but tables are missing or `alembic_version` was never stamped):

1. **Dev-only reset (recommended):** wipe the volume and rerun migrations:

   ```bash
   docker compose down -v
   docker compose up -d postgres
   alembic upgrade head
   ```

2. **Manual cleanup:** connect as user `app`, drop leftover objects in schema `public`, then `alembic upgrade head`, or `alembic stamp` only if the schema already matches head exactly (advanced).

---

## 8. What is *not* in PostgreSQL

- **Conversation hot state** (active session, recent slots, last LLM tool call) → Redis.
- **Recent message history** for in-flight chats → Redis (mirrored into `messages` on flush).
- **Rate limiting / nudge cooldowns** → Redis.
- **RAG embeddings / company knowledge** → Chroma.
- **Captured candidate slots before flush** → Redis, then committed here.

This split keeps Postgres focused on durable, queryable, auditable data.
