"""
INCIDENTX AI - PagerDuty Events API v2 Connector (Stage 6.4)
Handles automated on-call paging, deduplication keys, and incident resolution synchronization.
"""

from datetime import datetime, timezone
from typing import Any, Dict
import httpx
from backend.app.services.integrations.base import BaseIntegrationConnector


SEVERITY_MAP = {
    "SEV-1": "critical",
    "SEV-2": "error",
    "SEV-3": "warning",
    "SEV-4": "info",
}


class PagerDutyConnector(BaseIntegrationConnector):
    """Integrates IncidentX AI alerts with PagerDuty Events API v2."""

    PAGERDUTY_V2_URL = "https://events.pagerduty.com/v2/enqueue"

    def format_alert_payload(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        routing_key = self.config.get("routing_key", "")
        raw_sev = data.get("severity", "SEV-2")
        pd_severity = SEVERITY_MAP.get(raw_sev.upper(), "error")

        incident_id = data.get("incident_id", "default")
        title = data.get("title", f"Autonomous Alert: {event_type}")
        service_name = data.get("service_name", "DemoMesh Cluster")

        action = "trigger"
        if data.get("status") in ("RESOLVED", "CLOSED"):
            action = "resolve"
        elif data.get("status") == "INVESTIGATING":
            action = "acknowledge"

        payload = {
            "routing_key": routing_key,
            "event_action": action,
            "dedup_key": f"incidentx-{incident_id}",
            "payload": {
                "summary": f"[{raw_sev}] IncidentX: {title} on {service_name}",
                "severity": pd_severity,
                "source": f"IncidentX-AI/{service_name}",
                "component": service_name,
                "group": "Reliability-Control-Plane",
                "class": event_type,
                "custom_details": {
                    "incident_id": incident_id,
                    "event_type": event_type,
                    "root_cause": data.get("root_cause"),
                    "confidence": data.get("confidence", 0.0),
                    "action_name": data.get("action_name"),
                    "dashboard_url": f"http://localhost:3000/incidents/{incident_id}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        }
        return payload

    async def send_alert(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        routing_key = self.config.get("routing_key")
        if not routing_key:
            return {"status": "error", "message": "Missing routing_key in PagerDuty configuration"}

        payload = self.format_alert_payload(event_type, data)

        # Mock / Test routing keys skip external HTTP request
        if routing_key.startswith("test-") or routing_key == "mock-key":
            return {
                "status": "success",
                "provider": "pagerduty",
                "mocked": True,
                "dedup_key": payload["dedup_key"],
                "event_action": payload["event_action"],
                "delivered_at": datetime.now(timezone.utc).isoformat(),
                "payload": payload,
            }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(self.PAGERDUTY_V2_URL, json=payload)
            return {
                "status": "success" if resp.is_success else "failed",
                "provider": "pagerduty",
                "status_code": resp.status_code,
                "response": resp.json() if resp.is_success else resp.text,
            }

    async def test_connection(self) -> Dict[str, Any]:
        routing_key = self.config.get("routing_key", "")
        if not routing_key or len(routing_key) < 16:
            return {
                "status": "failed",
                "message": "Invalid PagerDuty integration routing_key. Expected a 32-character Service Integration Key.",
            }
        return {
            "status": "success",
            "message": "PagerDuty integration key validated.",
            "provider": "pagerduty",
        }
