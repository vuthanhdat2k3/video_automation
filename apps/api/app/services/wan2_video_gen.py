from uuid import UUID
import json
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import NotFoundException
from app.models.shot import ShotModel
from app.models.scene import SceneModel
from app.models.project import ProjectModel
from app.models.asset import AssetModel
from app.services.comfyui.client import ComfyUIClient
from app.services.asset_utils import _get_storage

class Wan2VideoGenError(Exception):
    pass

class Wan2VideoGenService:
    """Service to generate premium Image-to-Video clips using Wan2.1-14B on remote/local ComfyUI."""

    def __init__(self, db: AsyncSession, comfyui: ComfyUIClient | None = None):
        self.db = db
        base_url = settings.wan2_comfyui_base_url or settings.comfyui_base_url
        self.comfyui = comfyui or ComfyUIClient(
            base_url=base_url,
            timeout=settings.comfyui_timeout,
        )

    async def generate_for_shot(self, shot_id: UUID) -> tuple[bytes, str]:
        """Generate animated MP4 video bytes for a shot. Returns (video_bytes, prompt)."""
        # 1. Fetch Shot, Scene, Project
        result = await self.db.execute(
            select(ShotModel).where(ShotModel.id == shot_id)
        )
        shot = result.scalar_one_or_none()
        if not shot:
            raise NotFoundException(f"Shot {shot_id} not found")

        scene_res = await self.db.execute(
            select(SceneModel).where(SceneModel.id == shot.scene_id)
        )
        scene = scene_res.scalar_one_or_none()
        project_id = scene.project_id if scene else shot.id

        project = None
        if scene and scene.project_id:
            proj_res = await self.db.execute(
                select(ProjectModel).where(ProjectModel.id == scene.project_id)
            )
            project = proj_res.scalar_one_or_none()

        # 2. Get positive prompt (fallback to shot description if not already generated)
        prompt = shot.generation_prompt
        if not prompt:
            prompt = (
                f"2D Chinese donghua animation style, masterpiece, best quality, "
                f"{shot.description or ''}, dramatic cinematic lighting, smooth motion, high-end production"
            )

        # 3. Load Keyframe Image Asset
        if not shot.keyframe_asset_id:
            raise Wan2VideoGenError(f"Shot {shot_id} does not have a keyframe image generated. Please generate keyframe first.")

        asset_res = await self.db.execute(
            select(AssetModel).where(AssetModel.id == shot.keyframe_asset_id)
        )
        keyframe_asset = asset_res.scalar_one_or_none()
        if not keyframe_asset:
            raise NotFoundException(f"Keyframe asset {shot.keyframe_asset_id} not found")

        # 4. Read keyframe image bytes and upload to ComfyUI input folder
        storage = _get_storage()
        keyframe_path = storage.get_asset_path(project_id, keyframe_asset.path)
        if not keyframe_path.exists():
            raise Wan2VideoGenError(f"Keyframe image file not found at {keyframe_path}")
        
        image_bytes = keyframe_path.read_bytes()
        remote_filename = await self.comfyui.upload_image(image_bytes, keyframe_asset.filename)

        # 5. Load and configure Wan2.1-14B workflow
        workflow_path = Path(__file__).parent / "comfyui" / "workflows" / "wan2_1_i2v_14b.json"
        with open(workflow_path) as f:
            workflow = json.load(f)

        # Determine dimensions based on aspect ratio (default vertical 9:16)
        width, height = 480, 832
        if project and project.aspect_ratio == "16:9":
            width, height = 832, 480

        overrides = {
            "5": {"inputs": {"image": remote_filename}},
            "6": {
                "inputs": {
                    "positive_prompt": prompt,
                    "negative_prompt": "blurry, low quality, static, deformed, ugly, flickering, morphing, real-world, photorealistic, 3d render"
                }
            },
            "7": {
                "inputs": {
                    "generation_width": width,
                    "generation_height": height
                }
            }
        }

        try:
            video_bytes = await self.comfyui.generate_with_workflow_dict(workflow, overrides=overrides)
            return video_bytes, prompt
        except Exception as e:
            raise Wan2VideoGenError(f"Wan2.1 video generation failed: {e}") from e
