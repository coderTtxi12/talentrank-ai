from fastapi import FastAPI

from app.api.v1 import api_router_v1
from app.core.config import settings
from app.core.logging import configure_logging, get_logger


def create_app() -> FastAPI:
    configure_logging()
    logger = get_logger(__name__)

    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.include_router(api_router_v1, prefix=settings.API_V1_PREFIX)

    logger.info(
        "App initialized: %s v%s (env=%s)",
        settings.PROJECT_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
    )
    return app


app = create_app()
