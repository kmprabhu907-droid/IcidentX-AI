"""
INCIDENTX AI - Alert Pydantic Schemas (Phase 9)
Schemas for alert ingestion from Prometheus Alertmanager, Grafana, Kubernetes, and Webhooks.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AlertIngestRequest(BaseModel):
    source: str = Field(default="generic_webhook", description="alertmanager, grafana, kubernetes, opentelemetry, webhook, manual")
    alert_name: Optional[str] = Field(None, description="Name or identifier of the alert rule")
    service_name: Optional[str] = Field(None, description="Impacted microservice or workload")
    severity: Optional[str] = Field("P2", description="P1, P2, P3, P4 or SEV-1, SEV-2, etc.")
    environment: Optional[str] = Field(None, description="DEMOMESH or KUBERNETES")
    description: Optional[str] = Field(None, description="Alert observation message")
    alerts: Optional[List[Dict[str, Any]]] = Field(None, description="Prometheus Alertmanager alerts array")
    evalMatches: Optional[List[Dict[str, Any]]] = Field(None, description="Grafana evalMatches array")
    ruleName: Optional[str] = Field(None, description="Grafana rule name")
    reason: Optional[str] = Field(None, description="Kubernetes event reason (OOMKilled, CrashLoopBackOff, etc.)")
    raw_payload: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Raw metadata")


class AlertResponse(BaseModel):
    id: str
    incident_id: Optional[str] = None
    fingerprint: str
    alert_name: str
    source: str
    severity: str
    service_name: str
    environment: str
    status: str
    description: str
    occurrence_count: int
    starts_at: datetime
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertIngestResponse(BaseModel):
    action: str  # CREATED, CORRELATED, SUPPRESSED
    incident_id: str
    alert_id: str
    fingerprint: str
    is_new_incident: bool
    service_name: str
    severity: str
    environment: str
    summary: str
