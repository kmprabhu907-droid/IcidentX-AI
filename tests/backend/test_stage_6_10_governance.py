# ==============================================================================
# IncidentX AI — Stage 6.10 Test Suite: Enterprise Governance & Cryptographic Audit
# Validates Hash Chaining, Tamper Detection, Policy Engine, and Operational Endpoints
# ==============================================================================

import json
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.security import create_access_token, hash_password
from backend.app.models.audit import AuditLog
from backend.app.models.governance import GovernancePolicy
from backend.app.models.user import User, UserRole
from backend.app.services.audit.verifier import (
    GENESIS_HASH,
    compute_audit_hash,
    record_audit_event,
    sanitize_audit_details,
    verify_audit_chain,
)
from backend.app.services.governance.policy_engine import GovernancePolicyEngine


class TestStage610AuditLedgerAndVerification:
    """Tests cryptographic blockchain-style audit logging and tamper detection."""

    def test_compute_audit_hash_deterministic_and_unique(self):
        h1 = compute_audit_hash("0"*64, "2026-11-11T12:00:00Z", "USER", "admin@incidentx.ai", "LOGIN", "AUTH", "user-1", "{}")
        h2 = compute_audit_hash("0"*64, "2026-11-11T12:00:00Z", "USER", "admin@incidentx.ai", "LOGIN", "AUTH", "user-1", "{}")
        assert len(h1) == 64
        assert h1 == h2, "Hash must be deterministic for identical inputs"

        h3 = compute_audit_hash("0"*64, "2026-11-11T12:00:01Z", "USER", "admin@incidentx.ai", "LOGIN", "AUTH", "user-1", "{}")
        assert h1 != h3, "Timestamp change must yield distinct hash"

        h4 = compute_audit_hash("0"*64, "2026-11-11T12:00:00Z", "USER", "admin@incidentx.ai", "LOGOUT", "AUTH", "user-1", "{}")
        assert h1 != h4, "Action change must yield distinct hash"

    def test_sanitize_audit_details_redacts_credentials(self):
        payload = {
            "username": "sre_lead",
            "password": "SuperSecretPassword123!",
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "api_key": "live-api-key-value",
            "safe_metadata": {"service": "checkout-service", "region": "us-east-1"}
        }
        sanitized = sanitize_audit_details(payload)
        parsed = json.loads(sanitized)

        assert parsed["username"] == "sre_lead"
        assert parsed["password"] == "[REDACTED]"
        assert parsed["token"] == "[REDACTED]"
        assert parsed["api_key"] == "[REDACTED]"
        assert parsed["safe_metadata"]["service"] == "checkout-service"

    @pytest.mark.asyncio
    async def test_audit_hash_chain_creation_and_tamper_detection(self, db_session: AsyncSession):
        test_org = "test-chain-org"

        # 1. Create 3 chained audit events
        e1 = await record_audit_event(
            session=db_session,
            actor_type="USER",
            actor_id="sre@incidentx.ai",
            action="INCIDENT_INVESTIGATION_STARTED",
            resource_type="INCIDENT",
            resource_id="inc-100",
            organization_id=test_org,
            details={"severity": "HIGH"}
        )
        await db_session.commit()

        assert e1.prev_hash == GENESIS_HASH
        assert e1.checksum is not None

        e2 = await record_audit_event(
            session=db_session,
            actor_type="AGENT",
            actor_id="ReliabilityAgent",
            action="HYPOTHESIS_FORMULATED",
            resource_type="INCIDENT",
            resource_id="inc-100",
            organization_id=test_org,
            details={"root_cause": "memory_leak"}
        )
        await db_session.commit()

        assert e2.prev_hash == e1.checksum
        assert e2.checksum is not None

        e3 = await record_audit_event(
            session=db_session,
            actor_type="USER",
            actor_id="admin@incidentx.ai",
            action="REMEDIATION_APPROVED",
            resource_type="REMEDIATION_ACTION",
            resource_id="rem-500",
            organization_id=test_org,
            details={"action_name": "restart_pod"}
        )
        await db_session.commit()

        assert e3.prev_hash == e2.checksum

        # 2. Verify pristine chain
        report = await verify_audit_chain(db_session, organization_id=test_org)
        assert report["is_valid"] is True
        assert report["status"] == "SECURE_INTEGRITY_VERIFIED"
        assert report["verified_records"] == 3
        assert len(report["tampered_records"]) == 0

        # 3. Simulate unauthorized database record tampering
        e2.action = "UNAUTHORIZED_ALTERATION"
        await db_session.commit()

        # 4. Verify chain tampering is immediately detected
        tamper_report = await verify_audit_chain(db_session, organization_id=test_org)
        assert tamper_report["is_valid"] is False
        assert tamper_report["status"] == "TAMPERING_DETECTED"
        assert len(tamper_report["tampered_records"]) >= 1


