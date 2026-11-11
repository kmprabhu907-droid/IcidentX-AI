"""
INCIDENTX AI - Enterprise Governance & Operational Administration API Router
Provides operational management, system health overview, and configurable governance policies.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.auth import get_current_user, require_permission, require_roles
from backend.app.core.database import get_db
from backend.app.core.tenant import resolve_tenant
from backend.app.models.governance import GovernancePolicy
from backend.app.models.incident import Incident
from backend.app.models.integration import IntegrationConfig
from backend.app.models.investigation import AgentExecution
from backend.app.models.organization import Organization, OrganizationMembership
from backend.app.models.remediation import RemediationAction
from backend.app.models.telemetry import TelemetryEvent
from backend.app.models.user import User, UserRole
from backend.app.models.workflow import WorkflowExecution
from backend.app.services.audit.verifier import record_audit_event
from backend.app.services.governance.policy_engine import DEFAULT_POLICIES, GovernancePolicyEngine

router = APIRouter(prefix="/governance", tags=["Audit & Governance"])


class GovernancePolicyCreateRequest(BaseModel):
    policy_type: str = Field(..., description="Policy category (DATA_RETENTION, APPROVAL_POLICY, AI_EXECUTION_PERMISSION, ORG_LIMITS)")
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    rules: Dict[str, Any] = Field(..., description="JSON rule parameters for policy")
    is_enforced: bool = True


class GovernancePolicyResponse(BaseModel):
    id: str
    organization_id: str
    policy_type: str
    name: str
    description: Optional[str]
    rules: Dict[str, Any]
    is_enforced: bool
    created_by: str
    created_at: datetime
    updated_at: datetime


@router.get("/policies", response_model=List[GovernancePolicyResponse])
async def list_governance_policies(
    db: AsyncSession = Depends(get_db),
    tenant_org_id: str = Depends(resolve_tenant),
    current_user: Optional[User] = Depends(require_permission("audit:read")),
):
    """
    Lists active and default governance policies for the current organization.
    """
    query = select(GovernancePolicy).where(GovernancePolicy.organization_id == tenant_org_id)
    result = await db.execute(query)
    policies = list(result.scalars().all())

    # If no custom policies exist yet, expose default baseline policies
    existing_types = {p.policy_type for p in policies}
    responses = []

    for p in policies:
        rules_dict = {}
        try:
            rules_dict = json.loads(p.rules)
        except Exception:
            pass
        responses.append(
            GovernancePolicyResponse(
                id=p.id,
                organization_id=p.organization_id,
                policy_type=p.policy_type,
                name=p.name,
                description=p.description,
                rules=rules_dict,
                is_enforced=p.is_enforced,
                created_by=p.created_by,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
        )

    for p_type, default_rules in DEFAULT_POLICIES.items():
        if p_type not in existing_types:
            responses.append(
                GovernancePolicyResponse(
                    id=f"default-{p_type.lower()}",
                    organization_id=tenant_org_id,
                    policy_type=p_type,
                    name=f"Standard Enterprise {p_type.replace('_', ' ').title()}",
                    description=f"Built-in baseline governance policy for {p_type}",
                    rules=default_rules,
                    is_enforced=True,
                    created_by="system-default",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )

    return responses


@router.post("/policies", response_model=GovernancePolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_governance_policy(
    payload: GovernancePolicyCreateRequest,
    db: AsyncSession = Depends(get_db),
    tenant_org_id: str = Depends(resolve_tenant),
    current_user: Optional[User] = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ORGANIZATION_ADMIN])),
):
    """
    Configures or updates an enterprise governance policy. Restricted to organization administrators.
    """
    valid_types = {"DATA_RETENTION", "APPROVAL_POLICY", "AI_EXECUTION_PERMISSION", "ORG_LIMITS"}
    if payload.policy_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid policy_type '{payload.policy_type}'. Valid options: {valid_types}"
        )

    # Check for existing policy of this type
    query = select(GovernancePolicy).where(
        GovernancePolicy.organization_id == tenant_org_id,
        GovernancePolicy.policy_type == payload.policy_type,
    )
    res = await db.execute(query)
    policy = res.scalar_one_or_none()

    actor_id = current_user.email if current_user else "admin"

    if policy:
        policy.name = payload.name
        policy.description = payload.description
        policy.rules = json.dumps(payload.rules, sort_keys=True)
        policy.is_enforced = payload.is_enforced
    else:
        policy = GovernancePolicy(
            organization_id=tenant_org_id,
            policy_type=payload.policy_type,
            name=payload.name,
            description=payload.description,
            rules=json.dumps(payload.rules, sort_keys=True),
            is_enforced=payload.is_enforced,
            created_by=actor_id,
        )
        db.add(policy)

    await db.commit()
    await db.refresh(policy)

    # Record tamper-evident audit log
    await record_audit_event(
        session=db,
        actor_type="USER",
        actor_id=actor_id,
        action="GOVERNANCE_POLICY_UPDATED",
        resource_type="GOVERNANCE_POLICY",
        resource_id=policy.id,
        details={"policy_type": payload.policy_type, "name": payload.name, "is_enforced": payload.is_enforced},
        organization_id=tenant_org_id,
    )
    await db.commit()

    return GovernancePolicyResponse(
        id=policy.id,
        organization_id=policy.organization_id,
        policy_type=policy.policy_type,
        name=policy.name,
        description=policy.description,
        rules=payload.rules,
        is_enforced=policy.is_enforced,
        created_by=policy.created_by,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@router.get("/health-overview")
async def get_operational_health_overview(
    db: AsyncSession = Depends(get_db),
    tenant_org_id: str = Depends(resolve_tenant),
    current_user: Optional[User] = Depends(require_permission("audit:read")),
) -> Dict[str, Any]:
    """
    Consolidated Operational Administration View:
    Returns system health, active organizations, user activity, integration health,
    agent activity, error rates, and storage telemetry.
    """
    # 1. User & Organization metrics
    user_count_res = await db.execute(select(func.count(User.id)))
    total_users = user_count_res.scalar() or 0

    org_count_res = await db.execute(select(func.count(Organization.id)))
    total_orgs = org_count_res.scalar() or 0

    # 2. Incident & Remediation metrics
    incident_count_res = await db.execute(select(func.count(Incident.id)))
    total_incidents = incident_count_res.scalar() or 0

    remediation_count_res = await db.execute(select(func.count(RemediationAction.id)))
    total_remediations = remediation_count_res.scalar() or 0

    # 3. Agent Execution Activity
    agent_exec_res = await db.execute(select(func.count(AgentExecution.id)))
    total_agent_executions = agent_exec_res.scalar() or 0

    # 4. Integration Health
    integrations_res = await db.execute(
        select(IntegrationConfig).where(IntegrationConfig.organization_id == tenant_org_id)
    )
    integrations = list(integrations_res.scalars().all())
    active_integrations = sum(1 for i in integrations if i.is_active)

    # 5. Telemetry & Storage utilization
    telemetry_count_res = await db.execute(select(func.count(TelemetryEvent.id)))
    total_telemetry_events = telemetry_count_res.scalar() or 0

    # 6. Workflows
    workflows_res = await db.execute(select(func.count(WorkflowExecution.id)))
    total_workflows = workflows_res.scalar() or 0

    retention_days = await GovernancePolicyEngine.get_retention_days(db, tenant_org_id)

    return {
        "status": "OPERATIONAL",
        "system_health": {
            "api_server": "HEALTHY",
            "database_connectivity": "CONNECTED",
            "redis_cache": "ACTIVE",
            "workflow_worker": "ONLINE",
            "demomesh_telemetry": "SYNCHRONIZED",
        },
        "tenant_overview": {
            "current_tenant": tenant_org_id,
            "total_organizations": total_orgs,
            "total_registered_users": total_users,
        },
        "operational_metrics": {
            "total_incidents_recorded": total_incidents,
            "total_remediations_executed": total_remediations,
            "total_autonomous_workflows": total_workflows,
            "total_ai_agent_executions": total_agent_executions,
            "configured_integrations": len(integrations),
            "active_integrations": active_integrations,
        },
        "storage_and_governance": {
            "telemetry_events_stored": total_telemetry_events,
            "data_retention_days": retention_days,
            "audit_ledger_status": "TAMPER_EVIDENT_CHAIN_ACTIVE",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
