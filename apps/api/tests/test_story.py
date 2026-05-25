import json
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel

from ai_2d_shared.enums import Style
from ai_2d_shared.story import StoryBibleRequest
from app.services.llm.base import LLMProvider, extract_json_block
from app.services.story import StoryBibleService, CharacterList, WorldInfo


class TestExtractJsonBlock:
    def test_raw_json(self):
        result = extract_json_block('{"key": "value"}')
        assert result == '{"key": "value"}'

    def test_markdown_fenced(self):
        result = extract_json_block('```json\n{"key": "value"}\n```')
        assert result == '{"key": "value"}'

    def test_markdown_fenced_no_lang(self):
        result = extract_json_block('```\n{"key": "value"}\n```')
        assert result == '{"key": "value"}'


class TestLLMProvider:
    @pytest.mark.asyncio
    async def test_generate_with_retry_success_first_try(self):
        """Test that generate_with_retry returns parsed schema on success."""
        class SuccessProvider(LLMProvider):
            async def generate(self, system, user, schema):
                return await self.generate_with_retry(system, user, schema)
            async def chat(self, messages):
                return '{"name": "Test", "era": "modern", "location": "City", "society": "S", "atmosphere": "A", "rules": [], "factions": []}'

        result = await SuccessProvider().generate_with_retry("s", "u", WorldInfo)
        assert result["name"] == "Test"
        assert result["era"] == "modern"

    @pytest.mark.asyncio
    async def test_generate_with_retry_eventually_fails(self):
        class FailingProvider(LLMProvider):
            async def generate(self, system, user, schema):
                return await self.generate_with_retry(system, user, schema)

            async def chat(self, messages):
                return "not json at all"

        fp = FailingProvider()
        from app.services.llm.base import LLMGenerationError
        with pytest.raises(LLMGenerationError):
            await fp.generate_with_retry("system", "user", WorldInfo, max_retries=1)


class TestStoryBibleService:
    @pytest.mark.asyncio
    async def test_generate_story_bible_with_mock_llm(self):
        request = StoryBibleRequest(
            concept="Một thiếu gia ẩn thân trong thành phố hiện đại",
            style=Style.TWO_D_CHINESE_DONGHUA,
            target_episodes=1,
            language="vietnamese",
        )

        expected_world = {
            "name": "Cultivation City",
            "era": "modern",
            "location": "Neon City",
            "society": "Hidden cultivators among normal society",
            "atmosphere": "Mysterious and dramatic",
            "rules": ["Cultivators must hide their powers"],
            "factions": ["Ancient clan", "Modern government"],
        }
        expected_chars = {
            "characters": [
                {"name": "Lâm Hàn", "role": "main_protagonist", "appearance": "Black hair",
                 "personality": "Stoic", "backstory": "Heir of fallen clan",
                 "age": 22, "gender": "male", "power_level": "peak",
                 "relationships": [], "visual_cues": [], "style_tokens": []}
            ]
        }
        expected_eps = {
            "episodes": [
                {"episode_number": 1, "title": "The Awakening",
                 "summary": "Hero appears", "key_events": ["Event 1"],
                 "character_focus": ["Lâm Hàn"], "cliffhanger": None}
            ]
        }
        expected_scenes = {
            "scenes": [
                {"episode_number": 1, "scene_order": 1, "title": "Rainy Rooftop",
                 "description": "Hero stands in rain",
                 "characters_present": ["Lâm Hàn"], "location": "Rooftop",
                 "duration_seconds": 10.0, "emotional_beat": "Mysterious"}
            ]
        }

        service = StoryBibleService()
        service.llm = AsyncMock(spec=LLMProvider)

        async def fake_generate(system, user, schema):
            if schema.__name__ == "WorldInfo":
                return expected_world
            elif schema.__name__ == "CharacterList":
                return expected_chars
            elif schema.__name__ == "EpisodeList":
                return expected_eps
            elif schema.__name__ == "SceneList":
                return expected_scenes
            return {}

        service.llm.generate = fake_generate

        bible = await service.generate_story_bible(request)

        assert bible.world.name == "Cultivation City"
        assert len(bible.characters) == 1
        assert bible.characters[0]["name"] == "Lâm Hàn"
        assert len(bible.episodes) == 1
        assert bible.episodes[0].title == "The Awakening"
        assert len(bible.scene_breakdowns) == 1
        assert bible.scene_breakdowns[0].title == "Rainy Rooftop"
