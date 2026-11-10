"""
INCIDENTX AI - Audit Log Repository
"""

from typing import List, Optional, Tuple
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.audit import AuditLog
from backend.app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(AuditLog, session)

    async def list_audit_logs(
        self,
        page: int = 1,
        page_size: int = 50,
        incident_id: Optional[str] = None,
        actor_type: Optional[str] = None,
    ) -> Tuple[List[AuditLog], int]:
        filters = []
        if incident_id:
            filters.append(AuditLog.incident_id == incident_id)
        if actor_type:
            filters.append(AuditLog.actor_type == actor_type)

        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=desc(AuditLog.created_at),
        )
