"""Contenedores de workers por dominio.

* ``app.workers.sentiment_analysis`` — NOTIFY `candidate_completed` + sentimiento.
* ``app.workers.listwise_plackett_luce`` — NOTIFY `listwise_job_pending` + listwise (orquestador + subagentes).

Las imágenes Docker en ``backend/workers/<nombre>/Dockerfile`` invocan el módulo
``worker`` dentro de cada subpaquete.
"""
