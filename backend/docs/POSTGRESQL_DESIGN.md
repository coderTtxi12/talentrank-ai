# PostgreSQL Design

Persistent store for the Grupo Sazón screening platform. Hot-path conversation
state lives in Redis (see [`REDIS_DESIGN.md`](./REDIS_DESIGN.md)); PostgreSQL
holds everything that must survive process restarts, be queried analytically,
or be auditable under GDPR / EU AI Act / NYC LL-144.

> **Driver / version:** PostgreSQL 16 + `psycopg` 3 (sync) via SQLAlchemy 2.0.
> **Migrations:** Alembic — initial revision `0001_initial_schema.py`.
> **Schema source of truth:** [`backend/app/models/database.py`](../app/models/database.py).

---

## 1. Design principles

- **PostgreSQL-native types.** `UUID` PKs (server-generated with `gen_random_uuid()`), `TIMESTAMPTZ` everywhere, `JSONB` for evolving payloads, `ARRAY` for short lists, native `ENUM` for closed sets.
- **Catalogs are tables, not enums.** `service_areas`, `service_zones`, `platforms` change without migrations.
- **One table per concern.** `conversations` ≠ `messages` ≠ `jobs` ≠ `ranking_*`.
- **License is a boolean.** Captured via chat (`drivers_license: bool`). **No image, no document, no upload table.** Keeps the system out of GDPR “special category” territory and removes a large class of storage / abuse risk.
- **Workers consume jobs from Postgres** with `SELECT ... FOR UPDATE SKIP LOCKED` — no extra broker for v1.
- **Auditability first.** Each ranking decision is reproducible from `ranking_runs` + `ranking_tournaments` + `ranking_results.decision_trace`.

---

## 2. Entity map

```
service_areas ──< service_zones
service_areas ──< vacancies
service_areas ──< candidates
service_zones ──< candidates

candidates    ──< conversations ──< messages
                    │
                    ├──< sentiment_results (1:1)
                    ├──< nudges
                    └──< security_events

vacancies     ──< ranking_runs ──< ranking_tournaments
                                  └──< ranking_results >── candidates

jobs          (queue table consumed by sentiment + ranking + nudge workers)
audit_log     (cross-entity append-only trail)
```

---

## 3. Tables

### Catalogs

| Table | Purpose | Key columns |
|---|---|---|
| `service_areas` | 45 cities (ES + MX) | `code` (unique), `city`, `country`, `active` |
| `service_zones` | sub-zones inside a city | `area_id`, `name` (unique per area) |
| `platforms` | Glovo, Uber Eats, Rappi, DiDi, Stuart, … | `code`, `name`, `active` |

### `vacancies`

Operational job to fill. Drives the ranking.

- `area_id`, `urgency` (`low/medium/high`), `critical_shifts` (`text[]`, e.g. `{night, weekend}`), `ideal_start_days` (int), `headcount`, `status`.
- The fields **`urgency`, `critical_shifts`, `ideal_start_days`** are the *operational context* injected verbatim into the listwise prompt — this is exactly what a fixed-weights formula cannot model.

### `candidates`

One row per person screened.

- Contact: `full_name`, optional `phone`, `email` (both unique).
- Locale + privacy: `language`, `consent`, `consent_at`.
- Screening data captured by the agent: `drivers_license: bool`, `area_id`, `zone_id`, `availability` (enum), `preferred_schedule` (enum), `experience_years` (0–50, CHECK), `platforms text[]`, `start_date`.
- State: `status` (`new / in_progress / qualified / qualified_flagged / soft_disq / hard_disq / waitlist / abandoned`), `slot_uncertain` flag (set by the agent when validation retried twice).

> **License rationale:** the chat agent only asks *“do you have a driver’s license?”*. Storing the answer as a boolean makes the field cheap, regex-validatable, and free of biometric-document handling. ID document upload is an explicit non-feature for v1.

### `conversations` and `messages`

- `conversations.session_id` is the same key Redis uses for hot-path state. Postgres has the durable copy.
- `captured_data JSONB` mirrors slots so dashboards can query them without joining `candidates`.
- `messages` is append-only; one row per turn (user / assistant / system / tool). `tool_calls JSONB` records ReAct tool invocations for replay. `security_flagged bool` marks turns the reflection agent intervened on.

Indexes: `(conversation_id, created_at)` for chronological reads; `status` and `(candidate_id)` on conversations for dashboards.

### `jobs` (worker queue)

Single generic queue:

