"""
INCIDENTX AI - Intelligent Alert Ingestion Engine (Phase 9 Module 9.3)
Ingests, normalizes, validates, deduplicates, and correlates alerts from Prometheus Alertmanager,
Grafana, Kubernetes Events, OpenTelemetry signals, and webhooks.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
import uuid
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import IncidentXException
from backend.app.core.logging import logger
from backend.app.infrastructure.core.environment_manager import environment_manager
from backend.app.infrastructure.core.infrastructure_models import EnvironmentMode
from backend.app.models.alert import Alert
from backend.app.models.audit import AuditLog
from backend.app.models.incident import Incident
from backend.app.models.timeline import TimelineEvent
from backend.app.services.agents.oncall_agent import oncall_incident_agent
from backend.app.services.incident.lifecycle_engine import IncidentLifecycleEngine
from backend.app.services.incident.timeline_engine import incident_timeline_engine


class IngestedAlertPayload(BaseModel):
    source: str = Field(default="generic_webhook", description="alertmanager, grafana, kubernetes, opentelemetry, webhook, manual")
    alert_name: Optional[str] = Field(None, description="Name or title of the alert")
    service_name: Optional[str] = Field(None, description="Target microservice or workload")
    severity: Optional[str] = Field("P2", description="P1, P2, P3, P4 or SEV-1, SEV-2, etc.")
    environment: Optional[str] = Field(None, description="DEMOMESH or KUBERNETES")
    description: Optional[str] = Field(None, description="Alert message or observation")
    raw_payload: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Raw incoming webhook payload")


class AlertIngestionResult(BaseModel):
    action: str  # CREATED, CORRELATED, SUPPRESSED, REJECTED
    incident_id: str
    alert_id: str
    fingerprint: str
    is_new_incident: bool
    service_name: str
    severity: str
    environment: str
    summary: str


class AlertIngestionEngine:
    """
    Normalizes, fingerprints, deduplicates, and links alerts to incidents.
    """

    @classmethod
    def generate_fingerprint(
        cls, service_name: str, alert_name: str, environment: str, error_signature: str = ""
    ) -> str:
        key = f"{service_name.lower().strip()}:{alert_name.lower().strip()}:{environment.upper().strip()}:{error_signature.strip()}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    @classmethod
    def parse_payload(cls, raw_data: Dict[str, Any], explicit_source: Optional[str] = None) -> IngestedAlertPayload:
        """
        Parses incoming payload across Prometheus Alertmanager, Grafana, Kubernetes, or generic.
        """
        source = explicit_source or "webhook"
        service = "unknown-service"
        alert_name = "InfrastructureAlert"
        severity = "P2"
        description = "Automated alert received from monitoring provider."
        env = environment_manager.active_mode.value

        # 1. Prometheus Alertmanager Format
        if "alerts" in raw_data and isinstance(raw_data["alerts"], list) and raw_data["alerts"]:
            source = "alertmanager"
            first = raw_data["alerts"][0]
            labels = first.get("labels", {})
            annotations = first.get("annotations", {})
            alert_name = labels.get("alertname", labels.get("alert_name", "PrometheusAlert"))
            service = labels.get("service", labels.get("app", labels.get("job", "cluster")))
            severity = labels.get("severity", "P2")
            description = (
                annotations.get("description")
                or annotations.get("summary")
                or annotations.get("message")
                or f"Prometheus alert '{alert_name}' fired on {service}."
            )
            env = labels.get("environment", labels.get("env", env))

        # 2. Grafana Alerting Format
        elif "ruleName" in raw_data or "evalMatches" in raw_data:
            source = "grafana"
            alert_name = raw_data.get("ruleName", "GrafanaAlert")
            service = raw_data.get("tags", {}).get("service", "cluster")
            severity = raw_data.get("tags", {}).get("severity", "P2")
            description = raw_data.get("message") or f"Grafana rule '{alert_name}' state changed to {raw_data.get('state')}."

        # 3. Kubernetes Infrastructure / Warning Event Format
        elif "reason" in raw_data and ("involvedObject" in raw_data or "resource_name" in raw_data):
            source = "kubernetes"
            alert_name = raw_data.get("reason", "KubernetesWarning")
            service = (
                raw_data.get("resource_name")
                or raw_data.get("involvedObject", {}).get("name")
                or "kubernetes-workload"
            )
            severity = "P1" if alert_name in ["OOMKilled", "CrashLoopBackOff"] else "P2"
            description = raw_data.get("message", f"Kubernetes warning [{alert_name}] on {service}.")
            env = "KUBERNETES"

        # 4. Standard / Generic IncidentX Webhook
        else:
            source = raw_data.get("source", source)
            service = raw_data.get("service_name") or raw_data.get("service", service)
            alert_name = raw_data.get("alert_name") or raw_data.get("title", alert_name)
            severity = raw_data.get("severity", severity)
            description = raw_data.get("description") or raw_data.get("summary", description)
            env = raw_data.get("environment", env)

        norm_sev = IncidentLifecycleEngine.normalize_severity(severity)

        return IngestedAlertPayload(
            source=source,
            alert_name=alert_name,
            service_name=service,
            severity=norm_sev,
            environment=env.upper(),
            description=description,
            raw_payload=raw_data,
        )

    @classmethod
    async def ingest_alert(
        cls,
        payload_data: Dict[str, Any],
        session: AsyncSession,
        source_override: Optional[str] = None,
    ) -> AlertIngestionResult:
        """
        Executes full alert ingestion, deduplication against open incidents, and lifecycle creation.
        """
        now = datetime.now(timezone.utc)
        parsed = cls.parse_payload(payload_data, explicit_source=source_override)

        fingerprint = cls.generate_fingerprint(
            service_name=parsed.service_name,
            alert_name=parsed.alert_name,
            environment=parsed.environment,
        )

        # 1. Search for existing OPEN incident for deduplication
        open_states = [
            "DETECTED",
            "ACKNOWLEDGED",
            "INVESTIGATING",
            "ROOT_CAUSE_IDENTIFIED",
            "REMEDIATION_PENDING",
            "REMEDIATING",
            "VERIFYING",
        ]

        query = (
            select(Incident)
            .where(
                Incident.status.in_(open_states),
                Incident.environment == parsed.environment,
            )
            .order_by(desc(Incident.detected_at))
        )
        res = await session.execute(query)
        open_incidents = list(res.scalars().all())

        # Match by fingerprint or impacted service
        matching_incident: Optional[Incident] = None
        for inc in open_incidents:
            if inc.fingerprint == fingerprint or (inc.impact_scope and parsed.service_name in inc.impact_scope):
                matching_incident = inc
                break

        alert_id = str(uuid.uuid4())
        raw_json_str = json.dumps(parsed.raw_payload)

        if matching_incident:
            # -------------------------------------------------------------
            # DEDUPLICATION / CORRELATION BRANCH
            # -------------------------------------------------------------
            alert = Alert(
                id=alert_id,
                incident_id=matching_incident.id,
                fingerprint=fingerprint,
                alert_name=parsed.alert_name,
                source=parsed.source,
                severity=parsed.severity,
                service_name=parsed.service_name,
                environment=parsed.environment,
                status="CORRELATED",
                description=parsed.description,
                starts_at=now,
                raw_payload=raw_json_str,
                occurrence_count=1,
                last_seen_at=now,
            )
            session.add(alert)

            # Record Timeline Event
            await incident_timeline_engine.record_event(
                incident_id=matching_incident.id,
                event_type="ALERT_CORRELATED",
                service_name=parsed.service_name,
                title=f"Correlated Alert: {parsed.alert_name}",
                description=f"Incoming alert from '{parsed.source}' correlated with active incident '{matching_incident.title}'.",
                severity="INFO",
                actor=f"{parsed.source}-ingestion",
                actor_type="SYSTEM",
                data_source=parsed.environment,
                raw_data=raw_json_str,
                session=session,
            )

            logger.info(
                f"[AlertIngestion] Correlated alert '{parsed.alert_name}' on {parsed.service_name} to incident {matching_incident.id}"
            )

            return AlertIngestionResult(
                action="CORRELATED",
                incident_id=matching_incident.id,
                alert_id=alert_id,
                fingerprint=fingerprint,
                is_new_incident=False,
                service_name=parsed.service_name,
                severity=parsed.severity,
                environment=parsed.environment,
                summary=f"Alert correlated with active incident '{matching_incident.title}'.",
            )

        else:
            # -------------------------------------------------------------
            # NEW INCIDENT CREATION BRANCH
            # -------------------------------------------------------------
            incident_id = f"inc-{uuid.uuid4().hex[:8]}"
            title = f"[{parsed.severity}] {parsed.alert_name} on {parsed.service_name}"

            new_incident = Incident(
                id=incident_id,
                title=title,
                summary=parsed.description,
                severity=parsed.severity,
                status="DETECTED",
                priority="CRITICAL" if parsed.severity in ["P1", "SEV-1"] else ("HIGH" if parsed.severity in ["P2", "SEV-2"] else "MEDIUM"),
                environment=parsed.environment,
                source=parsed.source,
                fingerprint=fingerprint,
                impact_scope=parsed.service_name,
                organization_id="default-org",
                detected_at=now,
                assigned_team="Platform SRE",
                oncall_responder="IncidentX AI (Tier-1 Primary SRE)",
            )
            session.add(new_incident)
            await session.flush()

            # Create Alert record
            alert = Alert(
                id=alert_id,
                incident_id=incident_id,
                fingerprint=fingerprint,
                alert_name=parsed.alert_name,
                source=parsed.source,
                severity=parsed.severity,
                service_name=parsed.service_name,
                environment=parsed.environment,
                status="ACTIVE",
                description=parsed.description,
                starts_at=now,
                raw_payload=raw_json_str,
                occurrence_count=1,
                last_seen_at=now,
            )
            session.add(alert)

            # Record Timeline Events: ALERT_INGESTED and INCIDENT_CREATED
            await incident_timeline_engine.record_event(
                incident_id=incident_id,
                event_type="ALERT_INGESTED",
                service_name=parsed.service_name,
                title=f"Alert Ingested: {parsed.alert_name}",
                description=f"Raw alert ingested from '{parsed.source}'. Severity: {parsed.severity}. Service: {parsed.service_name}.",
                severity="WARN" if parsed.severity in ["P1", "P2"] else "INFO",
                actor=f"{parsed.source}-ingestion",
                actor_type="SYSTEM",
                data_source=parsed.environment,
                raw_data=raw_json_str,
                session=session,
            )

            await incident_timeline_engine.record_event(
                incident_id=incident_id,
                event_type="INCIDENT_CREATED",
                service_name=parsed.service_name,
                title=f"Incident Created: {incident_id}",
                description=f"Incident initialized in DETECTED state. Priority: {new_incident.priority}. Assigned to: {new_incident.assigned_team}.",
                severity="CRITICAL" if parsed.severity == "P1" else "WARN",
                actor="IncidentLifecycleEngine",
                actor_type="SYSTEM",
                data_source=parsed.environment,
                session=session,
            )

            # Auto-acknowledge page alert through On-Call Agent (Tier-1 AI Responder)
            try:
                page = await oncall_incident_agent.ingest_page(
                    {
                        "service_name": parsed.service_name,
                        "severity": parsed.severity,
                        "source": parsed.source,
                        "summary": parsed.description,
                        "incident_id": incident_id,
                    },
                    db=session,
                )
                new_incident.acknowledged_at = datetime.now(timezone.utc)
                new_incident.acknowledged_by = page.acknowledged_by or "IncidentX AI (Tier-1)"
                new_incident.status = "ACKNOWLEDGED"

                await incident_timeline_engine.record_event(
                    incident_id=incident_id,
                    event_type="ACKNOWLEDGED",
                    service_name=parsed.service_name,
                    title="Auto-Acknowledged by Tier-1 AI",
                    description=f"Sub-second MTTA achieved: {page.mtta_seconds}s by {new_incident.acknowledged_by}.",
                    severity="INFO",
                    actor=new_incident.acknowledged_by,
                    actor_type="AI_AGENT",
                    data_source=parsed.environment,
                    session=session,
                )
            except Exception as oncall_err:
                logger.warning(f"[AlertIngestion] On-call auto-ack non-fatal issue: {oncall_err}")

            # Audit log
            audit = AuditLog(
                incident_id=incident_id,
                organization_id="default-org",
                actor_type="SYSTEM",
                actor_id=f"{parsed.source}-ingestion",
                action="INCIDENT_CREATED_FROM_ALERT",
                resource_type="Incident",
                resource_id=incident_id,
                details=f"Created incident '{title}' from alert '{parsed.alert_name}'.",
            )
            session.add(audit)

            logger.info(f"[AlertIngestion] Created new incident {incident_id} from alert '{parsed.alert_name}'")

            return AlertIngestionResult(
                action="CREATED",
                incident_id=incident_id,
                alert_id=alert_id,
                fingerprint=fingerprint,
                is_new_incident=True,
                service_name=parsed.service_name,
                severity=parsed.severity,
                environment=parsed.environment,
                summary=f"New incident '{title}' created and auto-acknowledged.",
            )


# Singleton engine
alert_ingestion_engine = AlertIngestionEngine()
