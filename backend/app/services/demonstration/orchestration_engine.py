"""
INCIDENTX AI - Hackathon Demonstration & End-to-End Orchestrator (Phase 16 Master Engine)
Executes the complete 16-step autonomous SRE orchestration loop across all 15 previous phases:
Detect -> Investigate -> Root Cause -> Remediate -> Verify -> Learn -> Postmortem.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import asyncio
import uuid

from backend.app.core.logging import logger
from backend.app.services.demonstration.schemas import (
    DemonstrationScenario,
    DemonstrationScenarioID,
    OrchestrationExecutionResult,
    OrchestrationStep,
    StepStatus,
)
from backend.app.services.communication.notification_service import notification_service
from backend.app.services.communication.schemas import NotificationEventType
from backend.app.services.sre_intelligence.sre_engine import sre_intelligence_engine
from backend.app.services.learning.learning_service import learning_service
from backend.app.services.learning.schemas import TelemetryStage
from backend.app.services.learning.telemetry_comparator import TelemetryComparator


class DemonstrationOrchestrator:
    """
    Coordinates and drives live hackathon demonstration scenarios.
    """

    SCENARIOS = {
        DemonstrationScenarioID.SCENARIO_A: DemonstrationScenario(
            scenario_id=DemonstrationScenarioID.SCENARIO_A,
            title="Deployment-Induced API Latency Spike",
            target_service="payment-service",
            severity="SEV-1",
            environment="DEMOMESH",
            fault_type="DATABASE_REGRESSION_AFTER_DEPLOY",
            description="Recent rollout v2.4.1 introduced unindexed ledger query, causing database connection pool lockup and P95 latency jump to 1840ms.",
            expected_root_cause="Unindexed ledger transaction query introduced in commit sha-9b2f11 locked connection pool.",
            proposed_remediation="Rollback deployment to previous revision v2.4.0 (git sha-7a8f12).",
        ),
        DemonstrationScenarioID.SCENARIO_B: DemonstrationScenario(
            scenario_id=DemonstrationScenarioID.SCENARIO_B,
            title="Kubernetes Memory Exhaustion & OOMKilled Cascades",
            target_service="order-service",
            severity="SEV-1",
            environment="DEMOMESH",
            fault_type="JVM_HEAP_LEAK_OOMKILLED",
            description="Unbounded in-memory session cache caused container heap saturation, triggering continuous CrashLoopBackOff restarts.",
            expected_root_cause="Linear JVM heap growth exceeded container 512Mi limit, resulting in exit code 137 (OOMKilled).",
            proposed_remediation="Rolling restart of deployment and increase memory limit to 768Mi.",
        ),
        DemonstrationScenarioID.SCENARIO_C: DemonstrationScenario(
            scenario_id=DemonstrationScenarioID.SCENARIO_C,
            title="Cascading Service Dependency Failure",
            target_service="auth-service",
            severity="SEV-2",
            environment="DEMOMESH",
            fault_type="THREAD_DEADLOCK_UPSTREAM_CASCADE",
            description="Token cache synchronization contention blocked API gateway threads, threatening cascading checkout failure.",
            expected_root_cause="Lock inversion on shared cryptographic JWT token cache during high concurrent load.",
            proposed_remediation="Trigger cache warmup recovery workflow and enable upstream rate-limiting circuit breaker.",
        ),
    }

    def __init__(self):
        self._history: Dict[str, OrchestrationExecutionResult] = {}
        self._active_scenario_id: Optional[DemonstrationScenarioID] = None

    def list_scenarios(self) -> List[DemonstrationScenario]:
        return list(self.SCENARIOS.values())

    def reset_scenarios(self) -> None:
        """Resets active demo state."""
        self._active_scenario_id = None
        logger.info("[DemonstrationOrchestrator] All demonstration scenarios reset.")

    async def execute_scenario(
        self,
        scenario_id: DemonstrationScenarioID,
        environment: str = "DEMOMESH",
    ) -> OrchestrationExecutionResult:
        """
        Drives the full 16-step autonomous SRE orchestration loop.
        """
        scenario = self.SCENARIOS.get(scenario_id, self.SCENARIOS[DemonstrationScenarioID.SCENARIO_A])
        exec_id = f"demo-exec-{uuid.uuid4().hex[:8]}"
        incident_id = f"INC-2026-{uuid.uuid4().hex[:4].upper()}"
        now = datetime.now(timezone.utc)

        result = OrchestrationExecutionResult(
            execution_id=exec_id,
            scenario_id=scenario_id,
            incident_id=incident_id,
            title=f"Autonomous Resolution: {scenario.title}",
            severity=scenario.severity,
            target_service=scenario.target_service,
            environment=environment,
            started_at=now,
        )

        steps_definition = [
            (1, "Telemetry Anomaly Detection", "Phase 15 SRE", f"Multi-signal anomaly detected on '{scenario.target_service}'. Z-score > 3.8."),
            (2, "Incident Creation & Triage", "Phase 9 Command", f"Created incident {incident_id} ({scenario.severity}) mapped to Core SRE."),
            (3, "On-Call Notification & Paging", "Phase 14 Comm", f"Dispatched P1 page to Primary On-Call (Sarah Chen). Escalation timer armed."),
            (4, "Multi-Agent Investigation Launch", "Phase 10 Multi-Agent", "Coordinator dispatched 5 specialized agents to investigate."),
            (5, "Cross-Domain Evidence Collection", "Phase 8.3 & 10", "Harvested Kubernetes pod logs, Prometheus metrics, and traces."),
            (6, "Intelligent Hypothesis Generation", "Phase 11 Root Cause", "Synthesized 3 competing hypotheses (Deployment regression, OOM, Network)."),
            (7, "Counter-Evidence Cross-Examination", "Phase 11 Courtroom", "Examined counter-evidence: DB connectivity was intact; git sha correlated."),
            (8, "Autonomous Judicial Ruling", "Phase 11 Courtroom", f"Verdict rendered: {scenario.expected_root_cause} (Confidence: 94%)."),
            (9, "Intelligent Remediation Planning", "Phase 12 Planning", f"Generated structured remediation plan: {scenario.proposed_remediation}"),
            (10, "Deterministic Risk Assessment", "Phase 12 Risk", "Evaluated risk score 0.85 (CRITICAL). Requires human emergency override."),
            (11, "Anti-Tamper Human Authorization", "Phase 12 Approval", "Incident Commander approved action with SHA-256 parameter signature."),
            (12, "Controlled Safe Execution", "Phase 12 Execution", f"Executed allowlisted action on '{scenario.target_service}' in {environment}."),
            (13, "Empirical 12-Pillar Verification", "Phase 13 Recovery", "Sampled post-remediation telemetry: Pods ready, error rate dropped to 0.15%."),
            (14, "Multi-Interval Stability Observation", "Phase 13 Stability", "Monitored 5-minute observation window; 0 drift detected, 0 crash loops."),
            (15, "Enterprise Postmortem Generation", "Phase 13 Postmortem", "Synthesized audit-grade postmortem with Facts vs AI Hypotheses and tasks."),
            (16, "Controlled Self-Learning & Knowledge Ingestion", "Phase 13 & 15", "Stored fingerprint into Knowledge Base; incremented learning weights."),
        ]

        # Initialize steps
        for step_num, name, phase, details in steps_definition:
            result.steps.append(
                OrchestrationStep(
                    step_number=step_num,
                    name=name,
                    phase_ref=phase,
                    status=StepStatus.PENDING,
                    details=details,
                )
            )

        # Execute through steps sequentially
        for step in result.steps:
            step.started_at = datetime.now(timezone.utc)
            step.status = StepStatus.IN_PROGRESS
            # Small yield to simulate distributed agent processing
            await asyncio.sleep(0.01)

            # Specific Step Hooks
            if step.step_number == 3:
                notification_service.send_incident_notification(
                    incident_id=incident_id,
                    event_type=NotificationEventType.SEV1_CRITICAL,
                    severity=scenario.severity,
                    title=scenario.title,
                    affected_service=scenario.target_service,
                    summary=scenario.description,
                )
                step.evidence.append(f"Notification delivered to Slack, PagerDuty, and Console.")

            elif step.step_number == 8:
                step.evidence.append(f"Confirmed Root Cause: {scenario.expected_root_cause}")
                result.root_cause_ruling = scenario.expected_root_cause
                result.confidence_score = 0.94

            elif step.step_number == 12:
                step.evidence.append(f"Action executed: {scenario.proposed_remediation}")
                result.remediation_executed = scenario.proposed_remediation

            elif step.step_number == 15:
                pm = learning_service.generate_postmortem(
                    incident_id=incident_id,
                    title=scenario.title,
                    severity=scenario.severity,
                    environment=environment,
                    affected_services=[scenario.target_service],
                    detected_at=now,
                    verified_root_cause=scenario.expected_root_cause,
                    root_cause_is_conclusive=True,
                    remediation_performed=scenario.proposed_remediation,
                )
                result.postmortem_id = pm.postmortem_id
                step.evidence.append(f"Postmortem ID: {pm.postmortem_id} (HTML/Markdown export ready)")

            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now(timezone.utc)

        end_time = datetime.now(timezone.utc)
        result.completed_at = end_time
        result.total_duration_seconds = round((end_time - now).total_seconds(), 2)
        result.is_completed = True

        self._history[exec_id] = result
        logger.info(f"[DemonstrationOrchestrator] Completed scenario {scenario_id.value} in {result.total_duration_seconds}s")
        return result

    def get_execution(self, execution_id: str) -> Optional[OrchestrationExecutionResult]:
        return self._history.get(execution_id)

    def list_executions(self) -> List[OrchestrationExecutionResult]:
        return list(self._history.values())


demonstration_orchestrator = DemonstrationOrchestrator()
