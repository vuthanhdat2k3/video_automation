"""Tests for lip sync service."""
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from app.services.lipsync import LipSyncService, LipSyncError
from app.models.shot import ShotModel
from pathlib import Path


@pytest.mark.asyncio
async def test_needs_lipsync_true():
    """Shot with description + keyframe + audio → needs lipsync."""
    shot = ShotModel(
        scene_id="00000000-0000-0000-0000-000000000001",
        order_index=0, duration_seconds=4.0,
        description="Hello world",
        keyframe_asset_id="00000000-0000-0000-0000-000000000002",
        audio_asset_id="00000000-0000-0000-0000-000000000003",
    )
    assert LipSyncService.needs_lipsync(shot) is True


@pytest.mark.asyncio
async def test_needs_lipsync_no_description():
    """Shot without description → no lipsync needed."""
    shot = ShotModel(
        scene_id="00000000-0000-0000-0000-000000000001",
        order_index=0, duration_seconds=4.0,
        description=None,
        keyframe_asset_id="00000000-0000-0000-0000-000000000002",
        audio_asset_id="00000000-0000-0000-0000-000000000003",
    )
    assert LipSyncService.needs_lipsync(shot) is False


@pytest.mark.asyncio
async def test_needs_lipsync_no_keyframe():
    """Shot without keyframe → no lipsync needed."""
    shot = ShotModel(
        scene_id="00000000-0000-0000-0000-000000000001",
        order_index=0, duration_seconds=4.0,
        description="Hello",
        keyframe_asset_id=None,
        audio_asset_id="00000000-0000-0000-0000-000000000003",
    )
    assert LipSyncService.needs_lipsync(shot) is False


@pytest.mark.skip(reason="integration: requires ffmpeg + valid media files")
@pytest.mark.asyncio
async def test_lipsync_fallback():
    """FFmpeg fallback generates MP4 from portrait + audio."""
    import tempfile, shutil
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not available")
    ls = LipSyncService()

    # Create a minimal 1x1 PNG as portrait
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        img = tmp / "portrait.png"
        img.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        audio = tmp / "audio.mp3"
        audio.write_bytes(b"\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        out = tmp / "out.mp4"

        result = await ls.generate_talking_head(img, audio, out)
        assert result.exists()
        assert result.suffix == ".mp4"


@pytest.mark.asyncio
async def test_generate_lipsync_endpoint(client, db_session):
    """POST /shots/{id}/generate-lipsync returns job_id."""
    from app.models.project import ProjectModel
    from app.models.scene import SceneModel
    from unittest.mock import patch, AsyncMock

    db = db_session
    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    scene = SceneModel(project_id=project.id, title="Lip Sync", order_index=0)
    db.add(scene)
    await db.commit()
    await db.refresh(scene)

    shot = ShotModel(
        scene_id=scene.id, order_index=0, duration_seconds=4.0,
        description="Dialogue", keyframe_asset_id=None,
    )
    db.add(shot)
    await db.commit()
    await db.refresh(shot)

    with patch("app.routers.shots.dispatch_job", new_callable=AsyncMock) as mock:
        mock.return_value.id = shot.id
        resp = await client.post(f"/api/v1/shots/{shot.id}/generate-lipsync")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "job_id" in data
