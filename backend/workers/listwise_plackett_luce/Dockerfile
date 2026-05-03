# Image for the listwise + Plackett-Luce ranking worker.
#
# Build context (set in docker-compose.yml) MUST be `./backend` so that the
# `app/` package and shared code are available to COPY.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install Python deps first (better layer caching). The worker reuses the main
# requirements.txt so SQLAlchemy models and core helpers stay in lockstep with
# the API. Heavy ranking-specific deps (numpy, scipy, jaxopt, etc.) will be
# added here when the actual algorithm is wired in.
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY app /app/app
COPY prompts /app/prompts
COPY docs /app/docs

CMD ["python", "-m", "app.workers.listwise_plackett_luce.worker"]
