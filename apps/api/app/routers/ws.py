"""WebSocket router for real-time job progress."""
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import ProjectModel
from app.exceptions import NotFoundException
from app.services.websocket import manager
from app.services.job import JobService

router = APIRouter()


@router.websocket("/ws/projects/{project_id}")
async def project_ws(
    websocket: WebSocket,
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """WebSocket endpoint for live job progress per project."""
    # Validate project exists
    result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    if not result.scalar_one_or_none():
        await websocket.close(code=4004, reason="Project not found")
        return

    await manager.connect(project_id, websocket)

    # Send initial state — all active jobs
    try:
        svc = JobService(db)
        jobs = await svc.list_by_project(project_id)
        await websocket.send_json({
            "type": "init",
            "jobs": [j.model_dump() for j in jobs],
        })

        # Keep connection alive — listen for pings
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(project_id, websocket)
    except Exception:
        manager.disconnect(project_id, websocket)
