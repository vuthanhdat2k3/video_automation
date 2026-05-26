"""Tests for WebSocket, logging, and cleanup services."""
import json
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from app.services.websocket import JobProgressManager


@pytest.mark.asyncio
async def test_ws_connect_disconnect():
    """Test WebSocket connection lifecycle."""
    mgr = JobProgressManager()
    ws = AsyncMock()

    await mgr.connect("proj-1", ws)
    assert "proj-1" in mgr._connections
    assert ws in mgr._connections["proj-1"]

    mgr.disconnect("proj-1", ws)
    assert "proj-1" not in mgr._connections


@pytest.mark.asyncio
async def test_ws_broadcast():
    """Test broadcast sends to all connections."""
    mgr = JobProgressManager()
    ws1 = AsyncMock()
    ws2 = AsyncMock()

    await mgr.connect("proj-1", ws1)
    await mgr.connect("proj-1", ws2)

    await mgr.broadcast("proj-1", {"type": "job.completed", "job": {"id": "x"}})

    expected = json.dumps({"type": "job.completed", "job": {"id": "x"}})
    ws1.send_text.assert_called_once_with(expected)
    ws2.send_text.assert_called_once_with(expected)


@pytest.mark.asyncio
async def test_ws_broadcast_stale_removed():
    """Test stale connections are cleaned up on broadcast."""
    mgr = JobProgressManager()
    ws = AsyncMock()
    ws.send_text = AsyncMock(side_effect=Exception("gone"))

    await mgr.connect("proj-1", ws)
    await mgr.broadcast("proj-1", {"type": "job.failed"})

    assert "proj-1" not in mgr._connections


@pytest.mark.asyncio
async def test_ws_broadcast_empty():
    """Test broadcast with no connections does nothing."""
    mgr = JobProgressManager()
    await mgr.broadcast("proj-1", {"type": "test"})  # should not raise


@pytest.mark.asyncio
async def test_cleanup_service(db_session):
    """Test cleanup deletes old jobs."""
    from datetime import datetime, timedelta, timezone
    from app.models.job import JobModel
    from app.models.project import ProjectModel
    from app.services.cleanup import cleanup_old_jobs

    db = db_session
    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.flush()

    # Create an old job
    old = JobModel(
        project_id=project.id,
        type="generate_keyframe",
        status="completed",
        updated_at=datetime.now(timezone.utc) - timedelta(hours=200),
    )
    db.add(old)
    await db.flush()

    # Create a recent job
    recent = JobModel(
        project_id=project.id,
        type="generate_audio",
        status="failed",
    )
    db.add(recent)
    await db.commit()

    count = await cleanup_old_jobs(db, max_age_hours=168)
    assert count == 1  # only the old one deleted


@pytest.mark.asyncio
async def test_logging_format():
    """Test structured formatter produces valid JSON."""
    from app.logging import StructuredFormatter
    import logging

    fmt = StructuredFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello world",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-123"
    output = fmt.format(record)
    data = json.loads(output)
    assert data["message"] == "hello world"
    assert data["request_id"] == "req-123"
    assert data["level"] == "INFO"
