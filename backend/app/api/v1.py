from fastapi import APIRouter

from app.api.routes import chat, health

api_router_v1 = APIRouter()
api_router_v1.include_router(health.router)
api_router_v1.include_router(chat.router)
