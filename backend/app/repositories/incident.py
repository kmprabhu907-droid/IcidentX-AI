"""
INCIDENTX AI - Incident Repository
"""

from typing import List, Optional, Tuple
from sqlalchemy import desc, or_
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
        environment: Optional[str] = None,
        owner_id: Optional[str] = None,
        priority: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Incident], int]:
        filters = []
        if status:
            filters.append(Incident.status == status)
        if severity:
            filters.append(Incident.severity == severity)
        if environment:
            filters.append(Incident.environment == environment)
        if owner_id:
            filters.append(Incident.owner_id == owner_id)
        if priority:
            filters.append(Incident.priority == priority)
        if search:
            term = f"%{search}%"
            filters.append(
                or_(
                    Incident.title.ilike(term),
                    Incident.summary.ilike(term),
                    Incident.impact_scope.ilike(term),
                )
            )

        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=desc(Incident.detected_at),
        )
