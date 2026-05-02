from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router_v1
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.realtime.socket_server import build_combined_asgi


def create_fastapi_application() -> FastAPI:
    configure_logging()
    logger = get_logger(__name__)

    fastapi_app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    fastapi_app.include_router(api_router_v1, prefix=settings.API_V1_PREFIX)

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info(
        "FastAPI initialized: %s v%s (env=%s)",
        settings.PROJECT_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
    )
    return fastapi_app


app = build_combined_asgi(create_fastapi_application())
