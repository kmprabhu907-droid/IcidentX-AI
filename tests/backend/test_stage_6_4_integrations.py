"""
INCIDENTX AI - Stage 6.4 Enterprise Integrations & Connectors Tests
Verifies Slack Block Kit, PagerDuty Events v2, GitHub, Jira, and Generic Webhook HMAC-SHA256 signing.
"""

import json
import pytest
from httpx import AsyncClient
from backend.app.models.integration import IntegrationProvider
from backend.app.services.integrations.github import GitHubConnector
from backend.app.services.integrations.jira import JiraConnector
from backend.app.services.integrations.pagerduty import PagerDutyConnector
from backend.app.services.integrations.slack import SlackConnector
from backend.app.services.integrations.webhook import WebhookConnector


async def _register_and_login(client: AsyncClient, email: str, name: str) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": name,
        "role": "SRE_ENGINEER",
    })
    res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!",
    })
    return res.json()["access_token"]


def test_slack_block_kit_payload():
    """Verify Slack Block Kit JSON adheres to Slack schema with interactive buttons."""
    connector = SlackConnector({"webhook_url": "https://hooks.slack.com/services/test/mock/token"})
    data = {
        "severity": "SEV-1",
        "service_name": "payment-gateway",
        "title": "Cascading Downstream Timeout",
        "incident_id": "inc-uuid-101",
        "root_cause": "Thread starvation in database connection pool",
        "confidence": 0.95,
        "action_id": "act-scale-replicas",
        "action_name": "Scale Service Replicas",
    }
    payload = connector.format_alert_payload("INCIDENT_DETECTED", data)

    assert "blocks" in payload
    blocks = payload["blocks"]

    # Header block
    assert blocks[0]["type"] == "header"
    assert "Incident Detected" in blocks[0]["text"]["text"]

    # Fields section
    fields_block = blocks[1]
    assert fields_block["type"] == "section"
    assert any("SEV-1" in f["text"] for f in fields_block["fields"])
    assert any("payment-gateway" in f["text"] for f in fields_block["fields"])

    # Action block with buttons
    action_block = blocks[-1]
    assert action_block["type"] == "actions"
    elements = action_block["elements"]
    assert any(btn["text"]["text"] == "View in IncidentX" for btn in elements)
    assert any("Approve: Scale Service Replicas" in btn["text"]["text"] for btn in elements)


@pytest.mark.asyncio
async def test_slack_dispatch_mock():
    """Verify Slack dispatch handles mocked URLs cleanly."""
    connector = SlackConnector({"webhook_url": "https://hooks.slack.com/services/test/mock"})
    result = await connector.send_alert("INCIDENT_DETECTED", {"title": "Test Alert"})
    assert result["status"] == "success"
    assert result["mocked"] is True


def test_pagerduty_events_v2_payload():
    """Verify PagerDuty Events API v2 payload mapping and severity normalization."""
    connector = PagerDutyConnector({"routing_key": "test-pd-routing-key-1234567890"})
    data = {
        "severity": "SEV-1",
        "service_name": "order-service",
        "title": "High Error Rate Detected",
        "incident_id": "inc-uuid-202",
        "status": "DETECTED",
        "root_cause": "Out of memory killed container",
    }
    payload = connector.format_alert_payload("INCIDENT_DETECTED", data)

    assert payload["routing_key"] == "test-pd-routing-key-1234567890"
    assert payload["event_action"] == "trigger"
    assert payload["dedup_key"] == "incidentx-inc-uuid-2022" or "incidentx-inc-uuid-202" in payload["dedup_key"]
    assert payload["payload"]["severity"] == "critical"
    assert payload["payload"]["component"] == "order-service"
    assert payload["payload"]["custom_details"]["incident_id"] == "inc-uuid-202"


def test_github_issue_payload():
    """Verify GitHub connector generates structured Markdown post-mortem reports."""
    connector = GitHubConnector({
        "token": "test-gh-token",
        "repo_owner": "incidentx",
        "repo_name": "incidentx-mesh",
    })
    data = {
        "severity": "SEV-2",
        "service_name": "auth-service",
        "title": "JWT Signature Verification Latency",
        "incident_id": "inc-gh-303",
        "root_cause": "JWKS endpoint throttling",
        "action_name": "Cache JWKS Keyset",
    }
    payload = connector.format_alert_payload("ROOT_CAUSE_IDENTIFIED", data)

    assert "[INCIDENTX SEV-2]" in payload["title"]
    assert "IncidentX Autonomous Reliability Report" in payload["body"]
    assert "auth-service" in payload["body"]
    assert "Cache JWKS Keyset" in payload["body"]
    assert "incident" in payload["labels"]


