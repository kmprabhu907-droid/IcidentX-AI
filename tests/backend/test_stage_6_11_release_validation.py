# ==============================================================================
# IncidentX AI — Stage 6.11 Test Suite: Production Validation & Enterprise Release
# Validates Master Release Report, Health Probes, and Production Readiness Contracts
# ==============================================================================

from pathlib import Path
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.security import create_access_token, hash_password
from backend.app.models.user import User, UserRole

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestStage611ReleaseDocumentation:
    """Validates the official enterprise release documentation."""

    def test_release_report_exists_and_contains_all_stages(self):
        report_path = REPO_ROOT / "docs" / "phase6" / "PHASE_6_ENTERPRISE_RELEASE_REPORT.md"
        assert report_path.exists(), "Master enterprise release report must exist"

        content = report_path.read_text()

        # Verify all stages are documented
        for stage in [
            "Stage 6.0",
            "Stage 6.1",
            "Stage 6.2",
            "Stage 6.3",
            "Stage 6.4",
            "Stage 6.5",
            "Stage 6.6",
            "Stage 6.7",
            "Stage 6.8",
            "Stage 6.9",
            "Stage 6.10",
            "Stage 6.11",
        ]:
            assert stage in content, f"Release report must document {stage}"

        # Verify release decision
        assert "PRODUCTION_READY" in content, "Release report must state PRODUCTION_READY classification"

        # Verify benchmarks and DR metrics
        assert "Actual Measured Performance Benchmarks" in content
        assert "Disaster Recovery & Resilience Targets" in content
        assert "Security Assessment & Threat Posture" in content


class TestStage611HealthAndOperationalContracts:
    """Validates Kubernetes health probes and operational endpoints."""

    @pytest.mark.asyncio
    async def test_kubernetes_liveness_and_readiness_probes(self, client: AsyncClient):
        # 1. Liveness probe
        live_resp = await client.get("/api/v1/health/live")
        assert live_resp.status_code == 200
        live_data = live_resp.json()
        assert live_data["status"] == "alive"

        # 2. Readiness probe
        ready_resp = await client.get("/api/v1/health/ready")
        assert ready_resp.status_code == 200
        ready_data = ready_resp.json()
        assert ready_data["status"] in ["ready", "not_ready"]
        assert "subsystems" in ready_data
        assert "database" in ready_data["subsystems"]

        # 3. Startup probe
        startup_resp = await client.get("/api/v1/health/startup")
        assert startup_resp.status_code == 200
        startup_data = startup_resp.json()
        assert startup_data["status"] == "started"

    @pytest.mark.asyncio
    async def test_operational_governance_contract(self, client: AsyncClient, db_session: AsyncSession):
        sre = User(
            email="sre.validation@incidentx.internal",
            hashed_password=hash_password("Password123!"),
            full_name="SRE Validator",
            role=UserRole.SRE_ENGINEER.value,
            is_active=True,
            is_superuser=False,
            organization_id="default-org"
        )
        db_session.add(sre)
        await db_session.commit()
        await db_session.refresh(sre)

        token = create_access_token({"sub": sre.id, "email": sre.email, "role": sre.role})
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/governance/health-overview", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "OPERATIONAL"
        assert data["system_health"]["api_server"] == "HEALTHY"
        assert data["storage_and_governance"]["audit_ledger_status"] == "TAMPER_EVIDENT_CHAIN_ACTIVE"
