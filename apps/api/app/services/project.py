from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.project import ProjectCreate, ProjectRead, ProjectUpdate

from app.exceptions import NotFoundException
from app.models.project import ProjectModel
from app.services.storage import StorageManager


class ProjectService:
    def __init__(self, db: AsyncSession, storage: StorageManager):
        self.db = db
        self.storage = storage

    async def create_project(self, data: ProjectCreate) -> ProjectRead:
        project = ProjectModel(**data.model_dump())
        self.db.add(project)
        await self.db.flush()
        self.storage.ensure_project_dirs(project.id)
        await self.db.commit()
        await self.db.refresh(project)
        return ProjectRead.model_validate(project)

    async def get_project(self, project_id: UUID) -> ProjectRead:
        project = await self._get_or_404(project_id)
        return ProjectRead.model_validate(project)

    async def list_projects(self) -> list[ProjectRead]:
        result = await self.db.execute(select(ProjectModel).order_by(ProjectModel.created_at.desc()))
        projects = result.scalars().all()
        return [ProjectRead.model_validate(p) for p in projects]

    async def update_project(self, project_id: UUID, data: ProjectUpdate) -> ProjectRead:
        project = await self._get_or_404(project_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(project, key, value)
        await self.db.commit()
        await self.db.refresh(project)
        return ProjectRead.model_validate(project)

    async def delete_project(self, project_id: UUID) -> None:
        project = await self._get_or_404(project_id)
        await self.db.delete(project)
        await self.db.commit()

    async def delete_all_projects(self) -> None:
        result = await self.db.execute(select(ProjectModel))
        projects = result.scalars().all()
        for project in projects:
            await self.db.delete(project)
        await self.db.commit()

    async def _get_or_404(self, project_id: UUID) -> ProjectModel:
        result = await self.db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise NotFoundException(f"Project {project_id} not found")
        return project