- `job_type` (`sentiment` | `ranking` | `nudge`), `status`, `payload JSONB`.
- `attempts` / `max_attempts` for retry policy, `last_error TEXT`.
- `run_after TIMESTAMPTZ` for deferred execution (used by nudges).
- `locked_at` / `locked_by` for visibility into in-flight work.

**Hot path** — workers pull with:

```sql
SELECT id, payload
FROM jobs
WHERE status = 'pending'
  AND job_type = $1
  AND run_after <= now()
ORDER BY run_after
FOR UPDATE SKIP LOCKED
LIMIT 10;
```

Backed by the partial index `ix_jobs_pending_runafter (job_type, run_after) WHERE status = 'pending'`.

### `sentiment_results`

1:1 with `conversations`. `sentiment` enum (`positive / neutral / confused / frustrated`), `confidence`, `signals JSONB` (per-turn breakdown), `model_version`.

Used by the ranking worker as a soft penalty (frustrated → lowered utility / dashboard flag).

### Ranking pipeline (Listwise + Plackett–Luce)

Three tables — one per layer of the worker described in `Phase1_Conversation_Design.md` §5:

| Table | Grain | Notes |
|---|---|---|
| `ranking_runs` | one per `(vacancy_id, attempt)` | `rubric_version`, `pool_size`, `top_n`, run lifecycle |
| `ranking_tournaments` | one per LLM listwise call | `candidate_ids` and `llm_ranking` are UUID arrays of length K; `confidence`, `model`, `is_active_learning` |
| `ranking_results` | one per `(run_id, candidate_id)` | `utility` (PL latent), `posterior_variance`, `rank_position`, `tournaments_seen`, `decision_trace JSONB` |

Auditability: any past ranking can be replayed from `ranking_tournaments`. The recruiter dashboard joins `ranking_results` ↔ `candidates` ↔ `conversations` to render the daily top-K.

### `security_events`

Every block by the reflection agent.

- `attack_type` (`direct_override`, `prompt_leakage`, `role_hijack`, `base64_obf`, `cross_lingual`, `indirect_injection`, `multi_turn_trust`, `chat_template_abuse`, `reward_framing`),
- `severity` enum, `pattern`, `raw_input`, `blocked bool`, `extra JSONB`.

Linked to the offending `conversation_id` and `message_id` for forensics.

### `nudges`

Schedule of re-engagement messages: `(+5min light, +4h context, +24h value, +72h close)`. The nudge worker picks rows where `delivered = false AND scheduled_at <= now()`.

### `audit_log`

Append-only cross-entity trail (`entity_type`, `entity_id`, `action`, `actor`, `payload JSONB`). Used for GDPR access requests and EU AI Act explainability.

---

## 4. Conventions

- **Primary keys.** UUID v4, server-generated.
- **Timestamps.** Always `TIMESTAMPTZ`. `created_at` defaults to `now()`. `updated_at` uses both `server_default` and `onupdate=func.now()` in SQLAlchemy.
- **Soft deletes.** Not used. Closed/abandoned/disqualified states are explicit on `status`.
- **JSONB columns** never replace first-class columns when the field is queried in a `WHERE` clause. They store: extracted slots snapshot, decision traces, sentiment signals, rubric metadata, security extras, audit payloads.
- **Foreign keys.** `ON DELETE CASCADE` for child rows (`messages`, `ranking_tournaments`, `ranking_results`, `nudges`); `ON DELETE SET NULL` for cross-entity refs we want to keep around (`candidate_id` / `vacancy_id` on conversations, `message_id` on security events).
- **Enums.** Created once in migration `0001`, reused across columns (`language_enum`, `job_status_enum`).

---

## 5. Migrations

```bash
# from backend/
alembic upgrade head
```

- `alembic/env.py` reads `settings.DATABASE_URL` (so secrets stay out of `alembic.ini`).
- Initial revision: `0001_initial_schema.py` — installs `pgcrypto`, all enums, all tables and indexes (including the partial index for the worker hot path).
- Downgrade is symmetric and tested manually before each release.

---

## 6. Containerization

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

2. **Manual cleanup:** connect as user `app`, drop leftover objects in schema `public`, then `alembic upgrade head`, or `alembic stamp 0001` only if the schema already matches `0001` exactly (advanced).

---

## 7. What is *not* in PostgreSQL

- **Conversation hot state** (active session, recent slots, last LLM tool call) → Redis.
- **Recent message history** for in-flight chats → Redis (mirrored into `messages` on flush).
- **Rate limiting / nudge cooldowns** → Redis.
- **RAG embeddings / company knowledge** → Chroma.
- **Captured candidate slots before flush** → Redis, then committed here.

This split keeps Postgres focused on durable, queryable, auditable data.
