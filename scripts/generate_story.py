"""
CLI tool for Story Bible generation.

Usage:
    python scripts/generate_story.py \\
        --project-id <uuid> \\
        --concept "Đô thị tu tiên, thiếu gia ẩn thân" \\
        --style 2d_chinese_donghua \\
        --language vietnamese \\
        --save

Requires: PostgreSQL running with the project, or --dry-run to skip DB.
Requires: Ollama (or configured LLM provider) running.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps/api"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages/shared"))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ai_2d_shared.enums import Style
from ai_2d_shared.story import StoryBibleRequest
from app.config import settings
from app.services.story import StoryBibleService


async def main():
    parser = argparse.ArgumentParser(description="Generate Story Bible from concept")
    parser.add_argument("--project-id", type=str, required=True, help="Project UUID")
    parser.add_argument("--concept", type=str, required=True, help="Story concept in Vietnamese")
    parser.add_argument("--style", type=str, default="2d_chinese_donghua", help="Animation style")
    parser.add_argument("--episodes", type=int, default=1, help="Number of episodes")
    parser.add_argument("--duration", type=float, default=1.5, help="Episode duration in minutes")
    parser.add_argument("--language", type=str, default="vietnamese", help="Output language")
    parser.add_argument("--save", action="store_true", help="Save to project DB")
    parser.add_argument("--dry-run", action="store_true", help="Skip DB, print JSON only")
    parser.add_argument("--output", type=str, help="Save output JSON to file")
    args = parser.parse_args()

    style_map = {
        "2d_chinese_donghua": Style.TWO_D_CHINESE_DONGHUA,
        "2d_anime": Style.TWO_D_ANIME,
        "2d_western": Style.TWO_D_WESTERN,
        "2d_pixar": Style.TWO_D_PIXAR,
    }
    style = style_map.get(args.style, Style.TWO_D_CHINESE_DONGHUA)

    request = StoryBibleRequest(
        concept=args.concept,
        style=style,
        target_episodes=args.episodes,
        episode_duration_minutes=args.duration,
        language=args.language,
    )

    if args.dry_run:
        print("=== DRY RUN — not connecting to DB ===\n")
        service = StoryBibleService(db=None)
        bible = await service.generate_story_bible(request)
        print(json.dumps(bible.model_dump(), ensure_ascii=False, indent=2))
        return
    else:
        engine = create_async_engine(settings.database_url, echo=False)
        async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session_factory() as db:
            service = StoryBibleService(db=db)
            bible = await service.generate_story_bible(request)
            await service.save_bible_to_project(UUID(args.project_id), bible)
            await db.commit()
            print(f"Story Bible saved to project {args.project_id}")
            print(json.dumps(bible.model_dump(), ensure_ascii=False, indent=2))
        await engine.dispose()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(bible.model_dump(), f, ensure_ascii=False, indent=2)
        print(f"Output written to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
