"""Sentiment pipeline worker package.

Runtime entrypoint: :mod:`app.workers.sentiment_analysis.worker` (LISTEN on
``candidate_completed``, phase-1 hard filters, phase-2 LLM sentiment).

LLM helper only: :mod:`app.workers.sentiment_analysis.agent`.
"""
