"""Worker subpackages grouped by domain.

* ``app.workers.sentiment_analysis`` — ``LISTEN`` on ``candidate_completed`` + sentiment pipeline.
* ``app.workers.listwise_plackett_luce`` — ``LISTEN`` on ``listwise_job_pending`` + listwise
  (orchestrator + sub-agents).

Docker images under ``backend/workers/<name>/Dockerfile`` run the ``worker`` module
inside each subpackage.
"""
