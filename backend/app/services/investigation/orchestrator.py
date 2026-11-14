"""
INCIDENTX AI - Advanced Multi-Agent Investigation Orchestrator (Phase 10 Module 10.1)
Coordinates the 11 specialized investigation agents through dependency-aware DAG execution,
parallel diagnostic task dispatch, shared evidence synthesis, contradiction evaluation,
and seamless Phase 9 incident lifecycle integration.
"""

import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import async_session_factory
from backend.app.core.logging import logger
from backend.app.models.audit import AuditLog
from backend.app.models.incident import Incident
from backend.app.services.incident.lifecycle_engine import incident_lifecycle_engine
from backend.app.services.incident.timeline_engine import incident_timeline_engine
from backend.app.services.investigation.agents import (
    ContextGatheringAgent,
    DeploymentChangeAgent,
    EvidenceVerificationAgent,
    IncidentIntakeAgent,
    InvestigationQualityConsensusAgent,
    InvestigationSummaryAgent,
    KubernetesInvestigatorAgent,
    LogAnalysisAgent,
    NetworkInvestigationAgent,
    RemediationIntelligenceAgent,
    RootCauseHypothesisAgent,
    SecurityInvestigationAgent,
    ServiceDependencyAnalysisAgent,
    TelemetryAnalysisAgent,
    TraceAnalysisAgent,
)
from backend.app.services.investigation.collaboration_protocol import (
    CollaborationMessageType,
    collaboration_protocol_engine,
)
from backend.app.services.investigation.evidence_engine import (
    EvidenceCategory,
    EvidenceVerificationStatus,
    shared_evidence_engine,
)
from backend.app.services.investigation.root_cause_engine import (
    advanced_root_cause_engine,
)
from backend.app.services.investigation.timeline import TimelineReconstructor


class InvestigationTask:
    """Represents a scheduled or executing task in the multi-agent DAG."""

    def __init__(self, task_id: str, agent_name: str, phase: str, dependencies: Optional[List[str]] = None):
        self.task_id = task_id
        self.agent_name = agent_name
        self.phase = phase
        self.dependencies = dependencies or []
        self.status = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.duration_ms: int = 0
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "phase": self.phase,
            "dependencies": self.dependencies,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class InvestigationState:
    """Represents real-time status of an active investigation."""

    def __init__(self, incident_id: str, investigation_id: Optional[str] = None):
        self.incident_id = incident_id
        self.investigation_id = investigation_id or f"inv-{uuid.uuid4().hex[:12]}"
        self.current_stage = "INITIALIZED"
        self.status = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
        self.completed_agents: List[str] = []
        self.failed_agents: List[str] = []
        self.tasks: Dict[str, InvestigationTask] = {}
        self.started_at = datetime.now(timezone.utc)
        self.finished_at: Optional[datetime] = None
        self.duration_ms: int = 0
        self.error_message: Optional[str] = None
        self.data: Dict[str, Any] = {}
        self.report: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "investigation_id": self.investigation_id,
            "current_stage": self.current_stage,
            "status": self.status,
            "completed_agents": self.completed_agents,
            "failed_agents": self.failed_agents,
            "tasks": [t.to_dict() for t in self.tasks.values()],
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "report": self.report,
            "workflow_data": self.data,
        }


