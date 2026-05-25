"""
Seed script — creates the demo project "Đô Thị Tu Tiên: Thiếu Gia Ẩn Thân"
with character, scene, and shot using the service layer directly.

Usage: python scripts/seed_demo_project.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps/api"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages/shared"))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base
from app.models.character import CharacterModel
from app.models.project import ProjectModel
from app.models.scene import SceneModel
from app.models.shot import ShotModel
from app.services.storage import StorageManager


async def seed():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_factory() as db:
        storage = StorageManager(settings.storage_root)

        # 1. Project
        print("Creating project...")
        project = ProjectModel(
            name="Đô Thị Tu Tiên: Thiếu Gia Ẩn Thân",
            style="2d_chinese_donghua",
            aspect_ratio="9:16",
            description=(
                "Lâm Hàn, một thiếu gia bí ẩn sống ẩn dật giữa lòng thành phố. "
                "Sở hữu sức mạnh tu tiên cổ xưa, anh che giấu thân phận để bảo vệ "
                "những người xung quanh khỏi thế giới ngầm đầy nguy hiểm."
            ),
        )
        db.add(project)
        await db.flush()
        storage.ensure_project_dirs(project.id)
        print(f"  Project: {project.name} (id={project.id})")

        # 2. Character: Lâm Hàn
        print("Creating character...")
        character = CharacterModel(
            project_id=project.id,
            name="Lâm Hàn",
            role="Main Character / Thiếu gia ẩn thân",
            character_json={
                "age": 22,
                "gender": "male",
                "hair_style": "medium length, slightly messy",
                "hair_color": "dark black with subtle blue undertone",
                "eye_shape": "sharp, slightly narrowed",
                "eye_color": "deep amber",
                "face_shape": "angular jaw, high cheekbones",
                "skin_tone": "fair porcelain",
                "height": "178cm",
                "build": "lean athletic",
                "clothing_style": "modern casual — black hoodie, dark jeans, silver necklace",
                "distinctive_features": [
                    "faint glowing rune marks on left forearm when using powers",
                    "silver ring with jade stone on right hand",
                    "piercing gaze that shifts between cold and gentle",
                ],
                "personality_traits": [
                    "stoic and reserved on the surface",
                    "protective of innocents",
                    "reluctant hero burdened by power",
                    "shows dry humor around trusted friends",
                ],
            },
        )
        db.add(character)
        await db.flush()
        print(f"  Character: {character.name} (id={character.id})")

        # 3. Scene
        print("Creating scene...")
        scene = SceneModel(
            project_id=project.id,
            title="Main xuất hiện dưới mưa",
            description=(
                "Đêm mưa tầm tã. Lâm Hàn đứng trên sân thượng cao nhất thành phố, "
                "nhìn xuống khu phố cổ nơi bọn côn đồ quấy rối dân thường. "
                "Ánh sáng đèn neon phản chiếu qua những hạt mưa."
            ),
            duration_seconds=12.0,
            order_index=1,
            continuity_json={
                "characters_present": [],
                "active_props": ["neon_signs", "rain", "rooftop_ledge"],
                "lighting": "nocturnal neon rain",
                "mood": "melancholic yet intense",
                "time_of_day": "night",
                "weather": "heavy rain",
            },
        )
        db.add(scene)
        await db.flush()
        print(f"  Scene: {scene.title} (id={scene.id})")

        # 4. Shot
        print("Creating shot...")
        shot = ShotModel(
            scene_id=scene.id,
            order_index=1,
            duration_seconds=8.0,
            shot_type="cinematic_intro",
            description=(
                "Máy quay từ từ lia từ mặt đường đầy mưa lên sân thượng, "
                "bắt gặp bóng dáng Lâm Hàn đứng quay lưng. "
                "Tay phải anh nắm nhẹ, những vệt sáng xanh bắt đầu rực lên ở cánh tay trái. "
                "Anh bước một bước về phía trước và biến mất trong làn mưa."
            ),
            camera_json={
                "angle": "low",
                "framing": "wide",
                "movement": "crane up tilt",
                "lens": "35mm",
            },
            motion_json={
                "animation_style": "live2d",
                "easing": "ease_in_out",
                "fps": 24,
            },
            audio_json={
                "voice_profile": None,
                "background_music": "cinematic_ambient_dark",
                "sound_effects": ["heavy_rain", "thunder_distant", "footstep_on_metal"],
                "volume": 1.0,
            },
        )
        db.add(shot)
        await db.flush()
        print(f"  Shot: order={shot.order_index}, {shot.duration_seconds}s (id={shot.id})")

        await db.commit()

    await engine.dispose()

    # Summary
    print()
    print("=" * 60)
    print("Demo project seeded successfully!")
    print(f"  Project:   Đô Thị Tu Tiên: Thiếu Gia Ẩn Thân")
    print(f"  Character: Lâm Hàn")
    print(f"  Scene:     Main xuất hiện dưới mưa")
    print(f"  Shot:      8s cinematic_intro")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed())
