# Endpoint Rules

Mandatory rules for adding new endpoints.

## Versioning

- Every endpoint lives under a version prefix: `/api/v{N}`.
- Current version: `/api/v1`.
- Do not change existing contracts: breaking changes → new version (`v2`, …).
- Register the router in `app/api/v{N}.py`.

## Pydantic

- Requests and responses **always** use Pydantic models. No raw `dict`s.
- API schemas live under `app/models/`. ORM (SQLAlchemy) stays separate in `app/models/database.py`.
- Validate types, ranges, and formats in the schema, not in the handler.
- Use `response_model=` on every route.

## Idempotency

- Only where it applies. Do not add it to every endpoint.
- Apply to: operations that create/mutate external state and may be retried (POST/PUT/PATCH that trigger side effects: payments, shipments, jobs, critical writes).
- Mechanism: `Idempotency-Key` header (client UUID). Persist `key → response` (Redis/DB) for a reasonable window (e.g. 24h) and return the original response on retries.
- GET and naturally idempotent operations (pure PUT, DELETE) do not need the header.

## Pagination

- Only where it applies. Do not add it to endpoints that return a single resource or small, bounded lists by nature.
- Apply to: listings that can grow (>~100 items) or queries over tables with unknown N.
- Default style: cursor-based (`cursor`, `limit`). Use offset/limit only if the query cannot support cursors.
- Paginated response schema: `items`, `next_cursor` (or `next_offset`), `limit`, `total` (only if cheap to compute).
- `limit` with default and maximum (e.g. default 20, max 100), validated in Pydantic.

## Other rules

- Semantic HTTP: 200/201/204/400/401/403/404/409/422/500. Do not invent codes.
- Errors use a shared Pydantic schema (`code`, `message`, `details`).
- Non-trivial logic belongs in `app/services/`, not in the handler.
- Structured logging via `app.core.logging.get_logger(__name__)`.
- Async by default (`async def`) unless work is purely CPU-bound.
- Document every route: `summary`, `description`, `tags`, `responses` where relevant.
