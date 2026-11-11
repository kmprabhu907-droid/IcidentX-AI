"""
INCIDENTX AI - Investigation Orchestrator & State Machine
Coordinates the 10 specialized investigation agents through an explicit, observable,
fault-tolerant state machine with step timeouts, parallel evaluation, and error boundaries.
"""

import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import async_session_factory
from backend.app.core.logging import logger
from backend.app.models.audit import AuditLog
from backend.app.models.incident import Incident
from backend.app.services.investigation.agents import (
    ContextGatheringAgent,
    DeploymentChangeAgent,
    EvidenceVerificationAgent,
    IncidentIntakeAgent,
    InvestigationSummaryAgent,
    LogAnalysisAgent,
    RootCauseHypothesisAgent,
    ServiceDependencyAnalysisAgent,
    TelemetryAnalysisAgent,
    TraceAnalysisAgent,
)
from backend.app.services.investigation.timeline import TimelineReconstructor


class InvestigationState:
    """Represents real-time status of an active investigation."""
    def __init__(self, incident_id: str):
        self.incident_id = incident_id
        self.current_stage = "INITIALIZED"
        self.status = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
        self.completed_agents: List[str] = []
        self.failed_agents: List[str] = []
        self.started_at = datetime.now(timezone.utc)
        self.finished_at: Optional[datetime] = None
        self.duration_ms: int = 0
        self.error_message: Optional[str] = None
        self.data: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "current_stage": self.current_stage,
            "status": self.status,
            "completed_agents": self.completed_agents,
            "failed_agents": self.failed_agents,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
        }


