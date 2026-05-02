"""Emitir eventos Socket.IO al dashboard (namespace por defecto ``/``)."""

from __future__ import annotations

from typing import Any, Mapping

from app.realtime.socket_server import get_socketio


async def emit_candidate_status_changed(
    candidate_id: str,
    *,
    old_status: str,
    new_status: str,
) -> None:
    sio = get_socketio()
    if not sio:
        return
    await sio.emit(
        "status_changed",
        {
            "candidate_id": candidate_id,
            "loan_id": candidate_id,
            "old_status": old_status,
            "new_status": new_status,
        },
    )


async def emit_candidate_created(candidate: Mapping[str, Any]) -> None:
    sio = get_socketio()
    if not sio:
        return
    cid = str(candidate["id"])
    await sio.emit("candidate_created", {"candidate_id": cid, "data": dict(candidate)})


async def emit_candidate_updated(
    candidate_id: str,
    changes: Mapping[str, Any],
) -> None:
    sio = get_socketio()
    if not sio:
        return
    await sio.emit(
        "candidate_updated",
        {"candidate_id": candidate_id, "changes": dict(changes)},
    )
