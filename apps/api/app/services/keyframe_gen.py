import json
import shutil
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import NotFoundException
from app.models.asset import AssetModel
from app.models.character import CharacterModel
from app.models.project import ProjectModel
from app.models.scene import SceneModel
from app.models.shot import ShotModel
from app.services.animation_common import (
    build_character_descriptions,
    resolve_style,
    translate_text,
)
from app.services.asset_utils import _get_storage
from app.services.comfyui.client import ComfyUIClient


class KeyframeGenerationError(Exception):
    pass


class KeyframeGenService:
    """Generate keyframe images for shots with character descriptions."""

    KEYFRAME_PROMPT_TEMPLATE = (
        "{style}, {scene_context} {shot_description}, "
        "camera: {camera_angle} angle, {camera_framing} framing, {camera_movement} movement, "
        "{character_desc} "
        "high quality, detailed, sharp focus, cinematic lighting"
    )

    def __init__(self, db: AsyncSession, comfyui: ComfyUIClient | None = None):
        self.db = db
        self.comfyui = comfyui or ComfyUIClient(
            base_url=settings.comfyui_base_url,
            timeout=settings.comfyui_timeout,
        )

    async def generate_for_shot(self, shot_id: UUID) -> tuple[bytes, str]:
        """Generate keyframe image for a shot. Returns (png_bytes, prompt)."""
        # Eager-load Shot + Scene + Project in one JOIN query
        stmt = (
            select(ShotModel, SceneModel, ProjectModel)
            .join(SceneModel, ShotModel.scene_id == SceneModel.id)
            .join(ProjectModel, SceneModel.project_id == ProjectModel.id, isouter=True)
            .where(ShotModel.id == shot_id)
        )
        row = (await self.db.execute(stmt)).one_or_none()
        if not row:
            raise NotFoundException(f"Shot {shot_id} not found")
        shot: ShotModel = row[0]
        scene: SceneModel | None = row[1]
        project: ProjectModel | None = row[2]

        scene_desc = scene.description if scene else ""
        style = resolve_style(project.style) if project else "anime style"

        # Build character description from project characters
        char_desc = ""
        ref_image_filename = None
        if scene:
            char_parts = await build_character_descriptions(self.db, scene.project_id)
            if char_parts:
                char_desc = "; ".join(char_parts) + ". "

            # Handle IP-Adapter reference image
            char_result = await self.db.execute(
                select(CharacterModel).where(CharacterModel.project_id == scene.project_id)
            )
            for c in char_result.scalars().all():
                if c.reference_asset_id:
                    asset_res = await self.db.execute(
                        select(AssetModel).where(AssetModel.id == c.reference_asset_id)
                    )
                    asset = asset_res.scalar_one_or_none()
                    if asset:
                        src_path = _get_storage().get_asset_path(scene.project_id, asset.path)
                        if src_path.exists():
                            comfy_input_dir = Path(settings.comfyui_input_dir)
                            comfy_input_dir.mkdir(parents=True, exist_ok=True)
                            dest_path = comfy_input_dir / asset.filename
                            shutil.copy2(src_path, dest_path)
                            ref_image_filename = asset.filename

        cam = shot.camera
        scene_desc_en = await translate_text(scene_desc)
        shot_desc_en = await translate_text(shot.description or "")

        prompt = self.KEYFRAME_PROMPT_TEMPLATE.format(
            style=style,
            scene_context=scene_desc_en,
            shot_description=shot_desc_en,
            camera_angle=cam.angle or "eye-level",
            camera_framing=cam.framing or "medium",
            camera_movement=cam.movement or "static",
            character_desc=char_desc,
        )

        workflow_path = Path(__file__).parent / "comfyui" / "workflows" / "keyframe_gen.json"
        with open(workflow_path) as f:
            workflow = json.load(f)

        if "9" not in workflow or workflow["9"].get("class_type") != "KSampler":
            raise KeyframeGenerationError("workflow missing KSampler node (id=9)")

        overrides = {
            "3": {"inputs": {"text": prompt}},
            "4": {"inputs": {"text": "low quality, blurry, bad anatomy, extra limbs, watermark, text, ugly, deformed, realism, photorealistic, 3d render"}},
        }

        if ref_image_filename:
            overrides["7"] = {"inputs": {"image": ref_image_filename}}
        else:
            # Bypass IP-Adapter: connect checkpoint model directly to KSampler
            overrides["9"] = {"inputs": {"model": ["1", 0]}}
            # Remove unused IP-Adapter nodes so ComfyUI does not error on missing models
            for node_id in ["5", "6", "7", "8"]:
                if node_id in workflow:
                    del workflow[node_id]

        png = await self.comfyui.generate_with_workflow_dict(workflow, overrides=overrides)
        return png, prompt
