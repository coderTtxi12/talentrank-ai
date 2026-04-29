# Redis Design

Hot-path, low-latency state for active screening sessions. PostgreSQL holds
the durable record (see [`POSTGRESQL_DESIGN.md`](./POSTGRESQL_DESIGN.md));
Redis exists so the chat agent never has to round-trip through Postgres on
every turn.

> **Version:** Redis 7 (Alpine).
> **Persistence:** RDB snapshots (`save 60 1000`) + AOF (`appendonly yes`).
> **Eviction:** `maxmemory 256mb`, `maxmemory-policy allkeys-lru`.

---

## 1. What lives in Redis

| Concern | In Redis | In Postgres |
|---|---|---|
| Active session state (slots so far, current stage) | ✅ | snapshot on flush |
| Rolling conversation history for the LLM | ✅ (capped) | full append-only `messages` |
| Re-engagement timers / nudge state | ✅ | `nudges` schedule |
| Rate limiting / abuse throttling | ✅ | — |
| Idempotency keys for write endpoints | ✅ | — |
| Cached security verdicts (prompt-injection signatures) | ✅ | — |
| Distributed lock for ranking workers | ✅ | — |

Anything that is *queryable* or must survive Redis restart in pristine form
goes to Postgres.

---

## 2. Key naming conventions

```
<namespace>:<entity>:<id>[:<sub>]
```

- Namespaces are stable and short (`sess`, `hist`, `cand`, `nudge`, `rl`, `idem`, `sec`, `lock`).
- IDs are UUID strings or hashed external identifiers.
- Always specify a TTL (no key without an expiry policy).
- Database index `0` for app data; reserved `1` for ephemeral queues / pub-sub if needed.

---

## 3. Session state — `sess:<session_id>`

The single source of truth for **what the agent has captured during the
in-progress conversation** before it is flushed to Postgres.

- **Type:** Hash.
- **TTL:** `SESSION_TTL_SECONDS` (default **86 400 s = 24 h**).
- **Refreshed on every turn** with `EXPIRE sess:<id> 86400` so an active
  candidate keeps the key alive; an abandoned one expires automatically.

Fields:

| Field | Type | Notes |
|---|---|---|
| `candidate_id` | uuid | populated once the candidate row is created |
| `vacancy_id` | uuid | optional, set after city/area resolution |
| `stage` | str | `S0..S6` checkpoint marker |
| `language` | str | `es-ES` / `es-MX` / `en` (per-turn detector keeps it fresh) |
| `consent` | bool | required before storing PII |
| `slots` | json | extracted slots so far (mirrors `conversations.captured_data`) |
| `slot_uncertain` | bool | flips after 2 retries on the same slot |
| `last_seen_at` | iso8601 | also written to `conversations.last_seen_at` on flush |
| `nudge_count` | int | layered re-engagement counter (max 4) |

`session_id` is the **same value** stored in `conversations.session_id`, so
hot-path Redis and durable Postgres share the lookup key.

---

## 4. Conversation history — `hist:<session_id>`

Recent messages used to feed the ReAct LLM context window. **Capped, not
unbounded** — full history lives in Postgres `messages`.

- **Type:** List (newest pushed with `RPUSH`, oldest trimmed with `LTRIM`).
- **TTL:** `HISTORY_TTL_SECONDS` (default **604 800 s = 7 days**).
- **Cap:** last `HISTORY_MAX_TURNS` turns (default 40).
- **Each entry** is a JSON blob: `{role, content, language, ts, msg_id}`.
  `msg_id` is the Postgres `messages.id` once the row is committed (so we can
  re-hydrate by ID without re-storing the whole text).

```
RPUSH  hist:<sid>  '{"role":"user","content":"sí, tengo licencia",...}'
LTRIM  hist:<sid>  -40 -1
EXPIRE hist:<sid>  604800
```

Read path:

```
LRANGE hist:<sid> 0 -1
```

If the key is missing (cold session, expired), fall back to Postgres:

