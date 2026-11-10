"""
INCIDENTX AI - Investigation Repositories
"""

from typing import List, Tuple
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.investigation import AgentExecution, Evidence, RootCauseHypothesis
from backend.app.repositories.base import BaseRepository


class EvidenceRepository(BaseRepository[Evidence]):
    def __init__(self, session: AsyncSession):
        super().__init__(Evidence, session)

    async def list_by_incident(
        self, incident_id: str, page: int = 1, page_size: int = 50
    ) -> Tuple[List[Evidence], int]:
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=[Evidence.incident_id == incident_id],
            order_by=desc(Evidence.observed_at),
        )


class HypothesisRepository(BaseRepository[RootCauseHypothesis]):
    def __init__(self, session: AsyncSession):
        super().__init__(RootCauseHypothesis, session)

    async def list_by_incident(
        self, incident_id: str, page: int = 1, page_size: int = 50
    ) -> Tuple[List[RootCauseHypothesis], int]:
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=[RootCauseHypothesis.incident_id == incident_id],
            order_by=desc(RootCauseHypothesis.probability_score),
        )


class AgentExecutionRepository(BaseRepository[AgentExecution]):
    def __init__(self, session: AsyncSession):
        super().__init__(AgentExecution, session)

    async def list_by_incident(
        self, incident_id: str, page: int = 1, page_size: int = 50
    ) -> Tuple[List[AgentExecution], int]:
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=[AgentExecution.incident_id == incident_id],
            order_by=desc(AgentExecution.created_at),
        )
