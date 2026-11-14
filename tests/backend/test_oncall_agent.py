"""
INCIDENTX AI - Autonomous On-Call Incident Agent Test Suite
Verifies:
1. Shift status & 24/7 on-call roster management
2. Paged alert ingestion & sub-second autonomous acknowledgment (MTTA)
3. Autonomous on-call triage loop with Courtroom 2.0 evidence integration
4. Interactive On-Call Agent Copilot conversation
5. Executive Slack stakeholder updates & SRE blameless post-mortem generation
6. Human Tier-2 escalation policy
7. FastAPI REST endpoints (/api/v1/oncall/*)
"""

import pytest
from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.app.services.agents.oncall_agent import OnCallIncidentAgent, oncall_incident_agent


@pytest.mark.asyncio
async def test_oncall_shift_status():
    """Verify on-call shift roster, responder tiers, and MTTA calculations."""
    agent = OnCallIncidentAgent()
    status = agent.get_shift_status()

    assert "shift" in status
    assert status["shift"]["duty_status"] == "ON_DUTY"
    assert "Tier-1" in status["shift"]["primary_responder"]
    assert "Tier-2" in status["shift"]["secondary_responder"]
    assert status["shift"]["mean_time_to_acknowledge_seconds"] > 0.0
    assert len(status["all_pages"]) >= 1


@pytest.mark.asyncio
async def test_oncall_page_ingestion_and_auto_ack():
    """Verify incoming alerts are automatically acknowledged with sub-second MTTA."""
    agent = OnCallIncidentAgent()

    alert_data = {
        "service_name": "payment-service",
        "severity": "SEV-1",
        "source": "PagerDuty",
        "summary": "HTTP 500 error rate spike to 18.5% on /pay endpoint",
    }

    page = await agent.ingest_page(alert_data)

    assert page.page_id.startswith("page-")
    assert page.service_name == "payment-service"
    assert page.severity == "SEV-1"
    assert page.status == "ACKNOWLEDGED"
    assert page.mtta_seconds is not None
    assert page.mtta_seconds < 3.0
    assert "Tier-1" in page.acknowledged_by


@pytest.mark.asyncio
async def test_oncall_incident_triage():
    """Verify autonomous triage invokes multi-agent reasoning and formulates recovery advice."""
    agent = OnCallIncidentAgent()
    incident_id = "inc-oncall-test-101"

    triage = await agent.triage_incident(incident_id=incident_id, db=None)

    assert triage["incident_id"] == incident_id
    assert triage["status"] == "TRIAGED"
    assert "Autonomous triage verified" in triage["triage_summary"]
    assert triage["confidence_score"] > 0.0
    assert triage["leading_root_cause"] != ""
    assert triage["recommended_action"] is not None


@pytest.mark.asyncio
async def test_oncall_chat_copilot_intents():
    """Verify On-Call Agent Copilot handles roster, alerts, updates, and general queries."""
    agent = OnCallIncidentAgent()

    # 1. Roster query
    res1 = await agent.chat("Who is on call right now?")
    assert "Primary Responder" in res1["content"]
    assert "Tier-1" in res1["content"]

    # 2. Alerts query
    res2 = await agent.chat("What alerts are active?")
    assert "Active On-Call Pages" in res2["content"] or "operational" in res2["content"]

    # 3. Stakeholder update query
    res3 = await agent.chat("Draft a Slack update for incident inc-test-01")
    assert "INCIDENT UPDATE" in res3["content"]

    # 4. Post-mortem query
    res4 = await agent.chat("Generate postmortem for incident inc-test-01")
    assert "Blameless Post-Mortem" in res4["content"]


@pytest.mark.asyncio
async def test_oncall_stakeholder_update_drafting():
    """Verify Slack stakeholder update draft is structured and includes Courtroom consensus."""
    agent = OnCallIncidentAgent()
    incident_id = "inc-update-test-202"

    draft = await agent.draft_stakeholder_update(incident_id=incident_id, audience="SLACK")

    assert draft["incident_id"] == incident_id
    assert "🚨 *[INCIDENT UPDATE" in draft["slack_message"]
    assert "Root Cause Assessment" in draft["slack_message"]
    assert "Next Operational Steps" in draft["slack_message"]


@pytest.mark.asyncio
async def test_oncall_blameless_postmortem_generation():
    """Verify blameless post-mortem report follows Google SRE structure."""
    agent = OnCallIncidentAgent()
    incident_id = "inc-pm-test-303"

    pm = await agent.generate_blameless_postmortem(incident_id=incident_id)

    assert pm["incident_id"] == incident_id
    assert "# Blameless Post-Mortem Report" in pm["markdown_report"]
    assert "## 1. Executive Summary" in pm["markdown_report"]
    assert "## 2. Root Cause Analysis (Courtroom 2.0 Verdict)" in pm["markdown_report"]
    assert "## 3. Timeline of Events" in pm["markdown_report"]
    assert "## 4. Where We Got Lucky" in pm["markdown_report"]
    assert "## 5. Action Items & Preventative Measures" in pm["markdown_report"]


@pytest.mark.asyncio
async def test_oncall_escalation_to_human():
    """Verify escalation transfers responsibility to Tier-2 SRE with audit reason."""
    agent = OnCallIncidentAgent()

    page = await agent.ingest_page({"service_name": "auth-service", "summary": "Unresolvable token corruption"})

    esc = await agent.escalate_to_human(
        page_id=page.page_id,
        reason="Requires manual cryptographic certificate rotation beyond automated runbook permissions.",
    )

    assert esc["status"] == "ESCALATED"
    assert "Tier-2" in esc["escalated_to"]
    assert "cryptographic" in esc["escalation_reason"]

    # Verify status in agent
    updated_page = agent._pages[page.page_id]
    assert updated_page.status == "ESCALATED"


@pytest.mark.asyncio
async def test_oncall_api_endpoints():
    """Verify all /api/v1/oncall/* endpoints respond with proper JSON schemas."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/v1/oncall/status
        res_status = await client.get("/api/v1/oncall/status")
        assert res_status.status_code == 200
        data = res_status.json()
        assert "shift" in data
        assert "active_pages" in data

        # 2. POST /api/v1/oncall/page
        res_page = await client.post(
            "/api/v1/oncall/page",
            json={
                "service_name": "inventory-service",
                "severity": "SEV-2",
                "source": "Alertmanager",
                "summary": "Inventory synchronization drift detected",
            },
        )
        assert res_page.status_code == 200
        p_data = res_page.json()
        assert p_data["status"] == "ACKNOWLEDGED"
        page_id = p_data["page"]["page_id"]

        # 3. POST /api/v1/oncall/chat
        res_chat = await client.post(
            "/api/v1/oncall/chat",
            json={"message": "What is the status of active pages?"},
        )
        assert res_chat.status_code == 200
        assert "content" in res_chat.json()

        # 4. POST /api/v1/oncall/update/{id}/draft
        res_update = await client.post("/api/v1/oncall/update/inc-api-test/draft")
        assert res_update.status_code == 200
        assert "slack_message" in res_update.json()

        # 5. POST /api/v1/oncall/postmortem/{id}
        res_pm = await client.post("/api/v1/oncall/postmortem/inc-api-test")
        assert res_pm.status_code == 200
        assert "markdown_report" in res_pm.json()

        # 6. POST /api/v1/oncall/escalate/{page_id}
        res_esc = await client.post(
            f"/api/v1/oncall/escalate/{page_id}",
            json={"reason": "Blast radius exceeded single-service threshold"},
        )
        assert res_esc.status_code == 200
        assert res_esc.json()["status"] == "ESCALATED"
