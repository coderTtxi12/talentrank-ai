# Listwise worker: NOTIFY, cola `jobs` y exclusión mutua

Este documento describe cómo encola el ranking listwise desde la API, cómo el
worker despierta sin polling continuo, y cómo se evita que dos procesos
ejecuten el mismo trabajo.

## 1. Encolado desde la API

- **Endpoint:** `POST /api/v1/jobs/listwise`
- **Cuerpo opcional:** `{ "vacancy_id": "<uuid>" }` — si está presente, la cohorte
  son candidatos en `sentiment_analysis` con al menos una `conversations` ligada
  a esa vacante; si se omite, se consideran todos los que estén en
  `sentiment_analysis` (conversación asociada).
- **Efecto:** `INSERT` en `jobs` con `job_type = listwise` y `status = pending`.

La migración `0004_listwise_job_type_and_notify.py` añade el valor de enum
`listwise` a `job_type_enum` y un trigger `AFTER INSERT` que emite:

```text
NOTIFY listwise_job_pending, '<job_uuid>';
```

solo cuando el tipo del nuevo registro es `listwise`.

## 2. Por qué no hay polling constante

El proceso `python -m app.workers.listwise_plackett_luce.worker` abre una
conexión dedicada en autocommit (psycopg) y ejecuta `LISTEN listwise_job_pending`.
Queda bloqueado en `conn.notifies()` hasta que Postgres entrega un aviso: en
ese momento el bucle asyncio despierta y procesa **solo** el `job_id` recibido.

Esto es el mismo patrón que el worker de análisis de sentimiento con el canal
`candidate_completed`.

### Arranque y trabajos atrás

Para no perder filas insertadas mientras el worker estaba caído, al arrancar se
hace **un** barrido: `SELECT id FROM jobs WHERE job_type = listwise AND status = pending`
ordenado por `created_at`. Cada id se procesa con la misma rutina que un NOTIFY.
No es un bucle de polling periódico; solo ocurre al inicio del proceso.

## 3. Una sola ejecución por `job_id` (anti doble proceso)

Varios workers pueden estar escuchando el mismo canal. Todos reciben el mismo
`NOTIFY`, pero solo uno debe ejecutar el pipeline.

**Mecanismo:** `UPDATE` condicional en una sola sentencia SQL:

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

En SQLAlchemy:

```python
update(Job).where(...).values(...)
```

- Si **una** fila cambia (`rowcount == 1`), este proceso ha reclamado el trabajo
  y ejecuta el ranking listwise.
- Si **cero** filas, otro worker ya pasó el trabajo a `running`, o el job no
  existía / no estaba pendiente: este proceso sale sin hacer nada.

Así se evita doble ejecución incluso con NOTIFY duplicado o competencia en el
arranque.

## 4. Fase 1 del pipeline (datos → orquestador → subagentes)

1. **Cohorte:** candidatos con `status = sentiment_analysis`, filtrados por
   `vacancy_id` opcional vía `conversations.vacancy_id`.
2. **Contexto JD:** texto plano de `docs/GRUPO_SAZON_PUBLIC_INFO_ES.txt`
   (truncado). El **orquestador** solo recibe JD + lista de UUID (no fichas ni
   transcripciones en su contexto).
3. **Orquestador (LLM con tools):** itera llamando `run_group_ranking(candidate_ids, instructions)`.
   Cada llamada puede llevar **`instructions` distintas** (prompt de ranking por torneo).
4. **Por cada tool:** el backend vuelve a leer Postgres (ORM) con
   `load_ranking_cards_for_ids`: candidato, transcripción del último `conversation`,
   resultados de sentimiento (`sentiment_results` / `signals`), `post_conversation_summary`,
   `key_data_points`, teléfono, email, disponibilidad, etc. Ese dossier + JD + `instructions` van al **subagente**
   (otra llamada LLM, JSON `ordered_candidate_ids` + `rationale`). Varios tools
   en un turno se ejecutan en paralelo con `asyncio.gather`.
5. **Restricción ≥ 3 torneos por candidato:** el prompt del orquestador exige
   diseñar al menos tres apariciones por participante. Tras ejecutar, el worker
   calcula en Python `coverage` para auditoría.
6. **Transición de estado:** si el pipeline termina bien, los candidatos de la
   cohorte pasan de `sentiment_analysis` a `listwise`. El resultado agregado se
   guarda en `jobs.payload.result`.

## 5. Resumen operativo

| Pieza | Rol |
|--------|-----|
| Trigger `listwise_job_pending_notify` | Despierta workers en tiempo real. |
| `LISTEN listwise_job_pending` | Sin polling en caliente. |
| `UPDATE … WHERE status = pending` | Un solo ganador por job. |
| Orquestador + tool → subagente | Misma idea que `llm_client.run_agent`, pero la herramienta es una segunda llamada LLM. |
