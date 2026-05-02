"""Contenedores de workers por dominio.

* ``app.workers.sentiment_analysis`` — NOTIFY + sentimiento / fase 1.
* ``app.workers.listwise_plackett_luce`` — ranking listwise.

Las imágenes Docker en ``backend/workers/<nombre>/Dockerfile`` invocan el módulo
``worker`` dentro de cada subpaquete.
"""
