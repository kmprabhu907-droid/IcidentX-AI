"""
INCIDENTX AI - Incident Repository
"""

from typing import List, Optional, Tuple
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.incident import Incident
from backend.app.repositories.base import BaseRepository


class IncidentRepository(BaseRepository[Incident]):
    def __init__(self, session: AsyncSession):
        super().__init__(Incident, session)

    async def list_incidents(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> Tuple[List[Incident], int]:
        filters = []
        if status:
            filters.append(Incident.status == status)
        if severity:
            filters.append(Incident.severity == severity)

        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=desc(Incident.detected_at),
        )
