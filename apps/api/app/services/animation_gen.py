from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import NotFoundException
from app.models.project import ProjectModel
from app.models.scene import SceneModel
from app.models.shot import ShotModel
from app.services.animation_common import (
    build_character_descriptions,
    resolve_style,
    translate_text,
)
from app.services.comfyui.client import ComfyUIClient
from app.logging import get_logger

logger = get_logger("animation_gen")


class AnimationGenerationError(Exception):
    pass


class AnimationGenService:
    """Generate fluid 2D animation clips using AnimateDiff.

    Deprecated: Use Wan2VideoGenService instead (Wan2.1-14B).
    Will be removed in a future version.
    """

    def __init__(self, db: AsyncSession, comfyui: ComfyUIClient | None = None):
        logger.warning("AnimationGenService is deprecated, use Wan2VideoGenService instead")
        self.db = db
        self.comfyui = comfyui or ComfyUIClient(
            base_url=settings.comfyui_base_url,
            timeout=settings.comfyui_timeout,
        )

    ANIMATION_PROMPT_TEMPLATE = (
        "{style}, {scene_context} {shot_description}, fluid motion, high quality 2D animation, "
        "camera: {camera_angle} angle, {camera_framing} framing, {camera_movement} movement, "
        "{character_desc} "
        "high quality, detailed, sharp focus, cinematic lighting"
    )

    async def generate_for_shot(self, shot_id: UUID) -> tuple[bytes, str]:
        """Generate animated MP4 video clip for a shot. Returns (mp4_bytes, prompt)."""
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
        if scene:
            char_parts = await build_character_descriptions(self.db, scene.project_id)
            if char_parts:
                char_desc = "; ".join(char_parts) + ". "

        cam = shot.camera
        scene_desc_en = await translate_text(scene_desc)
        shot_desc_en = await translate_text(shot.description or "")

        prompt = self.ANIMATION_PROMPT_TEMPLATE.format(
            style=style,
            scene_context=scene_desc_en,
            shot_description=shot_desc_en,
            camera_angle=cam.angle or "eye-level",
            camera_framing=cam.framing or "medium",
            camera_movement=cam.movement or "static",
            character_desc=char_desc,
        )

        overrides = {
            "6": {"inputs": {"text": prompt}},
            "7": {"inputs": {"text": "low quality, blurry, bad anatomy, extra limbs, watermark, text, ugly, static, plain background"}},
        }

        mp4_bytes = await self.comfyui.generate_with_workflow("animation_gen.json", overrides=overrides)
        return mp4_bytes, prompt
