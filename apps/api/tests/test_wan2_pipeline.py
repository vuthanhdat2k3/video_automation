from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import pytest

from app.exceptions import NotFoundException
from app.services.wan2_video_gen import Wan2VideoGenService, Wan2VideoGenError
from app.models.project import ProjectModel
from app.models.scene import SceneModel
from app.models.shot import ShotModel
from app.models.asset import AssetModel

@pytest.mark.asyncio
async def test_wan2_video_gen_shot_not_found(db_session):
    """Test Wan2VideoGenService raises NotFoundException when shot doesn't exist."""
    svc = Wan2VideoGenService(db_session)
    with pytest.raises(NotFoundException):
        await svc.generate_for_shot(uuid4())

@pytest.mark.asyncio
async def test_wan2_video_gen_missing_keyframe_id(db_session):
    """Test Wan2VideoGenService raises Wan2VideoGenError when shot lacks keyframe asset ID."""
    db = db_session
    project = ProjectModel(name="Cultivation Project", style="2d_chinese_donghua", aspect_ratio="9:16")
    db.add(project)
    await db.flush()

    scene = SceneModel(project_id=project.id, title="Urban Arena", order_index=0)
    db.add(scene)
    await db.flush()

    shot = ShotModel(
        scene_id=scene.id,
        order_index=0,
        duration_seconds=4.0,
        description="Lâm Hàn flies with lightning",
        keyframe_asset_id=None,  # Missing keyframe ID
    )
    db.add(shot)
    await db.flush()
    shot_id = shot.id
    await db.commit()

    svc = Wan2VideoGenService(db)
    with pytest.raises(Wan2VideoGenError) as exc:
        await svc.generate_for_shot(shot_id)
    assert "does not have a keyframe image" in str(exc.value)

@pytest.mark.asyncio
@patch("app.services.wan2_video_gen._get_storage")
async def test_wan2_video_gen_success(mock_get_storage, db_session):
    """Test successful Wan2.1-14B video generation pipeline execution."""
    db = db_session
    project = ProjectModel(name="Cultivation Project", style="2d_chinese_donghua", aspect_ratio="9:16")
    db.add(project)
    await db.flush()

    scene = SceneModel(project_id=project.id, title="Urban Arena", order_index=0)
    db.add(scene)
    await db.flush()

    # Create dummy keyframe asset
    asset = AssetModel(
        project_id=project.id,
        type="keyframes",
        filename="dummy_kf.png",
        path="keyframes/dummy_kf.png",
    )
    db.add(asset)
    await db.flush()

    shot = ShotModel(
        scene_id=scene.id,
        order_index=0,
        duration_seconds=4.0,
        description="Lâm Hàn launches golden dragon blast",
        keyframe_asset_id=asset.id,
        generation_prompt="Premium test prompt",
    )
    db.add(shot)
    await db.flush()
    shot_id = shot.id
    await db.commit()

    # Mock storage
    mock_storage = MagicMock()
    mock_path = MagicMock()
    mock_path.exists.return_value = True
    mock_path.read_bytes.return_value = b"mocked_png_bytes"
    mock_storage.get_asset_path.return_value = mock_path
    mock_get_storage.return_value = mock_storage

    # Initialize Service and Mock ComfyUI Client
    svc = Wan2VideoGenService(db)
    svc.comfyui = AsyncMock()
    svc.comfyui.upload_image = AsyncMock(return_value="uploaded_dummy_kf.png")
    svc.comfyui.generate_with_workflow_dict = AsyncMock(return_value=b"mocked_mp4_bytes")

    video_bytes, prompt = await svc.generate_for_shot(shot_id)

    # Verification
    assert video_bytes == b"mocked_mp4_bytes"
    assert prompt == "Premium test prompt"
    svc.comfyui.upload_image.assert_called_once_with(b"mocked_png_bytes", "dummy_kf.png")
    svc.comfyui.generate_with_workflow_dict.assert_called_once()
