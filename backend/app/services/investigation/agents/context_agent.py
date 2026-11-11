"""
INCIDENTX AI - Context Gathering Agent
Inspects topological dependencies, service tiers, languages, and upstream/downstream boundaries.
"""

from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.service import Service, ServiceDependency
from backend.app.services.investigation.agents.base import BaseInvestigationAgent
from backend.app.services.investigation.schemas import ContextResult, ServiceContext


class ContextGatheringAgent(BaseInvestigationAgent):
    def __init__(self):
        super().__init__(
            name="ContextGatheringAgent",
            role="context",
            execution_phase="CONTEXT",
            timeout_seconds=10.0,
        )

    async def execute(
        self,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        impacted_names = state.get("incident", {}).get("impact_scope", [])

        # Fetch services from database
        svc_stmt = select(Service)
        svc_res = await session.execute(svc_stmt)
        all_services = list(svc_res.scalars().all())

        svc_name_map = {s.name: s for s in all_services}
        svc_id_map = {s.id: s for s in all_services}
        target_services = [svc_name_map[n] for n in impacted_names if n in svc_name_map]
        if not target_services:
            target_services = all_services[:4]

        # Fetch all topology dependencies
        dep_stmt = select(ServiceDependency)
        dep_res = await session.execute(dep_stmt)
        all_deps = list(dep_res.scalars().all())

        services_metadata: Dict[str, ServiceContext] = {}
        upstream_callers: List[str] = []
        downstream_callees: List[str] = []

        target_ids = {s.id for s in target_services}

        for s in target_services:
            # Outbound dependencies (what this service calls)
            outbound = [
                svc_id_map[d.target_service_id].name
                for d in all_deps
                if d.source_service_id == s.id and d.target_service_id in svc_id_map
            ]
            services_metadata[s.name] = ServiceContext(
                service_id=s.id,
                name=s.name,
                tier=s.tier,
                service_type=s.service_type,
                language=s.language,
                health_status=s.health_status,
                dependencies=outbound,
            )

        for d in all_deps:
            src_name = next((s.name for s in all_services if s.id == d.source_service_id), None)
            tgt_name = next((s.name for s in all_services if s.id == d.target_service_id), None)
            if d.source_service_id in target_ids and tgt_name:
                downstream_callees.append(tgt_name)
            if d.target_service_id in target_ids and src_name:
                upstream_callers.append(src_name)

        context_res = ContextResult(
            services_metadata=services_metadata,
            topology_depth=2,
            upstream_callers=list(set(upstream_callers)),
            downstream_callees=list(set(downstream_callees)),
            critical_path=["api-gateway", "order-service", "payment-service", "postgres-db"],
        )

        state["context"] = context_res.model_dump()
        return state
