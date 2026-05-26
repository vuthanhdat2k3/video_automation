from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import NotFoundException
from app.models.character import CharacterModel
from app.models.project import ProjectModel
from app.models.scene import SceneModel
from app.models.shot import ShotModel
from app.services.comfyui.client import ComfyUIClient

STYLE_MAP = {
    "2d_chinese_donghua": "Chinese donghua animation style",
    "2d_anime": "anime style, Japanese animation",
    "2d_western": "western 2D animation style",
    "3d_pixar": "3D Pixar-style render",
    "3d_realistic": "photorealistic 3D render",
}


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
        result = await self.db.execute(
            select(ShotModel).where(ShotModel.id == shot_id)
        )
        shot = result.scalar_one_or_none()
        if not shot:
            raise NotFoundException(f"Shot {shot_id} not found")

        scene_result = await self.db.execute(
            select(SceneModel).where(SceneModel.id == shot.scene_id)
        )
        scene = scene_result.scalar_one_or_none()
        scene_desc = scene.description if scene else ""

        style = "anime style"
        if scene:
            proj_result = await self.db.execute(
                select(ProjectModel).where(ProjectModel.id == scene.project_id)
            )
            project = proj_result.scalar_one_or_none()
            if project:
                style = STYLE_MAP.get(project.style, "anime style")

        # Build character description from project characters
        char_desc = ""
        if scene:
            char_result = await self.db.execute(
                select(CharacterModel).where(CharacterModel.project_id == scene.project_id)
            )
            chars = char_result.scalars().all()
            if chars:
                parts = []
                for c in chars:
                    dna = c.character_dna
                    if dna:
                        trait = []
                        if dna.gender and dna.age:
                            trait.append(f"{dna.age}-year-old {dna.gender}")
                        if dna.hair_color and dna.hair_style:
                            trait.append(f"{dna.hair_color} {dna.hair_style}")
                        if dna.eye_color:
                            trait.append(f"{dna.eye_color} eyes")
                        if dna.clothing_style:
                            trait.append(f"wearing {dna.clothing_style}")
                        if trait:
                            name = c.name or ""
                            parts.append(f"character {name}: {', '.join(trait)}")
                if parts:
                    char_desc = "; ".join(parts) + ". "

        cam = shot.camera
        prompt = self.KEYFRAME_PROMPT_TEMPLATE.format(
            style=style,
            scene_context=scene_desc or "",
            shot_description=shot.description or "",
            camera_angle=cam.angle or "eye-level",
            camera_framing=cam.framing or "medium",
            camera_movement=cam.movement or "static",
            character_desc=char_desc,
        )

        overrides = {
            "6": {"inputs": {"text": prompt}},
            "7": {"inputs": {"text": "low quality, blurry, bad anatomy, extra limbs, watermark, text, ugly"}},
        }
        png = await self.comfyui.generate_with_workflow("keyframe_gen.json", overrides=overrides)
        return png, prompt