def test_jira_issue_payload():
    """Verify Jira Cloud connector formats issue fields with appropriate priority."""
    connector = JiraConnector({
        "jira_url": "https://company.atlassian.net",
        "email": "sre@company.com",
        "api_token": "test-jira-token",
        "project_key": "REL",
    })
    data = {
        "severity": "SEV-1",
        "service_name": "checkout-service",
        "title": "Checkout Flow 500 Spike",
    }
    payload = connector.format_alert_payload("INCIDENT_DETECTED", data)

    fields = payload["fields"]
    assert fields["project"]["key"] == "REL"
    assert fields["priority"]["name"] == "Highest"
    assert fields["issuetype"]["name"] == "Bug"
    assert "[IncidentX SEV-1]" in fields["summary"]


def test_webhook_hmac_sha256_signing():
    """Verify Generic Webhook connector HMAC-SHA256 signature generation and validation."""
    secret = "my-custom-enterprise-secret-12345"
    connector = WebhookConnector({"url": "http://localhost:9999/webhook", "secret": secret})

    data = {"service": "inventory-service", "event": "SLO_BURN_RATE_EXCEEDED"}
    envelope = connector.format_alert_payload("SLO_BREACH", data)

    payload_bytes = json.dumps(envelope).encode("utf-8")
    signature = connector.compute_signature(payload_bytes, secret)

    assert signature.startswith("sha256=")
    # Verify valid signature succeeds
    assert WebhookConnector.verify_signature(payload_bytes, signature, secret) is True
    # Verify corrupted payload or wrong secret fails
    assert WebhookConnector.verify_signature(payload_bytes, signature, "wrong-secret") is False
    assert WebhookConnector.verify_signature(b'{"corrupted": true}', signature, secret) is False


@pytest.mark.asyncio
async def test_integration_config_crud_and_tenant_isolation(client: AsyncClient):
    """Integrations configured in Tenant A are not visible to Tenant B."""
    token_a = await _register_and_login(client, "sre.a@alpha.internal", "SRE Alpha")
    token_b = await _register_and_login(client, "sre.b@beta.internal", "SRE Beta")

    # Create Org A and Org B
    res_org_a = await client.post("/api/v1/organizations", json={"name": "Org A", "slug": "org-a"}, headers={"Authorization": f"Bearer {token_a}"})
    res_org_b = await client.post("/api/v1/organizations", json={"name": "Org B", "slug": "org-b"}, headers={"Authorization": f"Bearer {token_b}"})

    # SRE A creates Slack integration under Org A
    create_res = await client.post(
        "/api/v1/integrations/configs",
        json={
            "provider": "slack",
            "name": "Org A Production Alerts",
            "is_enabled": True,
            "config_dict": {"webhook_url": "https://hooks.slack.com/services/test/org-a"},
        },
        headers={
            "Authorization": f"Bearer {token_a}",
            "X-Organization-ID": "org-a",
        },
    )
    assert create_res.status_code == 201
    cfg_id = create_res.json()["id"]

    # SRE A sees the connector
    list_a = await client.get("/api/v1/integrations/configs", headers={"Authorization": f"Bearer {token_a}", "X-Organization-ID": "org-a"})
    assert len(list_a.json()) == 1
    assert list_a.json()[0]["name"] == "Org A Production Alerts"

    # SRE B under Org B cannot see SRE A's connector
    list_b = await client.get("/api/v1/integrations/configs", headers={"Authorization": f"Bearer {token_b}", "X-Organization-ID": "org-b"})
    assert len(list_b.json()) == 0

    # Test connection endpoint
    test_res = await client.post(
        f"/api/v1/integrations/configs/{cfg_id}/test",
        headers={"Authorization": f"Bearer {token_a}", "X-Organization-ID": "org-a"},
    )
    assert test_res.status_code == 200
    assert test_res.json()["status"] == "success"


@pytest.mark.asyncio
async def test_integration_dispatcher_broadcast(client: AsyncClient):
    """Dispatch-test endpoint broadcasts to all enabled connectors for the active tenant."""
    token = await _register_and_login(client, "dispatcher.test@incidentx.internal", "Dispatcher SRE")

    # Configure Slack connector
    await client.post(
        "/api/v1/integrations/configs",
        json={
            "provider": "slack",
            "name": "Multi-Channel Slack",
            "is_enabled": True,
            "config_dict": {"webhook_url": "https://hooks.slack.com/services/test/channel"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Configure PagerDuty connector
    await client.post(
        "/api/v1/integrations/configs",
        json={
            "provider": "pagerduty",
            "name": "Multi-Channel PagerDuty",
            "is_enabled": True,
            "config_dict": {"routing_key": "test-pd-key-multi-channel"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Trigger synthetic test dispatch
    dispatch_res = await client.post(
        "/api/v1/integrations/dispatch-test",
        json={
            "event_type": "INCIDENT_DETECTED",
            "severity": "SEV-1",
            "service_name": "checkout-api",
            "title": "Downstream Gateway Timeout",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dispatch_res.status_code == 200
    res_data = dispatch_res.json()
    assert res_data["status"] == "completed"
    assert res_data["dispatched_count"] >= 2
    providers = [r["provider"] for r in res_data["results"]]
    assert "slack" in providers
    assert "pagerduty" in providers