class TestStage610GovernancePolicyEngine:
    """Tests deterministic policy evaluation."""

    @pytest.mark.asyncio
    async def test_ai_remediation_permission_evaluation(self, db_session: AsyncSession):
        org = "test-gov-org"

        # Safe action, low risk -> Permitted
        allowed, reason = await GovernancePolicyEngine.evaluate_ai_remediation_permission(
            session=db_session, organization_id=org, action_type="restart_pod", risk_score=0.20
        )
        assert allowed is True
        assert "permitted" in reason.lower()

        # Safe action, excessive risk -> Blocked
        allowed, reason = await GovernancePolicyEngine.evaluate_ai_remediation_permission(
            session=db_session, organization_id=org, action_type="restart_pod", risk_score=0.85
        )
        assert allowed is False
        assert "exceeds" in reason.lower()

        # Destructive action -> Blocked by human gate
        allowed, reason = await GovernancePolicyEngine.evaluate_ai_remediation_permission(
            session=db_session, organization_id=org, action_type="delete_database", risk_score=0.10
        )
        assert allowed is False
        assert "human-in-the-loop" in reason.lower()

    @pytest.mark.asyncio
    async def test_approval_requirements_evaluation(self, db_session: AsyncSession):
        org = "test-gov-org"

        # Low risk -> 1 approval
        low_risk = await GovernancePolicyEngine.evaluate_approval_requirements(
            session=db_session, organization_id=org, risk_score=0.35
        )
        assert low_risk["required_approvals"] == 1
        assert low_risk["dual_approval_mandated"] is False

        # High risk -> 2 approvals mandated
        high_risk = await GovernancePolicyEngine.evaluate_approval_requirements(
            session=db_session, organization_id=org, risk_score=0.80
        )
        assert high_risk["required_approvals"] == 2
        assert high_risk["dual_approval_mandated"] is True


class TestStage610GovernanceAPI:
    """Tests operational administration and audit verification endpoints."""

    @pytest.mark.asyncio
    async def test_governance_policies_list_and_create(self, client: AsyncClient, db_session: AsyncSession):
        admin = User(
            email="gov.admin@incidentx.internal",
            hashed_password=hash_password("Password123!"),
            full_name="Gov Admin",
            role=UserRole.SUPER_ADMIN.value,
            is_active=True,
            is_superuser=True,
            organization_id="default-org"
        )
        db_session.add(admin)
        await db_session.commit()
        await db_session.refresh(admin)

        token = create_access_token({"sub": admin.id, "email": admin.email, "role": admin.role})
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Fetch default governance policies
        resp = await client.get("/api/v1/governance/policies", headers=headers)
        assert resp.status_code == 200
        policies = resp.json()
        assert len(policies) >= 4
        policy_types = [p["policy_type"] for p in policies]
        assert "AI_EXECUTION_PERMISSION" in policy_types
        assert "APPROVAL_POLICY" in policy_types

        # 2. Update a policy
        update_payload = {
            "policy_type": "DATA_RETENTION",
            "name": "Strict Enterprise Data Retention",
            "description": "Retention window tuned to 180 days for audit compliance",
            "rules": {"retention_days": 180, "archive_before_purge": True},
            "is_enforced": True
        }
        post_resp = await client.post("/api/v1/governance/policies", json=update_payload, headers=headers)
        assert post_resp.status_code == 201
        data = post_resp.json()
        assert data["name"] == "Strict Enterprise Data Retention"
        assert data["rules"]["retention_days"] == 180

    @pytest.mark.asyncio
    async def test_operational_health_overview(self, client: AsyncClient, db_session: AsyncSession):
        admin = User(
            email="sre.lead@incidentx.internal",
            hashed_password=hash_password("Password123!"),
            full_name="SRE Lead",
            role=UserRole.SRE_ENGINEER.value,
            is_active=True,
            is_superuser=False,
            organization_id="default-org"
        )
        db_session.add(admin)
        await db_session.commit()
        await db_session.refresh(admin)

        token = create_access_token({"sub": admin.id, "email": admin.email, "role": admin.role})
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/governance/health-overview", headers=headers)
        assert resp.status_code == 200
        overview = resp.json()
        assert overview["status"] == "OPERATIONAL"
        assert "system_health" in overview
        assert "operational_metrics" in overview
        assert "storage_and_governance" in overview
        assert overview["system_health"]["api_server"] == "HEALTHY"

    @pytest.mark.asyncio
    async def test_audit_logs_verify_endpoint(self, client: AsyncClient, db_session: AsyncSession):
        auditor = User(
            email="auditor@incidentx.internal",
            hashed_password=hash_password("Password123!"),
            full_name="Auditor User",
            role=UserRole.SECURITY_AUDITOR.value,
            is_active=True,
            is_superuser=False,
            organization_id="default-org"
        )
        db_session.add(auditor)
        await db_session.commit()
        await db_session.refresh(auditor)

        token = create_access_token({"sub": auditor.id, "email": auditor.email, "role": auditor.role})
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/audit-logs/verify", headers=headers)
        assert resp.status_code == 200
        report = resp.json()
        assert "is_valid" in report
        assert "status" in report
        assert "verified_at" in report
