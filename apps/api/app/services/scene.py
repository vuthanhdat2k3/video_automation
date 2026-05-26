from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.scene import ContinuityState, SceneCreate, SceneRead, SceneUpdate

from app.exceptions import NotFoundException
from app.models.scene import SceneModel


class SceneService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_project(self, project_id: UUID, episode: int | None = None) -> list[SceneRead]:
        query = (
            select(SceneModel)
            .where(SceneModel.project_id == project_id)
            .order_by(SceneModel.order_index)
        )
        if episode is not None:
            query = query.where(SceneModel.episode_number == episode)
        result = await self.db.execute(query)
        return [self._to_read(s) for s in result.scalars().all()]

    async def create(self, project_id: UUID, data: SceneCreate) -> SceneRead:
        last = await self.db.execute(
            select(SceneModel)
            .where(SceneModel.project_id == project_id)
            .order_by(SceneModel.order_index.desc())
            .limit(1)
        )
        last_scene = last.scalar_one_or_none()
        next_order = (last_scene.order_index + 1) if last_scene else 0

        scene = SceneModel(
            project_id=project_id,
            title=data.title,
            description=data.description,
            duration_seconds=data.duration_seconds,
            order_index=next_order,
            continuity_json=data.continuity.model_dump() if data.continuity else {},
        )
        self.db.add(scene)
        await self.db.flush()
        await self.db.refresh(scene)
        return self._to_read(scene)

    async def get(self, scene_id: UUID) -> SceneRead:
        scene = await self._get_or_404(scene_id)
        return self._to_read(scene)

    async def update(self, scene_id: UUID, data: SceneUpdate) -> SceneRead:
        scene = await self._get_or_404(scene_id)
        if data.title is not None:
            scene.title = data.title
        if data.description is not None:
            scene.description = data.description
        if data.duration_seconds is not None:
            scene.duration_seconds = data.duration_seconds
        if data.order_index is not None:
            scene.order_index = data.order_index
        if data.continuity is not None:
            existing = dict(scene.continuity_json or {})
            existing.update(data.continuity.model_dump(exclude_unset=True))
            scene.continuity_json = existing
        await self.db.commit()
        await self.db.refresh(scene)
        return self._to_read(scene)

    async def delete(self, scene_id: UUID) -> None:
        scene = await self._get_or_404(scene_id)
        await self.db.delete(scene)
        await self.db.commit()

    async def reorder(self, project_id: UUID, scene_ids: list[UUID]) -> list[SceneRead]:
        scenes = []
        for idx, sid in enumerate(scene_ids):
            result = await self.db.execute(
                select(SceneModel).where(
                    SceneModel.id == sid, SceneModel.project_id == project_id
                )
            )
            s = result.scalar_one_or_none()
            if s:
                s.order_index = idx
                scenes.append(s)
        await self.db.commit()
        for s in scenes:
            await self.db.refresh(s)
        return [self._to_read(s) for s in scenes]

    async def materialize_from_bible(self, scene_breakdowns: list, char_map: dict[str, UUID]) -> tuple[int, int]:
        """Create SceneModel + default ShotModel records from story bible breakdowns."""
        scenes_created = 0
        for sb in scene_breakdowns:
            char_uuids = [char_map.get(name) for name in getattr(sb, "characters_present", []) if name in char_map]
            continuity = ContinuityState(
                characters_present=char_uuids,
                location=getattr(sb, "location", None),
                mood=getattr(sb, "emotional_beat", None),
            )
            scene = SceneModel(
                project_id=UUID(int=0),  # placeholder, set by caller
                title=sb.title,
                description=sb.description,
                duration_seconds=sb.duration_seconds,
                order_index=sb.scene_order,
                episode_number=sb.episode_number,
                continuity_json=continuity.model_dump(),
            )
            self.db.add(scene)
            scenes_created += 1
        return scenes_created, scenes_created  # one shot per scene for now

    async def _get_or_404(self, scene_id: UUID) -> SceneModel:
        result = await self.db.execute(select(SceneModel).where(SceneModel.id == scene_id))
        scene = result.scalar_one_or_none()
        if not scene:
            raise NotFoundException(f"Scene {scene_id} not found")
        return scene

    def _to_read(self, scene: SceneModel) -> SceneRead:
        return SceneRead(
            id=scene.id,
            project_id=scene.project_id,
            title=scene.title,
            description=scene.description,
            duration_seconds=scene.duration_seconds,
            order_index=scene.order_index,
            continuity=ContinuityState(**scene.continuity_json) if scene.continuity_json else ContinuityState(),
            created_at=scene.created_at,
            updated_at=scene.updated_at,
        )
