# Listwise worker: NOTIFY, `jobs` queue, and mutual exclusion

This document explains how listwise ranking jobs are enqueued from the API, how the
worker wakes without continuous polling, and how duplicate execution of the same job
is prevented.

## 1. Enqueueing from the API

- **Endpoint:** `POST /api/v1/jobs/listwise`
- **Optional body:** `{ "vacancy_id": "<uuid>" }` — when present, the cohort is
  candidates in `sentiment_analysis` with at least one `conversations` row tied
  to that vacancy; when omitted, everyone currently in `sentiment_analysis` (with
  an associated conversation) is considered.
- **Effect:** `INSERT` into `jobs` with `job_type = listwise` and `status = pending`.

Migration `0004_listwise_job_type_and_notify.py` adds the `listwise` value to
`job_type_enum` and an `AFTER INSERT` trigger that emits:

```text
NOTIFY listwise_job_pending, '<job_uuid>';
```

only when the new row’s type is `listwise`.

## 2. Why there is no constant polling

The process `python -m app.workers.listwise_plackett_luce.worker` opens a dedicated
autocommit connection (psycopg) and runs `LISTEN listwise_job_pending`.
It blocks on `conn.notifies()` until PostgreSQL delivers a notification; the asyncio
loop then wakes and processes **only** the received `job_id`.

This mirrors the sentiment-analysis worker pattern on channel `candidate_completed`.

### Startup and backlog

To avoid losing rows inserted while the worker was down, on startup it performs **one**
sweep: `SELECT id FROM jobs WHERE job_type = listwise AND status = pending`
ordered by `created_at`. Each id is processed with the same routine as for NOTIFY.
There is no periodic polling loop; this happens once at process start.

## 3. Single execution per `job_id` (anti double-run)

Several workers may listen on the same channel. They all receive the same `NOTIFY`,
but only one should run the pipeline.

**Mechanism:** conditional `UPDATE` in a single SQL statement:

```sql
UPDATE jobs
SET status = 'running',
    locked_at = NOW(),
    locked_by = :worker_id,
    attempts = attempts + 1
WHERE id = :job_id
  AND job_type = 'listwise'
  AND status = 'pending';
```

In SQLAlchemy:

```python
update(Job).where(...).values(...)
```

- If **one** row changes (`rowcount == 1`), this process claimed the job and runs
  listwise ranking.
- If **zero** rows, another worker already moved the job to `running`, or the job
  did not exist / was not pending: this process exits without work.

That prevents double execution even with duplicate NOTIFY or races at startup.

## 4. Pipeline phase 1 (data → orchestrator → sub-agents)

1. **Cohort:** candidates with `status = sentiment_analysis`, optionally filtered by
   `vacancy_id` via `conversations.vacancy_id`.
2. **JD context:** plain text from `docs/GRUPO_SAZON_PUBLIC_INFO_ES.txt` (truncated).
   The **orchestrator** only receives JD + UUID list (no cards or transcripts in its context).
3. **Orchestrator (LLM with tools):** iterates by calling `run_group_ranking(candidate_ids, instructions)`.
   Each call may use **different `instructions`** (per-tournament ranking prompt).
4. **Per tool call:** the backend re-reads Postgres (ORM) with `load_ranking_cards_for_ids`:
   candidate, latest `conversation` transcript, sentiment (`sentiment_results` / `signals`),
   `post_conversation_summary`, `key_data_points`, phone, email, availability, etc.
   That dossier + JD + `instructions` goes to the **sub-agent** (another LLM call,
   JSON `ordered_candidate_ids` + `rationale`). Multiple tools in one turn run in parallel
   via `asyncio.gather`.
5. **≥ 3 tournaments per candidate:** the orchestrator prompt requires at least three
   appearances per participant. After execution, the worker computes Python `coverage` for auditing.
6. **Status transition:** if the pipeline succeeds, cohort candidates move from
   `sentiment_analysis` to `listwise`. The aggregated result is stored in `jobs.payload.result`.

## 5. Operational summary

| Piece | Role |
|--------|-----|
| Trigger `listwise_job_pending_notify` | Wakes workers in real time. |
| `LISTEN listwise_job_pending` | No hot-path polling. |
| `UPDATE … WHERE status = pending` | Single winner per job. |
| Orchestrator + tool → sub-agent | Same idea as `llm_client.run_agent`, but the tool is a second LLM call. |