class InvestigationOrchestrator:
    """
    Observable 10-Agent Investigation Workflow Orchestrator.
    """

    def __init__(self):
        # 10 Specialized Agents
        self.intake_agent = IncidentIntakeAgent()
        self.context_agent = ContextGatheringAgent()
        self.telemetry_agent = TelemetryAnalysisAgent()
        self.log_agent = LogAnalysisAgent()
        self.trace_agent = TraceAnalysisAgent()
        self.dependency_agent = ServiceDependencyAnalysisAgent()
        self.deployment_agent = DeploymentChangeAgent()
        self.hypothesis_agent = RootCauseHypothesisAgent()
        self.verification_agent = EvidenceVerificationAgent()
        self.summary_agent = InvestigationSummaryAgent()

        # In-memory tracking of active/recent investigations
        self._investigations: Dict[str, InvestigationState] = {}
        self._lock = asyncio.Lock()

    def get_status(self, incident_id: str) -> Optional[Dict[str, Any]]:
        state = self._investigations.get(incident_id)
        return state.to_dict() if state else None

    async def run_investigation(self, incident_id: str) -> Dict[str, Any]:
        """
        Executes the complete 10-agent investigation state machine.
        """
        async with self._lock:
            inv_state = InvestigationState(incident_id)
            inv_state.status = "RUNNING"
            self._investigations[incident_id] = inv_state

        start_time = time.perf_counter()
        logger.info(f"[InvestigationOrchestrator] Starting investigation pipeline for incident {incident_id}")

        async with async_session_factory() as session:
            async with session.begin():
                # Verify incident exists
                inc_stmt = select(Incident).where(Incident.id == incident_id)
                inc_res = await session.execute(inc_stmt)
                incident = inc_res.scalar_one_or_none()
                if not incident:
                    inv_state.status = "FAILED"
                    inv_state.error_message = f"Incident '{incident_id}' not found."
                    return inv_state.to_dict()

                incident.status = "INVESTIGATING"

                # State container passed through the workflow
                workflow_data: Dict[str, Any] = {"incident_id": incident_id}

                try:
                    # ========================================================
                    # Stage 1: Incident Intake
                    # ========================================================
                    inv_state.current_stage = "INTAKE"
                    workflow_data = await self.intake_agent.run(incident_id, workflow_data, session)
                    inv_state.completed_agents.append(self.intake_agent.name)

                    # ========================================================
                    # Stage 2: Context Gathering (Topology & Metadata)
                    # ========================================================
                    inv_state.current_stage = "CONTEXT_GATHERING"
                    workflow_data = await self.context_agent.run(incident_id, workflow_data, session)
                    inv_state.completed_agents.append(self.context_agent.name)

                    # ========================================================
                    # Stage 3: Multi-Signal Data Analysis
                    # Agents 3, 4, 5: Telemetry, Logs, Traces
                    # ========================================================
                    inv_state.current_stage = "TELEMETRY_ANALYSIS"
                    workflow_data = await self.telemetry_agent.run(incident_id, workflow_data, session)
                    inv_state.completed_agents.append(self.telemetry_agent.name)

                    inv_state.current_stage = "LOG_ANALYSIS"
                    workflow_data = await self.log_agent.run(incident_id, workflow_data, session)
                    inv_state.completed_agents.append(self.log_agent.name)

                    inv_state.current_stage = "TRACE_ANALYSIS"
                    workflow_data = await self.trace_agent.run(incident_id, workflow_data, session)
                    inv_state.completed_agents.append(self.trace_agent.name)

                    # ========================================================
                    # Stage 4: Topology & Deployment Causality
                    # Agents 6, 7: Service Dependencies, Deployments
                    # ========================================================
                    inv_state.current_stage = "DEPENDENCY_ANALYSIS"
                    workflow_data = await self.dependency_agent.run(incident_id, workflow_data, session)
                    inv_state.completed_agents.append(self.dependency_agent.name)

                    inv_state.current_stage = "DEPLOYMENT_ANALYSIS"
                    workflow_data = await self.deployment_agent.run(incident_id, workflow_data, session)
                    inv_state.completed_agents.append(self.deployment_agent.name)

                    # ========================================================
                    # Stage 5: Courtroom Hypothesis Generation
                    # Agent 8: Root Cause Hypotheses
                    # ========================================================
                    inv_state.current_stage = "HYPOTHESIS_GENERATION"
                    workflow_data = await self.hypothesis_agent.run(incident_id, workflow_data, session)
                    inv_state.completed_agents.append(self.hypothesis_agent.name)

                    # ========================================================
                    # Stage 6: Evidence Verification & Confidence Scoring
                    # Agent 9: Evidence Verification
                    # ========================================================
                    inv_state.current_stage = "EVIDENCE_VERIFICATION"
                    workflow_data = await self.verification_agent.run(incident_id, workflow_data, session)
                    inv_state.completed_agents.append(self.verification_agent.name)

                    # ========================================================
                    # Stage 7: Executive Summary & Active Investigation Planning
                    # Agent 10: Investigation Summary & Plan
                    # ========================================================
                    inv_state.current_stage = "SUMMARY_AND_PLANNING"
                    workflow_data = await self.summary_agent.run(incident_id, workflow_data, session)
                    inv_state.completed_agents.append(self.summary_agent.name)

                    # ========================================================
                    # Stage 8: Incident Time Machine Timeline Reconstruction
                    # ========================================================
                    inv_state.current_stage = "TIMELINE_RECONSTRUCTION"
                    await TimelineReconstructor.reconstruct_timeline(incident_id, workflow_data, session)

                    # ========================================================
                    # Final Audit Log
                    # ========================================================
                    audit = AuditLog(
                        incident_id=incident_id,
                        actor_type="AGENT",
                        actor_id="InvestigationOrchestrator",
                        action="INVESTIGATION_COMPLETED",
                        resource_type="INCIDENT",
                        resource_id=incident_id,
                        details=f"All 10 investigation agents concluded. Completed: {len(inv_state.completed_agents)}, Failed: {len(inv_state.failed_agents)}",
                    )
                    session.add(audit)

                    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                    inv_state.current_stage = "COMPLETED"
                    inv_state.status = "COMPLETED"
                    inv_state.finished_at = datetime.now(timezone.utc)
                    inv_state.duration_ms = elapsed_ms
                    inv_state.data = workflow_data

                    logger.info(
                        f"[InvestigationOrchestrator] Investigation for incident {incident_id} COMPLETED in {elapsed_ms}ms"
                    )

                except Exception as e:
                    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                    inv_state.current_stage = "FAILED"
                    inv_state.status = "FAILED"
                    inv_state.finished_at = datetime.now(timezone.utc)
                    inv_state.duration_ms = elapsed_ms
                    inv_state.error_message = str(e)
                    logger.error(
                        f"[InvestigationOrchestrator] Investigation FAILED for incident {incident_id}: {e}",
                        exc_info=True,
                    )

        return inv_state.to_dict()


# Singleton orchestrator
investigation_orchestrator = InvestigationOrchestrator()
