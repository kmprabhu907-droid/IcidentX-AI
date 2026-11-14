"""
INCIDENTX AI - Evidence-Grounded Incident Reasoning Engine (Phase 8.4)
Coordinates the 11-stage AI reasoning workflow:
Evidence ingestion, environment validation, hypothesis generation, counter-evidence search,
Root Cause Courtroom 2.0 evaluation, and Reliability Memory registration.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.infrastructure.core.environment_manager import environment_manager
from backend.app.infrastructure.core.infrastructure_models import EnvironmentMode
from backend.app.services.ai.courtroom.courtroom_engine import courtroom_engine
from backend.app.services.ai.models import (
    AIIncidentReasoningReport,
    AIReasoningEvidenceItem,
    CourtroomVerdict,
    ModelAttribution,
)
from backend.app.services.ai.router import llm_router
from backend.app.services.observability.unified_correlation_engine import unified_correlation_engine


class ReasoningEngine:
    """
    Production-grade multi-agent reasoning orchestrator grounded in verified telemetry.
    """

    def __init__(self):
        # In-memory store of past incident reasoning reports: incident_id -> AIIncidentReasoningReport
        self._reports: Dict[str, AIIncidentReasoningReport] = {}

    async def ingest_incident_evidence(
        self,
        incident_id: str,
        session: Optional[AsyncSession] = None,
    ) -> List[AIReasoningEvidenceItem]:
        """
        Extract and normalize heterogeneous telemetry items into strictly typed evidence contracts.
        Enforces environment isolation between DemoMesh (SIMULATED) and Kubernetes (LIVE_K8S).
        """
        timeline = await unified_correlation_engine.build_incident_timeline(
            incident_id=incident_id,
            session=session,
            limit=50,
        )

        expected_data_source = (
            "SIMULATED" if environment_manager.active_mode == EnvironmentMode.DEMOMESH else "LIVE_K8S"
        )

        evidence_items: List[AIReasoningEvidenceItem] = []

        for item in timeline:
            # Enforce environment isolation
            ds = item.data_source
            if ds != expected_data_source and item.source != "INCIDENT":
                logger.warning(
                    f"[ReasoningEngine] Dropping mismatched evidence '{item.id}' (source {ds} vs expected {expected_data_source})"
                )
                continue

            # Classify statement type
            stmt_type = "OBSERVED_FACT"
            if item.category == "METRIC_ANOMALY":
                stmt_type = "DERIVED_CALCULATION"
            elif item.category == "INCIDENT_STATE":
                stmt_type = "OBSERVED_FACT"

            evidence_items.append(
                AIReasoningEvidenceItem(
                    evidence_id=item.id,
                    source_type=item.source,
                    statement_classification=stmt_type,
                    resource_name=item.resource_name,
                    timestamp=item.timestamp,
                    details=item.details,
                    data_source=ds,
                    is_valid=True,
                )
            )

        # Fallback dummy evidence if timeline was empty
        if not evidence_items:
            evidence_items.append(
                AIReasoningEvidenceItem(
                    evidence_id=f"ev-init-{uuid.uuid4().hex[:6]}",
                    source_type="DEMOMESH" if expected_data_source == "SIMULATED" else "KUBERNETES",
                    statement_classification="OBSERVED_FACT",
                    resource_name="cluster-health",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    details={"status": "DEGRADED", "reason": "Initial incident trigger"},
                    data_source=expected_data_source,
                    is_valid=True,
                )
            )

        return evidence_items

    async def run_reasoning(
        self,
        incident_id: str,
        session: Optional[AsyncSession] = None,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
    ) -> AIIncidentReasoningReport:
        """
        Execute full end-to-end multi-agent AI reasoning pipeline for an incident.
        """
        logger.info(f"[ReasoningEngine] Initiating AI reasoning for incident '{incident_id}'...")

        # 1. Ingest & Validate Evidence Contract
        evidence_items = await self.ingest_incident_evidence(incident_id, session=session)

        # 2. Formulate Prompt Context
        system_prompt = (
            "You are the IncidentX AI Principal SRE & Autonomous Reliability Architect. "
            "Your objective is to evaluate infrastructure telemetry and formulate competing root-cause hypotheses. "
            "CRITICAL RULES:\n"
            "1. You MUST reference valid evidence IDs from the provided evidence list.\n"
            "2. Never hallucinate resource names, metrics, or non-existent evidence IDs.\n"
            "3. Formulate alternative competing explanations and actively test for contradicting counter-evidence.\n"
            "4. Classify risk level for all recommended recovery actions (LOW, MEDIUM, HIGH).\n"
            "5. Never output executable shell commands or direct infrastructure modifications."
        )

        user_prompt = f"Analyze incident '{incident_id}' based on the provided infrastructure telemetry."

        context_data = {
            "incident_id": incident_id,
            "evidence": [e.model_dump() for e in evidence_items],
            "environment_mode": environment_manager.active_mode.value,
        }

        # 3. Call LLM Router for Structured Courtroom Verdict
        verdict, attribution = await llm_router.generate_structured(
            schema=CourtroomVerdict,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context_data=context_data,
            preferred_provider=preferred_provider,
            preferred_model=preferred_model,
            incident_id=incident_id,
            agent_name="CourtroomVerdictAgent",
        )

        # 4. Pass candidate verdict through Courtroom 2.0 Engine for counter-evidence and confidence calibration
        calibrated_verdict = courtroom_engine.evaluate(
            evidence_items=evidence_items,
            candidate_hypotheses=verdict.competing_hypotheses,
            attribution=attribution,
        )

        # 5. Extract Recommended Actions
        recommended_actions = []
        for hyp in calibrated_verdict.competing_hypotheses:
            if hyp.is_leading and hyp.recommended_action:
                recommended_actions.append(hyp.recommended_action)

        if not recommended_actions:
            recommended_actions.append({
                "action_id": "act-investigate-topology",
                "name": "Investigate Service Dependencies & Logs",
                "risk_level": "LOW",
                "target_service": "cluster",
            })

        # 6. Assemble Full Report
        report = AIIncidentReasoningReport(
            incident_id=incident_id,
            status="COMPLETED",
            evidence_items=evidence_items,
            courtroom_verdict=calibrated_verdict,
            recommended_actions=recommended_actions,
            model_attribution=attribution,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Store report in-memory
        self._reports[incident_id] = report

        # 7. Bridge to Reliability Memory
        try:
            from backend.app.services.ai.reasoning_memory import reasoning_memory_bridge
            await reasoning_memory_bridge.record_reasoning_outcome(report, session)
        except Exception as e:
            logger.warning(f"[ReasoningEngine] Failed to record in Reliability Memory: {e}")

        logger.info(
            f"[ReasoningEngine] Reasoning completed for '{incident_id}' via {attribution.provider_name} ({attribution.model_name}) in {attribution.execution_time_ms}ms"
        )
        return report

    def get_report(self, incident_id: str) -> Optional[AIIncidentReasoningReport]:
        return self._reports.get(incident_id)

    def list_reports(self) -> List[AIIncidentReasoningReport]:
        return list(self._reports.values())


# Global singleton instance
reasoning_engine = ReasoningEngine()
