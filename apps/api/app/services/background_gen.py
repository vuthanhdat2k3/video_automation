from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import NotFoundException
from app.models.project import ProjectModel
from app.models.scene import SceneModel
from app.services.animation_common import resolve_style
from app.services.comfyui.client import ComfyUIClient


class BackgroundGenerationError(Exception):
    pass


class BackgroundGenService:
    """Generate background images from scene continuity state."""

    BACKGROUND_PROMPT_TEMPLATE = (
        "{style} landscape, {scene_title}, {description}, "
        "{time_of_day}, {weather}, "
        "{lighting} lighting, {mood} atmosphere, "
        "distant background, scenic environment, no characters, "
        "high quality, detailed, cinematic, beautiful scenery"
    )

    def __init__(self, db: AsyncSession, comfyui: ComfyUIClient | None = None):
        self.db = db
        self.comfyui = comfyui or ComfyUIClient(
            base_url=settings.comfyui_base_url,
            timeout=settings.comfyui_timeout,
        )

    async def generate_for_scene(self, scene_id: UUID) -> tuple[bytes, str]:
        """Generate background image for a scene. Returns (png_bytes, prompt)."""
        result = await self.db.execute(select(SceneModel).where(SceneModel.id == scene_id))
        scene = result.scalar_one_or_none()
        if not scene:
            raise NotFoundException(f"Scene {scene_id} not found")

        proj_result = await self.db.execute(
            select(ProjectModel).where(ProjectModel.id == scene.project_id)
        )
        project = proj_result.scalar_one_or_none()

        style = resolve_style(project.style) if project else "anime style"
        cont = scene.continuity
        prompt = self.BACKGROUND_PROMPT_TEMPLATE.format(
            style=style,
            scene_title=scene.title or "",
            description=scene.description or "",
            time_of_day=cont.time_of_day or "daytime",
            weather=cont.weather or "clear",
            lighting=cont.lighting or "natural",
            mood=cont.mood or "peaceful",
        )

        overrides = {
            "6": {"inputs": {"text": prompt}},
            "7": {"inputs": {"text": "low quality, blurry, character, person, human, people, watermark, text"}},
        }
        png = await self.comfyui.generate_with_workflow("background_gen.json", overrides=overrides)
        return png, prompt
