"""WebSocket router for real-time job progress."""
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import async_session_factory
from app.models.project import ProjectModel
from app.services.websocket import manager
from app.services.job import JobService

router = APIRouter()


@router.websocket("/ws/projects/{project_id}")
async def project_ws(
    websocket: WebSocket,
    project_id: UUID,
):
    """WebSocket endpoint for live job progress per project."""
    async with async_session_factory() as db:
        result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
        if not result.scalar_one_or_none():
            await websocket.close(code=4004, reason="Project not found")
            return

        await manager.connect(project_id, websocket)

        try:
            svc = JobService(db)
            jobs = await svc.list_by_project(project_id)
            await websocket.send_json({
                "type": "init",
                "jobs": [j.model_dump() for j in jobs],
            })

            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            manager.disconnect(project_id, websocket)
        except Exception:
            manager.disconnect(project_id, websocket)
