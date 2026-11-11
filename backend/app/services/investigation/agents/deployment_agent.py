"""
INCIDENTX AI - Deployment & Configuration Change Analysis Agent
Inspects recent service releases, Git commits, and configuration updates for temporal correlation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.investigation.agents.base import BaseInvestigationAgent
from backend.app.services.investigation.schemas import (
    DeploymentAnalysisResult,
    DeploymentRecord,
)
from backend.app.services.observability.demo_mesh import demo_mesh


class DeploymentChangeAgent(BaseInvestigationAgent):
    def __init__(self):
        super().__init__(
            name="DeploymentChangeAgent",
            role="deployment",
            execution_phase="DEPLOYMENT_ANALYSIS",
            timeout_seconds=10.0,
        )

    async def execute(
        self,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        impacted_services = state.get("incident", {}).get("impact_scope", [])
        now = datetime.now(timezone.utc).isoformat()

        deployments: List[DeploymentRecord] = []
        is_regression_fault = "deployment_regression" in demo_mesh.active_faults

        for svc_name in impacted_services:
            svc_def = demo_mesh.SERVICE_DEFINITIONS.get(svc_name, {})
            version = "v2.1.0-buggy" if (is_regression_fault and svc_name == "order-service") else svc_def.get("version", "v1.0.0")
            is_suspicious = is_regression_fault and svc_name == "order-service"

            deployments.append(DeploymentRecord(
                service_name=svc_name,
                version=version,
                deployed_at=now,
                commit_sha="a7b4f2c" if is_suspicious else "3e89da1",
                change_type="RELEASE",
                is_suspicious=is_suspicious,
            ))

        if is_regression_fault:
            correlation_score = 0.95
            summary = "Direct temporal correlation: Release v2.1.0-buggy was deployed immediately prior to error surge on order-service."
        else:
            correlation_score = 0.15
            summary = "No recent unexpected deployments detected. Services operating on stable tagged releases."

        res = DeploymentAnalysisResult(
            deployments_detected=deployments,
            config_changes_detected=["DB_POOL_MAX=50", "GATEWAY_TIMEOUT=2000ms"],
            temporal_correlation_score=correlation_score,
            deployment_impact_summary=summary,
        )

        state["deployment"] = res.model_dump()
        return state
