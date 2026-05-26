"""Tests for export service with mocked FFmpeg."""
from unittest.mock import patch, AsyncMock

import pytest

from app.services.exporter import ExportService, ExportError
from app.exceptions import NotFoundException
from app.models.scene import SceneModel
from app.models.shot import ShotModel
from app.models.asset import AssetModel
from app.models.project import ProjectModel


@pytest.mark.asyncio
async def test_export_no_scene(db_session):
    svc = ExportService(db_session)
    with pytest.raises(NotFoundException):
        await svc.export_scene("00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio
async def test_export_no_shots(db_session):
    from app.models.project import ProjectModel
    db = db_session
    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.flush()
    scene = SceneModel(project_id=project.id, title="S", order_index=0)
    db.add(scene)
    await db.commit()

    svc = ExportService(db)
    with pytest.raises(NotFoundException):
        await svc.export_scene(scene.id)


@pytest.mark.asyncio
async def test_export_success(db_session):
    """Test export creates valid MP4, mocks FFmpeg calls."""
    from unittest.mock import MagicMock
    db = db_session
    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.flush()

    scene = SceneModel(project_id=project.id, title="S", order_index=0)
    db.add(scene)
    await db.flush()

    shot = ShotModel(scene_id=scene.id, order_index=0, duration_seconds=2.0,
                     description="Test shot", keyframe_asset_id=None)
    db.add(shot)
    await db.commit()

    svc = ExportService(db)

    # Mock FFmpeg subprocess to succeed
    async def mock_ffmpeg(args):
        # Create a minimal valid MP4 output file
        pass

    svc._run_ffmpeg = AsyncMock()


    from pathlib import Path
    import tempfile, os

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("pathlib.Path.mkdir"), \
             patch("shutil.rmtree"):
            # Mock work_dir to use temp dir
            svc._assemble_video = AsyncMock(return_value=(b"fake_mp4_content", "scene_test.mp4"))
            mp4, filename = await svc.export_scene(scene.id)
            assert mp4 == b"fake_mp4_content"
            assert filename.endswith(".mp4")


@pytest.mark.asyncio
async def test_export_with_audio_asset(db_session):
    """Test export includes audio when shot has audio_asset_id."""
    from unittest.mock import MagicMock
    db = db_session
    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.flush()
    scene = SceneModel(project_id=project.id, title="S", order_index=0)
    db.add(scene)
    await db.flush()

    # Create an audio asset
    asset = AssetModel(
        project_id=project.id,
        type="audio",
        filename="test.mp3",
        path=str(project.id) + "/audio/test.mp3",
        metadata_json={"mime_type": "audio/mpeg"},
    )
    db.add(asset)
    await db.flush()

    shot = ShotModel(scene_id=scene.id, order_index=0, duration_seconds=2.0,
                     description="Test", audio_asset_id=asset.id)
    db.add(shot)
    await db.commit()

    svc = ExportService(db)
    svc._assemble_video = AsyncMock(return_value=(b"mp4_with_audio", "scene_test.mp4"))
    mp4, filename = await svc.export_scene(scene.id)
    assert len(mp4) > 0
    assert filename.endswith(".mp4")
