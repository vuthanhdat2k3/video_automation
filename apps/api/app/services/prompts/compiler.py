from . import templates


class PromptCompiler:
    def compile(self, template_name: str, **kwargs) -> str:
        template = getattr(templates, template_name, None)
        if template is None:
            raise ValueError(f"Unknown template: {template_name}")
        return template.format(**kwargs)

    def compile_system(self, language: str, target_duration_seconds: float, style: str) -> str:
        return self.compile(
            "SYSTEM_PROMPT",
            language=language,
            target_duration_seconds=target_duration_seconds,
            style=style,
        )

    def compile_world_builder(self, concept: str, style: str) -> str:
        return self.compile("WORLD_BUILDER_PROMPT", concept=concept, style=style)

    def compile_character_sheet(self, world_summary: str, style: str, character_count: int = 4) -> str:
        return self.compile(
            "CHARACTER_SHEET_PROMPT",
            world_summary=world_summary,
            style=style,
            character_count=character_count,
        )

    def compile_episodes(
        self, world_summary: str, character_summary: str,
        episode_count: int, episode_duration_minutes: float,
    ) -> str:
        return self.compile(
            "EPISODE_OUTLINE_PROMPT",
            world_summary=world_summary,
            character_summary=character_summary,
            episode_count=episode_count,
            episode_duration_minutes=episode_duration_minutes,
        )

    def compile_scene_breakdown(
        self, episode_number: int, episode_title: str,
        episode_summary: str, episode_duration_seconds: float,
    ) -> str:
        return self.compile(
            "SCENE_BREAKDOWN_PROMPT",
            episode_number=episode_number,
            episode_title=episode_title,
            episode_summary=episode_summary,
            episode_duration_seconds=episode_duration_seconds,
        )
