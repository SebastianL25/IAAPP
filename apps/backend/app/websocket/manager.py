"""Gestor de conexiones WebSocket para difundir progreso de trabajos.

Se usa desde dos lugares:
- Los routers WS (`app/api/*` -> `/api/ws/jobs`, `/api/ws/projects/{id}`)
  registran/quitan conexiones.
- El pipeline (que corre en threads via `asyncio.to_thread`) llama a
  `broadcast_threadsafe` con el event loop capturado al iniciar el server.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.global_connections: set[WebSocket] = set()
        self.project_connections: dict[str, set[WebSocket]] = {}
        self.loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    async def connect_global(self, ws: WebSocket) -> None:
        await ws.accept()
        self.global_connections.add(ws)

    async def connect_project(self, ws: WebSocket, project_id: str) -> None:
        await ws.accept()
        self.project_connections.setdefault(project_id, set()).add(ws)

    def disconnect_global(self, ws: WebSocket) -> None:
        self.global_connections.discard(ws)

    def disconnect_project(self, ws: WebSocket, project_id: str) -> None:
        conns = self.project_connections.get(project_id)
        if conns:
            conns.discard(ws)

    async def broadcast(self, message: dict, project_id: str | None = None) -> None:
        dead: list[WebSocket] = []
        for ws in list(self.global_connections):
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self.global_connections.discard(ws)

        if project_id:
            dead = []
            for ws in list(self.project_connections.get(project_id, set())):
                try:
                    await ws.send_json(message)
                except Exception:  # noqa: BLE001
                    dead.append(ws)
            for ws in dead:
                self.project_connections[project_id].discard(ws)

    def broadcast_threadsafe(self, message: dict, project_id: str | None = None) -> None:
        if self.loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(self.broadcast(message, project_id), self.loop)
        except Exception:  # noqa: BLE001
            logger.exception("Fallo al difundir mensaje por websocket")


manager = ConnectionManager()
