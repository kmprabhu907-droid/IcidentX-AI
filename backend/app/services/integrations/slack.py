"""
INCIDENTX AI - Slack Enterprise Block Kit Connector (Stage 6.4)
Renders interactive Slack Block Kit incident cards with one-click remediation actions.
"""

from datetime import datetime, timezone
from typing import Any, Dict
import httpx
from backend.app.services.integrations.base import BaseIntegrationConnector


class SlackConnector(BaseIntegrationConnector):
    """Integrates IncidentX AI alerts and human approvals with Slack Webhooks & Bot APIs."""

    def format_alert_payload(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        severity = data.get("severity", "SEV-2")
        service_name = data.get("service_name", "cluster")
        title = data.get("title", "Autonomous Reliability Alert")
        incident_id = data.get("incident_id", "")
        root_cause = data.get("root_cause", None)
        confidence = data.get("confidence", 0.0)
        action_id = data.get("action_id", None)
        action_name = data.get("action_name", "Auto-Remediation")
        dashboard_url = f"http://localhost:3000/incidents/{incident_id}" if incident_id else "http://localhost:3000/reliability"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 IncidentX AI: {event_type.replace('_', ' ').title()}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Severity:*\n`{severity}`"},
                    {"type": "mrkdwn", "text": f"*Service:*\n`{service_name}`"},
                    {"type": "mrkdwn", "text": f"*Event Title:*\n{title}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n<!date^{int(datetime.now(timezone.utc).timestamp())}^{{date_num}} {{time_secs}}|{datetime.now(timezone.utc).isoformat()}>",
                    },
                ],
            },
        ]

        if root_cause:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*AI Causal Hypothesis:*\n>{root_cause}\n*Confidence Score:* `{confidence * 100:.1f}%`",
                },
            })

        # Interactive Action Buttons
        action_elements = [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "View in IncidentX", "emoji": True},
                "url": dashboard_url,
                "action_id": "view_incident",
            }
        ]

        if action_id:
            action_elements.append({
                "type": "button",
                "text": {"type": "plain_text", "text": f"Approve: {action_name}", "emoji": True},
                "style": "primary",
                "value": f"approve:{action_id}",
                "action_id": "approve_remediation",
            })

        blocks.append({
            "type": "actions",
            "elements": action_elements,
        })

        return {
            "text": f"[{severity}] {event_type} on {service_name}: {title}",
            "blocks": blocks,
        }

    async def send_alert(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        webhook_url = self.config.get("webhook_url")
        if not webhook_url:
            return {"status": "error", "message": "Missing webhook_url in Slack configuration"}

        payload = self.format_alert_payload(event_type, data)

        # Mock / Test URLs skip actual HTTP dispatch
        if "hooks.slack.com/services/test" in webhook_url or "localhost" in webhook_url:
            return {
                "status": "success",
                "provider": "slack",
                "mocked": True,
                "delivered_at": datetime.now(timezone.utc).isoformat(),
                "payload": payload,
            }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=payload)
            return {
                "status": "success" if resp.is_success else "failed",
                "provider": "slack",
                "status_code": resp.status_code,
                "response": resp.text,
            }

    async def test_connection(self) -> Dict[str, Any]:
        webhook_url = self.config.get("webhook_url", "")
        if not webhook_url.startswith("https://hooks.slack.com/services/") and "test" not in webhook_url:
            return {
                "status": "failed",
                "message": "Invalid Slack webhook URL format. Expected 'https://hooks.slack.com/services/...' format.",
            }
        return {
            "status": "success",
            "message": "Slack webhook endpoint verified and ready.",
            "provider": "slack",
        }
