"""Shared utilities for animation generation services."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.character import CharacterModel
from app.services.story import create_llm_provider
from app.logging import get_logger

logger = get_logger("animation_common")

STYLE_MAP = {
    "2d_chinese_donghua": "Chinese donghua animation style",
    "2d_anime": "anime style, Japanese animation",
    "2d_western": "western 2D animation style",
    "3d_pixar": "3D Pixar-style render",
    "3d_realistic": "photorealistic 3D render",
}


async def translate_text(text: str) -> str:
    """Translate Vietnamese text to English using LLM. Falls back to original on failure."""
    if not text or not text.strip():
        return ""
    try:
        llm = create_llm_provider()
        translated = await llm.chat([
            {"role": "system", "content": "You are a professional translator. Translate the following Vietnamese text into high-quality descriptive English. Output ONLY the raw translation, without quotes, explanations, or introductory text."},
            {"role": "user", "content": text}
        ])
        translated = translated.strip()
        if translated:
            return translated
    except Exception:
        logger.warning("translation failed, falling back to original text", exc_info=True)
    return text


def resolve_style(project_style: str | None) -> str:
    """Resolve project style to a descriptive string."""
    if not project_style:
        return "anime style"
    return STYLE_MAP.get(project_style, "anime style")


async def build_character_descriptions(db: AsyncSession, project_id) -> list[str]:
    """Build character trait descriptions for a project."""
    result = await db.execute(
        select(CharacterModel).where(CharacterModel.project_id == project_id)
    )
    chars = result.scalars().all()
    parts = []
    for c in chars:
        dna = c.character_dna
        if not dna:
            continue
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
    return parts