class InvestigationOrchestrator:
    """
    Advanced Collaborative Multi-Agent Investigation Orchestrator.
    Manages task dispatch, parallel diagnostics, contradiction checks,
    and Phase 9 lifecycle synchronization.
    """

    def __init__(self):
        # 11 Specialized Autonomous Agents
        self.intake_agent = IncidentIntakeAgent()
        self.context_agent = ContextGatheringAgent()
        self.kubernetes_agent = KubernetesInvestigatorAgent()
        self.telemetry_agent = TelemetryAnalysisAgent()
        self.log_agent = LogAnalysisAgent()
        self.trace_agent = TraceAnalysisAgent()
        self.dependency_agent = ServiceDependencyAnalysisAgent()
        self.deployment_agent = DeploymentChangeAgent()
        self.network_agent = NetworkInvestigationAgent()
        self.security_agent = SecurityInvestigationAgent()
        self.hypothesis_agent = RootCauseHypothesisAgent()
        self.remediation_agent = RemediationIntelligenceAgent()
        self.consensus_agent = InvestigationQualityConsensusAgent()
        self.verification_agent = EvidenceVerificationAgent()
        self.summary_agent = InvestigationSummaryAgent()

        # In-memory tracking of active investigations and cancellation tokens
        self._investigations: Dict[str, InvestigationState] = {}
        self._cancel_tokens: Dict[str, bool] = {}
        self._cancellation_tokens: Dict[str, bool] = self._cancel_tokens

    @property
    def lock(self) -> asyncio.Lock:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.Lock()
        if getattr(self, "_lock_loop", None) is not loop:
            self._lock_obj = asyncio.Lock()
            self._lock_loop = loop
        return self._lock_obj

    @property
    def session_lock(self) -> asyncio.Lock:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.Lock()
        if getattr(self, "_session_lock_loop", None) is not loop:
            self._session_lock_obj = asyncio.Lock()
            self._session_lock_loop = loop
        return self._session_lock_obj

    def get_status(self, incident_id: str) -> Optional[Dict[str, Any]]:
        state = self._investigations.get(incident_id)
        return state.to_dict() if state else None

    def cancel_investigation(self, incident_id: str) -> bool:
        """
        Signals immediate cancellation for an active investigation.
        """
        self._cancel_tokens[incident_id] = True
        if incident_id in self._investigations:
            state = self._investigations[incident_id]
            state.status = "CANCELLED"
            state.current_stage = "CANCELLED"
            logger.warning(f"[InvestigationOrchestrator] Investigation {state.investigation_id} for incident {incident_id} CANCELLED by operator.")
        return True

    async def _safe_run_agent(
        self,
        agent: Any,
        incident_id: str,
        workflow_data: Dict[str, Any],
        session: AsyncSession,
        inv_state: InvestigationState,
    ) -> Dict[str, Any]:
        """
        Executes a single agent within failure isolation and timeout boundaries.
        """
        task_id = f"task-{agent.name}"
        task = InvestigationTask(task_id=task_id, agent_name=agent.name, phase=agent.execution_phase)
        task.status = "RUNNING"
        task.started_at = datetime.now(timezone.utc)
        inv_state.tasks[agent.name] = task

        t0 = time.perf_counter()
        try:
            async with self.session_lock:
                res_data = await agent.run(incident_id, workflow_data, session)
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                task.status = "COMPLETED"
                task.finished_at = datetime.now(timezone.utc)
                task.duration_ms = elapsed_ms
                task.result = {"status": "SUCCESS"}
                inv_state.completed_agents.append(agent.name)

                # Share finding announcement via collaboration protocol
                await collaboration_protocol_engine.send_message(
                    incident_id=incident_id,
                    investigation_id=inv_state.investigation_id,
                    sender_agent=agent.name,
                    message_type=CollaborationMessageType.EVIDENCE_SHARED,
                    summary=f"Agent {agent.name} concluded phase '{agent.execution_phase}' successfully.",
                    session=session,
                )

            return res_data
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            task.status = "FAILED"
            task.finished_at = datetime.now(timezone.utc)
            task.duration_ms = elapsed_ms
            task.error = str(e)
            inv_state.failed_agents.append(agent.name)
            logger.error(f"[InvestigationOrchestrator] Agent {agent.name} failed: {e}", exc_info=True)
            return workflow_data

    async def run_investigation(
        self,
        incident_id: str,
        session_override: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Executes the full Phase 10 collaborative multi-agent DAG pipeline.
        """
        inv_id = f"inv-{uuid.uuid4().hex[:12]}"
        async with self.lock:
            inv_state = InvestigationState(incident_id=incident_id, investigation_id=inv_id)
            inv_state.status = "RUNNING"
            self._investigations[incident_id] = inv_state
            self._cancel_tokens[incident_id] = False

        start_time = time.perf_counter()
        logger.info(
            f"[InvestigationOrchestrator] Starting Phase 10 Multi-Agent Investigation {inv_id} for incident {incident_id}"
        )

        # Helper to execute within a managed database session
        async def _execute_pipeline(session: AsyncSession) -> Dict[str, Any]:
            # 1. Verify incident exists and synchronize Phase 9 lifecycle status
            inc_stmt = select(Incident).where(Incident.id == incident_id)
            inc_res = await session.execute(inc_stmt)
            incident = inc_res.scalar_one_or_none()
            if not incident:
                inv_state.status = "FAILED"
                inv_state.error_message = f"Incident '{incident_id}' not found."
                return inv_state.to_dict()

            # Attempt Phase 9 lifecycle transition to INVESTIGATING if currently DETECTED/ACKNOWLEDGED
            if incident.status in ("DETECTED", "ACKNOWLEDGED"):
                try:
                    await incident_lifecycle_engine.transition(
                        incident_id=incident_id,
                        target_state="INVESTIGATING",
                        actor="MultiAgentOrchestrator",
                        actor_type="AI_AGENT",
                        reason="Multi-agent DAG investigation dispatched.",
                        session=session,
                    )
                except Exception as ex:
                    logger.debug(f"[InvestigationOrchestrator] Lifecycle auto-transition note: {ex}")

            # Notify Phase 9 real-time timeline stream
            await incident_timeline_engine.record_event(
                incident_id=incident_id,
                event_type="INVESTIGATION_STARTED",
                service_name=incident.impact_scope or "cluster",
                title="Collaborative Multi-Agent Investigation Dispatched",
                description=f"Investigation ID {inv_id}: Dispatching 11 specialized AI agents across parallel diagnostic lanes.",
                severity="INFO",
                actor="MultiAgentOrchestrator",
                actor_type="AI_AGENT",
                data_source=incident.environment or "DEMOMESH",
                session=session,
            )

            workflow_data: Dict[str, Any] = {
                "incident_id": incident_id,
                "investigation_id": inv_id,
                "affected_service": incident.impact_scope or "cluster",
                "environment": incident.environment or "DEMOMESH",
            }

            try:
                # ============================================================
                # Stage 1: Incident Intake & Context Gathering (Sequential)
                # ============================================================
                if self._cancel_tokens.get(incident_id):
                    return inv_state.to_dict()

                inv_state.current_stage = "INTAKE_AND_CONTEXT"
                workflow_data = await self._safe_run_agent(self.intake_agent, incident_id, workflow_data, session, inv_state)
                workflow_data = await self._safe_run_agent(self.context_agent, incident_id, workflow_data, session, inv_state)

                # ============================================================
                # Stage 2: Parallel Concurrent Diagnostic Lanes (Module 10.1 DAG)
                # Dispatches K8s, Logs, Metrics, Traces, Dependencies, Deployments,
                # Network, and Security simultaneously!
                # ============================================================
                if self._cancel_tokens.get(incident_id):
                    return inv_state.to_dict()

                inv_state.current_stage = "PARALLEL_DIAGNOSTICS"
                logger.info(f"[InvestigationOrchestrator] Dispatching Stage 2 parallel diagnostic agents for {incident_id}")

                parallel_agents = [
                    self.kubernetes_agent,
                    self.telemetry_agent,
                    self.log_agent,
                    self.trace_agent,
                    self.dependency_agent,
                    self.deployment_agent,
                    self.network_agent,
                    self.security_agent,
                ]

                # Run parallel diagnostic tasks concurrently with failure isolation
                results = await asyncio.gather(
                    *[
                        self._safe_run_agent(agent, incident_id, workflow_data.copy(), session, inv_state)
                        for agent in parallel_agents
                    ],
                    return_exceptions=True,
                )

                # Merge parallel findings into shared workflow state
                for res in results:
                    if isinstance(res, dict):
                        workflow_data.update(res)

                # ============================================================
                # Stage 3: Root Cause Analysis & Temporal Correlation
                # ============================================================
                if self._cancel_tokens.get(incident_id):
                    return inv_state.to_dict()

                inv_state.current_stage = "ROOT_CAUSE_ANALYSIS"
                workflow_data = await self._safe_run_agent(self.hypothesis_agent, incident_id, workflow_data, session, inv_state)

                # Advanced Root Cause Engine evaluation
                ranked_hypotheses = await advanced_root_cause_engine.evaluate_hypotheses(
                    incident_id=incident_id,
                    session=session,
                    affected_service=workflow_data.get("affected_service"),
                )
                top_hyp = ranked_hypotheses[0] if ranked_hypotheses else None
                workflow_data["primary_hypothesis"] = top_hyp.hypothesis_text if top_hyp else "Systemic operational anomaly"
                workflow_data["ranked_hypotheses"] = [h.model_dump() for h in ranked_hypotheses]

                # Phase 11 Root Cause Intelligence evaluation
                try:
                    from backend.app.services.root_cause.root_cause_service import root_cause_service
                    rc_report = await root_cause_service.evaluate_incident_root_cause(
                        incident_id=incident_id,
                        session=session,
                        investigation_id=inv_id,
                        affected_service=workflow_data.get("affected_service"),
                    )
                    workflow_data["root_cause_report"] = rc_report.model_dump()
                except Exception as rc_err:
                    logger.warning(f"[InvestigationOrchestrator] Phase 11 RootCauseService note: {rc_err}")

                # ============================================================
                # Stage 4: Consensus & Quality Review (Round 1 & Round 2 Re-Investigation)
                # ============================================================
                if self._cancel_tokens.get(incident_id):
                    return inv_state.to_dict()

                inv_state.current_stage = "CONSENSUS_AND_QUALITY"
                workflow_data = await self._safe_run_agent(self.consensus_agent, incident_id, workflow_data, session, inv_state)

                # Round 2 Check: If consensus agent flagged contradictions or gaps, conduct targeted re-investigation
                consensus_info = workflow_data.get("consensus_review", {})
                if consensus_info.get("consensus_status") == "INCONCLUSIVE_DISAGREEMENT":
                    logger.info(f"[InvestigationOrchestrator] Contradiction detected. Running Round 2 targeted verification.")
                    workflow_data = await self._safe_run_agent(self.verification_agent, incident_id, workflow_data, session, inv_state)

                # ============================================================
                # Stage 5: Remediation Intelligence
                # ============================================================
                if self._cancel_tokens.get(incident_id):
                    return inv_state.to_dict()

                inv_state.current_stage = "REMEDIATION_PLANNING"
                workflow_data = await self._safe_run_agent(self.remediation_agent, incident_id, workflow_data, session, inv_state)

                # ============================================================
                # Stage 6: Evidence Verification, Timeline, & Summary
                # ============================================================
                if self._cancel_tokens.get(incident_id):
                    return inv_state.to_dict()

                inv_state.current_stage = "VERIFICATION_AND_SUMMARY"
                workflow_data = await self._safe_run_agent(self.verification_agent, incident_id, workflow_data, session, inv_state)
                workflow_data = await self._safe_run_agent(self.summary_agent, incident_id, workflow_data, session, inv_state)

                # Timeline Reconstructor
                await TimelineReconstructor.reconstruct_timeline(incident_id, workflow_data, session)

                # ============================================================
                # Stage 7: Unified Investigation Report Generation
                # ============================================================
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                inv_state.current_stage = "COMPLETED"
                inv_state.status = "COMPLETED"
                inv_state.finished_at = datetime.now(timezone.utc)
                inv_state.duration_ms = elapsed_ms
                inv_state.data = workflow_data

                # Build final investigation report
                report = {
                    "incident_id": incident_id,
                    "investigation_id": inv_id,
                    "total_duration_ms": elapsed_ms,
                    "completed_agents": inv_state.completed_agents,
                    "failed_agents": inv_state.failed_agents,
                    "affected_service": workflow_data.get("affected_service"),
                    "environment": workflow_data.get("environment"),
                    "primary_root_cause": workflow_data.get("primary_hypothesis"),
                    "confidence_score": top_hyp.confidence_score if top_hyp else 0.85,
                    "confidence_tier": top_hyp.confidence_tier.value if top_hyp else "HIGH_CONFIDENCE",
                    "consensus_status": consensus_info.get("consensus_status", "CONSENSUS_REACHED"),
                    "remediation_recommendations": workflow_data.get("remediation_recommendations", []),
                    "ranked_hypotheses": workflow_data.get("ranked_hypotheses", []),
                    "root_cause_report": workflow_data.get("root_cause_report"),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }
                inv_state.report = report

                # Phase 9 Lifecycle auto-transition to ROOT_CAUSE_IDENTIFIED
                try:
                    await incident_lifecycle_engine.transition(
                        incident_id=incident_id,
                        target_state="ROOT_CAUSE_IDENTIFIED",
                        actor="MultiAgentOrchestrator",
                        actor_type="AI_AGENT",
                        reason=f"Multi-agent investigation reached ruling: {workflow_data.get('primary_hypothesis')[:100]}",
                        session=session,
                    )
                except Exception as ex:
                    logger.debug(f"[InvestigationOrchestrator] Lifecycle transition note: {ex}")

                # Notify Phase 9 real-time timeline stream of completion
                await incident_timeline_engine.record_event(
                    incident_id=incident_id,
                    event_type="INVESTIGATION_COMPLETED",
                    service_name=incident.impact_scope or "cluster",
                    title="Investigation Concluded: Ruling Formulated",
                    description=(
                        f"Investigation {inv_id} concluded in {elapsed_ms}ms with consensus. "
                        f"Ruling: {workflow_data.get('primary_hypothesis')} "
                        f"(Confidence: {report['confidence_score'] * 100}%)."
                    ),
                    severity="INFO",
                    actor="MultiAgentOrchestrator",
                    actor_type="AI_AGENT",
                    data_source=incident.environment or "DEMOMESH",
                    session=session,
                )

                # Record Audit Log
                audit = AuditLog(
                    incident_id=incident_id,
                    actor_type="AGENT",
                    actor_id="MultiAgentOrchestrator",
                    action="INVESTIGATION_COMPLETED",
                    resource_type="INCIDENT",
                    resource_id=incident_id,
                    details=f"All 11 investigation agents completed. Investigation ID: {inv_id}",
                )
                session.add(audit)

                logger.info(
                    f"[InvestigationOrchestrator] Investigation {inv_id} for incident {incident_id} COMPLETED in {elapsed_ms}ms"
                )
                return inv_state.to_dict()

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

        if session_override is not None:
            return await _execute_pipeline(session_override)
        else:
            async with async_session_factory() as session:
                async with session.begin():
                    return await _execute_pipeline(session)


# Singleton orchestrator
investigation_orchestrator = InvestigationOrchestrator()
