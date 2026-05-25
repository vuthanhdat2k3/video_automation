from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.character import CharacterDNA, CharacterRead, CharacterUpdate

from app.exceptions import NotFoundException
from app.models.character import CharacterModel


class CharacterService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_project(self, project_id: UUID) -> list[CharacterRead]:
        result = await self.db.execute(
            select(CharacterModel)
            .where(CharacterModel.project_id == project_id)
            .order_by(CharacterModel.name)
        )
        return [CharacterRead.model_validate(c) for c in result.scalars().all()]

    async def create(self, project_id: UUID, data) -> CharacterRead:
        dna = data.character_dna or CharacterDNA()
        character = CharacterModel(
            project_id=project_id,
            name=data.name,
            role=data.role,
            character_json=dna.model_dump(),
        )
        self.db.add(character)
        await self.db.commit()
        await self.db.refresh(character)
        return CharacterRead.model_validate(character)

    async def get(self, character_id: UUID) -> CharacterRead:
        character = await self._get_or_404(character_id)
        return CharacterRead.model_validate(character)

    async def update(self, character_id: UUID, data: CharacterUpdate) -> CharacterRead:
        character = await self._get_or_404(character_id)
        if data.name is not None:
            character.name = data.name
        if data.role is not None:
            character.role = data.role
        if data.reference_asset_id is not None:
            character.reference_asset_id = data.reference_asset_id
        if data.character_dna is not None:
            # Merge DNA into existing character_json
            existing = dict(character.character_json or {})
            existing.update(data.character_dna.model_dump(exclude_unset=True))
            character.character_json = existing
        await self.db.commit()
        await self.db.refresh(character)
        return CharacterRead.model_validate(character)

    async def delete(self, character_id: UUID) -> None:
        character = await self._get_or_404(character_id)
        await self.db.delete(character)
        await self.db.commit()

    async def _get_or_404(self, character_id: UUID) -> CharacterModel:
        result = await self.db.execute(
            select(CharacterModel).where(CharacterModel.id == character_id)
        )
        character = result.scalar_one_or_none()
        if not character:
            raise NotFoundException(f"Character {character_id} not found")
        return character
