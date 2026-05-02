# Image for the FastAPI backend.
#
# Each worker has its own dedicated Dockerfile under workers/<name>/Dockerfile
# but they all share this same source tree (app/), so SQLAlchemy models,
# config and logging stay in lockstep across services. Each container only
# runs the modules its entrypoint actually imports.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY app /app/app
COPY prompts /app/prompts
COPY docs /app/docs
COPY scripts /app/scripts
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY run.py /app/run.py

EXPOSE 8000

CMD ["python", "run.py"]
