from fastapi import APIRouter

from app.api.routes import health

api_router_v1 = APIRouter()
api_router_v1.include_router(health.router)
