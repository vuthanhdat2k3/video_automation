import pytest

from app.services.prompts.compiler import PromptCompiler


@pytest.fixture
def compiler():
    return PromptCompiler()


class TestPromptCompiler:
    def test_compile_system(self, compiler):
        result = compiler.compile_system(language="vietnamese", target_duration_seconds=60, style="2d_chinese_donghua")
        assert "vietnamese" in result
        assert "2d_chinese_donghua" in result
        assert "donghua" in result.lower()

    def test_compile_world_builder(self, compiler):
        result = compiler.compile_world_builder(
            concept="Đô thị tu tiên, thiếu gia ẩn thân",
            style="2d_chinese_donghua",
        )
        assert "Đô thị tu tiên" in result
        assert "2d_chinese_donghua" in result

    def test_compile_character_sheet(self, compiler):
        result = compiler.compile_character_sheet(
            world_summary='{"name": "Cultivation City"}',
            style="2d_chinese_donghua",
            character_count=3,
        )
        assert "3" in result
        assert "Cultivation City" in result

    def test_compile_episodes(self, compiler):
        result = compiler.compile_episodes(
            world_summary="Modern cultivation world",
            character_summary="Hero and villain",
            episode_count=2,
            episode_duration_minutes=2.0,
        )
        assert "2" in result
        assert "2.0" in result

    def test_compile_scene_breakdown(self, compiler):
        result = compiler.compile_scene_breakdown(
            episode_number=1,
            episode_title="The Awakening",
            episode_summary="Hero discovers powers",
            episode_duration_seconds=120.0,
        )
        assert "1" in result
        assert "The Awakening" in result
        assert "120.0" in result

    def test_unknown_template_raises(self, compiler):
        with pytest.raises(ValueError, match="Unknown template"):
            compiler.compile("NONEXISTENT_TEMPLATE")
