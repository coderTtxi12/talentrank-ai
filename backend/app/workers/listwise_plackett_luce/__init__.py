"""Listwise ranking worker package.

- :mod:`app.workers.listwise_plackett_luce.worker` — job queue + NOTIFY + pipeline glue
- :mod:`app.workers.listwise_plackett_luce.cohort` — cohort selection + ranking cards
- :mod:`app.workers.listwise_plackett_luce.orchestrator` — multi-step LLM orchestrator + tools
- :mod:`app.workers.listwise_plackett_luce.subagent` — per-tournament listwise call
- :mod:`app.workers.listwise_plackett_luce.persistence` — DB rows + PL apply
- :mod:`app.workers.listwise_plackett_luce.plackett_luce_fit` — Plackett–Luce MLE
- :mod:`app.workers.listwise_plackett_luce.openai_listwise` — long-timeout OpenAI client
"""
