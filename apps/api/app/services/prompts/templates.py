SYSTEM_PROMPT = """You are a professional donghua (Chinese animation) story writer specializing in urban xianxia and cultivation genres. You produce structured JSON output for animation production pipelines.

Rules:
1. Write all story content in {language}.
2. Output ONLY valid JSON, no markdown, no explanation.
3. Follow the requested schema exactly.
4. Be specific and visual — every description must be suitable for AI image generation.
5. Keep character visual descriptions detailed (hair, eyes, outfit, aura, distinguishing features).
6. Each scene should be 8-15 seconds of screen time.<｜end▁of▁thinking｜>Scene durations should sum to {target_duration_seconds}s total for the episode.
7. Stay consistent with the chosen style: {style}.
"""

WORLD_BUILDER_PROMPT = """Based on this story concept (in Vietnamese):
{concept}

Generate a complete world bible for a {style} donghua animation.

Output JSON with these fields:
- name: world name
- era: time period (hiện đại, cổ đại, hỗn hợp, etc.)
- location: main setting (city, region, specific landmarks)
- society: social structure description
- atmosphere: overall mood and atmosphere
- rules: list of world rules / limitations
- factions: list of factions and their descriptions

Make the world vivid, specific, and visually distinct for animation production."""

CHARACTER_SHEET_PROMPT = """Based on this world bible:
{world_summary}

Generate {character_count} character sheets for the main cast of this {style} donghua.

Output a JSON object with a "characters" array. Each character has:
- name
- role (main_protagonist, main_antagonist, supporting)
- appearance: detailed visual description suitable for AI image generation
- personality: personality traits and behavior
- backstory: brief origin story
- age
- gender
- power_level: cultivation level or power tier
- relationships: list of relationships to other characters
- visual_cues: list of visual signature elements (clothing, accessories, aura)
- style_tokens: list of keywords for AI image generation consistency

Make each character visually distinct with specific details for animation."""

EPISODE_OUTLINE_PROMPT = """Based on this world bible and characters, generate {episode_count} episode outlines.

World: {world_summary}
Characters: {character_summary}

Each episode should be approximately {episode_duration_minutes} minutes of animation.

Output a JSON object with an "episodes" array. Each episode has:
- episode_number
- title
- summary: brief plot summary
- key_events: list of key story events in order
- character_focus: list of character names focused in this episode
- cliffhanger: what happens at the end (or null)"""

SCENE_BREAKDOWN_PROMPT = """Break down Episode {episode_number}: "{episode_title}" into individual animation scenes.

Episode summary: {episode_summary}

Each scene should be 8-15 seconds. Total episode duration: ~{episode_duration_seconds}s.

Output a JSON object with a "scenes" array. Each scene has:
- episode_number
- scene_order
- title
- description: visual + action description suitable for animation storyboarding
- characters_present: list of character names in this scene
- location: where the scene takes place
- duration_seconds: 8-15
- emotional_beat: the emotional core of this scene"""
