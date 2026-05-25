import json
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.story import (
    CharacterSheet,
    EpisodeOutline,
    SceneBreakdown,
    StoryBible,
    StoryBibleRequest,
    WorldInfo,
    PowerSystem,
    Tone,
)

from app.config import settings
from app.models.character import CharacterModel
from app.models.project import ProjectModel
from app.services.llm.base import LLMProvider, LLMGenerationError
from app.services.llm.ollama import OllamaProvider
from app.services.llm.openai_compat import OpenAICompatProvider
from app.services.prompts.compiler import PromptCompiler


class CharacterList(BaseModel):
    characters: list[dict]


class EpisodeList(BaseModel):
    episodes: list[dict]


class SceneList(BaseModel):
    scenes: list[dict]


def create_llm_provider() -> LLMProvider:
    if settings.llm_provider == "openai_compat":
        return OpenAICompatProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
        )
    return OllamaProvider(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        max_tokens=settings.llm_max_tokens,
    )


class StoryBibleService:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db
        self.llm = create_llm_provider()
        self.compiler = PromptCompiler()

    async def generate_story_bible(self, request: StoryBibleRequest) -> StoryBible:
        target_duration = request.episode_duration_minutes * 60

        # Step 1: System prompt
        system = self.compiler.compile_system(
            language=request.language,
            target_duration_seconds=target_duration * request.target_episodes,
            style=request.style.value,
        )

        # Step 2: World building
        world_prompt = self.compiler.compile_world_builder(
            concept=request.concept, style=request.style.value
        )
        world_data = await self.llm.generate(system, world_prompt, WorldInfo)
        world = WorldInfo(**world_data)
        world_summary = json.dumps(world_data, ensure_ascii=False, indent=2)

        # Step 3: Character sheets
        char_prompt = self.compiler.compile_character_sheet(
            world_summary=world_summary, style=request.style.value
        )
        chars_data = await self.llm.generate(system, char_prompt, CharacterList)
        characters = chars_data.get("characters", [])

        # Step 4: Episode outlines
        ep_prompt = self.compiler.compile_episodes(
            world_summary=world_summary,
            character_summary=json.dumps(characters[:3], ensure_ascii=False),
            episode_count=request.target_episodes,
            episode_duration_minutes=request.episode_duration_minutes,
        )
        eps_data = await self.llm.generate(system, ep_prompt, EpisodeList)
        episodes = [EpisodeOutline(**ep) for ep in eps_data.get("episodes", [])]

        # Step 5: Scene breakdown per episode
        scenes = []
        for ep in episodes:
            scene_prompt = self.compiler.compile_scene_breakdown(
                episode_number=ep.episode_number,
                episode_title=ep.title,
                episode_summary=ep.summary,
                episode_duration_seconds=target_duration,
            )
            scenes_data = await self.llm.generate(system, scene_prompt, SceneList)
            scenes.extend(
                SceneBreakdown(**s) for s in scenes_data.get("scenes", [])
            )

        return StoryBible(
            project_id=UUID(int=0),  # placeholder, set when saved
            world=world,
            power_system=PowerSystem(),
            tone=Tone(),
            characters=characters,
            episodes=episodes,
            scene_breakdowns=scenes,
        )

    async def save_bible_to_project(
        self, project_id: UUID, bible: StoryBible
    ) -> None:
        if not self.db:
            raise RuntimeError("StoryBibleService has no DB session")

        bible.project_id = project_id

        # Save story_json to project
        result = await self.db.execute(
            select(ProjectModel).where(ProjectModel.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise LLMGenerationError(f"Project {project_id} not found")

        project.story_json = bible.model_dump()

        # Auto-create character records from story bible
        for char_data in bible.characters:
            name = char_data.get("name", "")
            if not name:
                continue

            # Dedup: find existing character with same name in project
            existing = (
                await self.db.execute(
                    select(CharacterModel).where(
                        CharacterModel.project_id == project_id,
                        CharacterModel.name == name,
                    )
                )
            ).scalar_one_or_none()

            if existing:
                existing.character_json = char_data
                existing.role = char_data.get("role", existing.role)
            else:
                new_char = CharacterModel(
                    project_id=project_id,
                    name=name,
                    role=char_data.get("role"),
                    character_json=char_data,
                )
                self.db.add(new_char)

        await self.db.commit()

    async def load_bible_from_project(
        self, project_id: UUID
    ) -> StoryBible | None:
        if not self.db:
            raise RuntimeError("StoryBibleService has no DB session")

        result = await self.db.execute(
            select(ProjectModel).where(ProjectModel.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project or not project.story_json:
            return None

        return StoryBible(**project.story_json)
