from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.shot import CameraConfig, MotionConfig, AudioConfig, ShotCreate, ShotRead, ShotUpdate
from ai_2d_shared.enums import ShotType

from app.exceptions import NotFoundException
from app.models.shot import ShotModel


class ShotService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_scene(self, scene_id: UUID) -> list[ShotRead]:
        result = await self.db.execute(
            select(ShotModel)
            .where(ShotModel.scene_id == scene_id)
            .order_by(ShotModel.order_index)
        )
        return [self._to_read(s) for s in result.scalars().all()]

    async def create(self, scene_id: UUID, data: ShotCreate) -> ShotRead:
        last = await self.db.execute(
            select(ShotModel)
            .where(ShotModel.scene_id == scene_id)
            .order_by(ShotModel.order_index.desc())
            .limit(1)
        )
        last_shot = last.scalar_one_or_none()
        next_order = (last_shot.order_index + 1) if last_shot else 0

        shot = ShotModel(
            scene_id=scene_id,
            order_index=data.order_index if data.order_index != 0 else next_order,
            duration_seconds=data.duration_seconds,
            description=data.description,
            shot_type=data.shot_type.value if isinstance(data.shot_type, ShotType) else data.shot_type,
            camera_json=data.camera.model_dump() if data.camera else {},
            motion_json=data.motion.model_dump() if data.motion else {},
            audio_json=data.audio.model_dump() if data.audio else {},
        )
        self.db.add(shot)
        await self.db.flush()
        await self.db.refresh(shot)
        return self._to_read(shot)

    async def get(self, shot_id: UUID) -> ShotRead:
        shot = await self._get_or_404(shot_id)
        return self._to_read(shot)

    async def update(self, shot_id: UUID, data: ShotUpdate) -> ShotRead:
        shot = await self._get_or_404(shot_id)
        if data.order_index is not None:
            shot.order_index = data.order_index
        if data.duration_seconds is not None:
            shot.duration_seconds = data.duration_seconds
        if data.description is not None:
            shot.description = data.description
        if data.shot_type is not None:
            shot.shot_type = data.shot_type.value if isinstance(data.shot_type, ShotType) else data.shot_type
        if data.camera is not None:
            existing = dict(shot.camera_json or {})
            existing.update(data.camera.model_dump(exclude_unset=True))
            shot.camera_json = existing
        if data.motion is not None:
            existing = dict(shot.motion_json or {})
            existing.update(data.motion.model_dump(exclude_unset=True))
            shot.motion_json = existing
        if data.audio is not None:
            existing = dict(shot.audio_json or {})
            existing.update(data.audio.model_dump(exclude_unset=True))
            shot.audio_json = existing
        await self.db.commit()
        await self.db.refresh(shot)
        return self._to_read(shot)

    async def delete(self, shot_id: UUID) -> None:
        shot = await self._get_or_404(shot_id)
        await self.db.delete(shot)
        await self.db.commit()

    async def reorder(self, scene_id: UUID, shot_ids: list[UUID]) -> list[ShotRead]:
        shots = []
        for idx, sid in enumerate(shot_ids):
            result = await self.db.execute(
                select(ShotModel).where(ShotModel.id == sid, ShotModel.scene_id == scene_id)
            )
            s = result.scalar_one_or_none()
            if s:
                s.order_index = idx
                shots.append(s)
        await self.db.commit()
        for s in shots:
            await self.db.refresh(s)
        return [self._to_read(s) for s in shots]

    async def _get_or_404(self, shot_id: UUID) -> ShotModel:
        result = await self.db.execute(select(ShotModel).where(ShotModel.id == shot_id))
        shot = result.scalar_one_or_none()
        if not shot:
            raise NotFoundException(f"Shot {shot_id} not found")
        return shot

    def _to_read(self, shot: ShotModel) -> ShotRead:
        return ShotRead(
            id=shot.id,
            scene_id=shot.scene_id,
            order_index=shot.order_index,
            duration_seconds=shot.duration_seconds,
            description=shot.description,
            shot_type=ShotType(shot.shot_type) if shot.shot_type else ShotType.DIALOGUE,
            camera=CameraConfig(**shot.camera_json) if shot.camera_json else CameraConfig(),
            motion=MotionConfig(**shot.motion_json) if shot.motion_json else MotionConfig(),
            audio=AudioConfig(**shot.audio_json) if shot.audio_json else AudioConfig(),
            status=shot.status,
            created_at=shot.created_at,
            updated_at=shot.updated_at,
        )
