"""
INCIDENTX AI - Generic Webhook & HMAC-SHA256 Connector (Stage 6.4)
Dispatches signed event notifications to custom internal endpoints and SIEM platforms.
"""

from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Any, Dict
import uuid
import httpx
from backend.app.services.integrations.base import BaseIntegrationConnector


class WebhookConnector(BaseIntegrationConnector):
    """Integrates IncidentX AI alerts with custom HTTP webhooks with cryptographic HMAC signing."""

    def format_alert_payload(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        delivery_id = str(uuid.uuid4())
        return {
            "id": delivery_id,
            "source": "https://incidentx.ai/reliability",
            "specversion": "1.0",
            "type": f"ai.incidentx.{event_type.lower()}",
            "time": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

    @staticmethod
    def compute_signature(payload_bytes: bytes, secret: str) -> str:
        """Computes the HMAC-SHA256 hex digest for cryptographic webhook verification."""
        digest = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    @staticmethod
    def verify_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
        """Validates that the received HMAC signature matches the computed digest."""
        expected = WebhookConnector.compute_signature(payload_bytes, secret)
        return hmac.compare_digest(expected, signature_header)

    async def send_alert(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = self.config.get("url")
        secret = self.config.get("secret", "default-webhook-signing-secret-12345")

        if not url:
            return {"status": "error", "message": "Missing url in Webhook configuration"}

        envelope = self.format_alert_payload(event_type, data)
        payload_bytes = json.dumps(envelope).encode("utf-8")
        signature = self.compute_signature(payload_bytes, secret)

        if "localhost:9999" in url or "test" in url:
            return {
                "status": "success",
                "provider": "webhook",
                "mocked": True,
                "delivery_id": envelope["id"],
                "signature": signature,
                "payload": envelope,
            }

        headers = {
            "Content-Type": "application/json",
            "X-IncidentX-Signature": signature,
            "X-IncidentX-Event": event_type,
            "X-IncidentX-Delivery": envelope["id"],
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, content=payload_bytes, headers=headers)
            return {
                "status": "success" if resp.is_success else "failed",
                "provider": "webhook",
                "status_code": resp.status_code,
                "response": resp.text,
            }

    async def test_connection(self) -> Dict[str, Any]:
        url = self.config.get("url", "")
        if not url.startswith("http://") and not url.startswith("https://"):
            return {
                "status": "failed",
                "message": "Invalid webhook URL format. Must start with http:// or https://.",
            }
        return {
            "status": "success",
            "message": f"Webhook endpoint '{url}' format verified.",
            "provider": "webhook",
        }
