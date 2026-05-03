from fastapi import APIRouter

from app.api.routes import candidates, chat, health, jobs

api_router_v1 = APIRouter()
api_router_v1.include_router(health.router)
api_router_v1.include_router(chat.router)
api_router_v1.include_router(candidates.router)
api_router_v1.include_router(jobs.router)