```sql
SELECT role, content, language, created_at
FROM messages
WHERE conversation_id = $1
ORDER BY created_at DESC
LIMIT 40;
```

…and rebuild the Redis list.

---

## 5. Re-engagement — `nudge:<session_id>`

Mirrors the layered cadence (`+5min`, `+4h`, `+24h`, `+72h`).

- **Type:** Hash with fields `next_at`, `next_type`, `count`.
- **TTL:** matches the longest cadence (`72h + buffer`, default 90 h).
- The nudge worker reads from Postgres (`nudges` table is the source of
  truth); Redis is a hot cache for the chat handler to know whether to
  short-circuit a candidate-initiated reopen.

---

## 6. Rate limiting — `rl:<scope>:<key>`

Sliding-window token bucket per scope:

| Scope | Key | Limit | TTL |
|---|---|---|---|
| `chat:ip` | client IP | 60 req / min | 60 s |
| `chat:session` | `session_id` | 30 turns / min | 60 s |
| `auth:ip` | client IP | 10 req / min | 60 s |

Implemented with `INCR` + `EXPIRE` (atomic via Lua script for first hit). Over-limit returns `429`.

---

## 7. Idempotency — `idem:<endpoint>:<key>`

Used **only** by endpoints that mutate external state (per `ENDPOINT_RULES.md`).

- **Type:** String (response body cached).
- **TTL:** 24 h.
- Keyed by the client-provided `Idempotency-Key` header.

---

## 8. Security cache — `sec:sig:<sha1(input)>`

Caches reflection-agent verdicts for repeated abusive inputs (e.g. the same
base64 payload retried by a probing client).

- **Type:** String (`block` | `allow` + metadata).
- **TTL:** 1 h.
- Saves an LLM call on the reflection step for known patterns; misses fall
  back to the full classifier and write the resulting verdict to both Redis
  and `security_events` in Postgres.

---

## 9. Worker locks — `lock:ranking:<vacancy_id>`

Prevents two ranking workers from running concurrently on the same vacancy.

- **Type:** String, set with `SET ... NX EX <ttl>`.
- **TTL:** `RANKING_LOCK_TTL` (default 600 s — re-extended every 60 s by the worker’s heartbeat).

---

## 10. TTL summary

| Key pattern | TTL | Refreshed on |
|---|---|---|
| `sess:<sid>` | 24 h | every turn |
| `hist:<sid>` | 7 days | every push |
| `nudge:<sid>` | 90 h | nudge schedule update |
| `rl:*` | 60 s | each request |
| `idem:*` | 24 h | first write |
| `sec:sig:*` | 1 h | first verdict |
| `lock:ranking:*` | 600 s | worker heartbeat |

All TTLs are configurable via `Settings` (`SESSION_TTL_SECONDS`, `HISTORY_TTL_SECONDS`, …).

---

## 11. Containerization

`docker-compose.yml` ships a `redis:7-alpine` service with:

- Persistent volume `redis_data:/data`.
- AOF + RDB snapshots for crash recovery.
- `maxmemory 256mb` + `allkeys-lru` to prevent memory blow-ups while keeping the most recent hot data.
- Health check via `redis-cli ping`.

```bash
docker compose up -d redis
redis-cli -h localhost -p 6380 ping   # → PONG  (host port 6380 → container 6379)
```

---

## 12. Failure modes

- **Redis down:** chat handler proceeds in *degraded mode* — re-hydrates state from Postgres on every turn (slower, still correct). Health check on `/api/v1/health` reports `degraded`.
- **Cold session (key expired):** rehydrate `sess:<sid>` and `hist:<sid>` from Postgres. The candidate sees no difference; latency rises by one DB read.
- **Redis OOM eviction (LRU):** active sessions stay (their keys are touched constantly); abandoned sessions get evicted first — exactly the desired behavior.
- **Inconsistency Redis ↔ Postgres:** Postgres is canonical. On reconciliation jobs (or on cold reads) Postgres wins and the Redis copy is rebuilt.
