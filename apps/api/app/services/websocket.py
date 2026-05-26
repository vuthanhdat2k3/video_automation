"""WebSocket connection manager for job progress broadcasting."""
import json
from uuid import UUID

from fastapi import WebSocket


class JobProgressManager:
    """Manages WebSocket connections per project for real-time job updates."""

    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, project_id: UUID, ws: WebSocket) -> None:
        await ws.accept()
        pid = str(project_id)
        if pid not in self._connections:
            self._connections[pid] = set()
        self._connections[pid].add(ws)

    def disconnect(self, project_id: UUID, ws: WebSocket) -> None:
        pid = str(project_id)
        conns = self._connections.get(pid)
        if conns:
            conns.discard(ws)
            if not conns:
                del self._connections[pid]

    async def broadcast(self, project_id: UUID, event: dict) -> None:
        pid = str(project_id)
        conns = self._connections.get(pid, set())
        if not conns:
            return
        payload = json.dumps(event)
        stale = set()
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.add(ws)
        for ws in stale:
            conns.discard(ws)
        if not conns and pid in self._connections:
            del self._connections[pid]


manager = JobProgressManager()
