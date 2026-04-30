# Image for the sentiment-analysis worker.
#
# Build context (set in docker-compose.yml) MUST be `./backend` so that the
# `app/` package, `prompts/` and shared code are available to COPY.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install Python deps first (better layer caching). We reuse the main
# requirements.txt so the worker stays in lockstep with the API. If the worker
# image grows too large later we can split this into a slimmer worker-only
# requirements file.
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY app /app/app
COPY prompts /app/prompts

CMD ["python", "-m", "app.workers.sentiment_analysis_worker"]
