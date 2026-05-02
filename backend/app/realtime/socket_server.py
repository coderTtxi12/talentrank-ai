"""Socket.IO (ASGI) — feed de candidatos en el namespace por defecto ``/``.

Todo el tráfico va a ``/socket.io`` y al namespace ``/`` (default). Evita rutas tipo
``http://host/candidates`` en el cliente, que suelen disparar errores Engine.IO / 400
en algunos navegadores y proxies.

Eventos cliente → servidor: ``subscribe_candidates``, ``subscribe_recent``.
Eventos servidor → cliente: ``candidates_snapshot``, ``recent_candidates_snapshot``,
``candidate_created``, ``candidate_updated``, ``status_changed``.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

import socketio

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.schemas.candidate_public import CandidatesRecentPayload, CandidatesSubscribePayload
from app.services.candidate_list import list_candidates_cursor_page

logger = get_logger(__name__)

_sio: Optional[socketio.AsyncServer] = None


def get_socketio() -> Optional[socketio.AsyncServer]:
    return _sio


def _build_raw_server() -> socketio.AsyncServer:
    cors = settings.socketio_cors_allowed_origins()
    return socketio.AsyncServer(
        async_mode="asgi",
        cors_allowed_origins=cors,
    )


def register_socket_handlers(sio: socketio.AsyncServer) -> None:
    """Registra eventos en el namespace ``/`` (default)."""

    @sio.event
    async def connect(_sid: str, _environ: dict[str, Any]) -> bool:
        logger.info("socket.io connect sid=%s (namespace=/ )", _sid[:12])
        return True

    @sio.event
    async def disconnect(_sid: str) -> None:
        logger.info("socket.io disconnect sid=%s", _sid[:12])

    @sio.on("subscribe_candidates")  # type: ignore[misc]
    async def subscribe_candidates(sid: str, data: Any) -> None:
        try:
            payload = CandidatesSubscribePayload.model_validate(data or {})
        except Exception as exc:  # noqa: BLE001
            logger.warning("subscribe_candidates invalid sid=%s: %s", sid[:12], exc)
            await sio.emit("subscription_error", {"message": str(exc)}, to=sid)
            return

        def work():
            with SessionLocal() as db:
                return list_candidates_cursor_page(
                    db,
                    limit=payload.limit,
                    cursor=payload.cursor,
                    status_filter=payload.status_filter,
                    country_filter=payload.country_code,
                    include_total=payload.include_total,
                )

        page = await asyncio.to_thread(work)
        await sio.emit("candidates_snapshot", page.model_dump(mode="json"), to=sid)

    @sio.on("subscribe_recent")  # type: ignore[misc]
    async def subscribe_recent(sid: str, data: Any) -> None:
        try:
            payload = CandidatesRecentPayload.model_validate(data or {})
        except Exception as exc:  # noqa: BLE001
            logger.warning("subscribe_recent invalid sid=%s: %s", sid[:12], exc)
            await sio.emit("subscription_error", {"message": str(exc)}, to=sid)
            return

        def work():
            with SessionLocal() as db:
                return list_candidates_cursor_page(
                    db,
                    limit=payload.limit,
                    cursor=payload.cursor,
                    status_filter=None,
                    country_filter=None,
                    include_total=False,
                )

        page = await asyncio.to_thread(work)
        await sio.emit(
            "recent_candidates_snapshot",
            {
                "items": [c.model_dump(mode="json") for c in page.items],
                "next_cursor": page.next_cursor,
                "limit": page.limit,
                "cursor": payload.cursor,
            },
            to=sid,
        )


def build_combined_asgi(fastapi_app: Any) -> Any:
    """ASGI combinado: Engine.IO en ``/socket.io`` + FastAPI en el resto."""

    global _sio
    sio = _build_raw_server()
    register_socket_handlers(sio)
    _sio = sio
    cors = settings.socketio_cors_allowed_origins()
    logger.info(
        "Socket.IO montado en /socket.io namespace=/ (default) cors=%s ENV=%s",
        cors,
        settings.ENVIRONMENT,
    )
    return socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path="socket.io")
