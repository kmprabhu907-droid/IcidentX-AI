"""
INCIDENTX AI - Service & Dependency Repositories
"""

from typing import List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.service import Service, ServiceDependency
from backend.app.repositories.base import BaseRepository


class ServiceRepository(BaseRepository[Service]):
    def __init__(self, session: AsyncSession):
        super().__init__(Service, session)

    async def get_by_name(self, name: str) -> Optional[Service]:
        stmt = select(Service).where(Service.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class ServiceDependencyRepository(BaseRepository[ServiceDependency]):
    def __init__(self, session: AsyncSession):
        super().__init__(ServiceDependency, session)

    async def get_by_endpoints(self, source_id: str, target_id: str) -> Optional[ServiceDependency]:
        stmt = select(ServiceDependency).where(
            ServiceDependency.source_service_id == source_id,
            ServiceDependency.target_service_id == target_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_service(self, service_id: str) -> List[ServiceDependency]:
        stmt = select(ServiceDependency).where(
            (ServiceDependency.source_service_id == service_id)
            | (ServiceDependency.target_service_id == service_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
