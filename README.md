# Orbio

Monorepo con todos los servicios del proyecto orquestados con Docker Compose.

```text
orbio/
├── docker-compose.yml      # Orquestación de todos los servicios
├── .env.example            # Variables de orquestación (puertos, DB, etc.)
├── backend/                # API FastAPI + workers
│   ├── Dockerfile
│   ├── .env.example        # Secretos de aplicación (OpenAI, LangSmith, ...)
│   └── ...
└── frontend-chat/          # Cliente web Next.js
    ├── Dockerfile
    └── ...
```

## Requisitos

- Docker Desktop (o Docker Engine + Compose v2)
- Para desarrollo fuera de Docker: Python 3.12 y Node 20

## Levantar todo con Docker

```bash
# 1) Variables de orquestación (puertos, credenciales DB) en la raíz
cp .env.example .env

# 2) Secretos de aplicación del backend (OPENAI_API_KEY, etc.)
cp backend/.env.example backend/.env
# Edita backend/.env y pon tu OPENAI_API_KEY real

# 3) Build y arranque
docker compose up --build
```

Servicios publicados por defecto:

| Servicio          | URL                              |
| ----------------- | -------------------------------- |
| Frontend (Next)   | http://localhost:3000            |
| API (FastAPI)     | http://localhost:8000            |
| Health check API  | http://localhost:8000/api/v1/health |
| Postgres          | localhost:5433                   |
| Redis             | localhost:6380                   |

Para parar todo: `docker compose down`.
Para borrar también los volúmenes (DB, Chroma, Redis): `docker compose down -v`.

## Servicios

- **postgres** — base de datos relacional.
- **redis** — caché / sesiones.
- **api** — backend FastAPI (`backend/`).
- **sentiment-analysis-worker** — worker (`backend/workers/sentiment_analysis`).
- **listwise-plackett-luce-worker** — worker (`backend/workers/listwise_plackett_luce`).
- **frontend** — cliente web Next.js (`frontend-chat/`).

## Desarrollo fuera de Docker

Si prefieres correr los procesos en local y dejar Docker sólo para Postgres/Redis:

```bash
# Sólo infra
docker compose up postgres redis

# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py

# Frontend (en otra terminal)
cd frontend-chat
cp .env.example .env.local   # asegúrate de NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

## Notas

- `NEXT_PUBLIC_API_URL` se inlinea en el bundle de Next durante `next build`, por
  eso `docker-compose.yml` la pasa como **build arg** al servicio `frontend`.
  Si cambias la URL pública, hay que reconstruir la imagen del frontend
  (`docker compose build frontend`).
- El `backend/.env` queda fuera del control de versiones (ver `.gitignore`).
  El `.env` de la raíz también: contiene credenciales locales de Postgres.
