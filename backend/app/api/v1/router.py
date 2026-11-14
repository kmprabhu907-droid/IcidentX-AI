"""
INCIDENTX AI - API v1 Master Router
"""

from fastapi import APIRouter
from backend.app.api.v1.incidents import router as incidents_router
from backend.app.api.v1.services import router as services_router
from backend.app.api.v1.investigation import router as investigation_router
from backend.app.api.v1.audit import router as audit_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.observability import router as observability_router
from backend.app.api.v1.telemetry import router as telemetry_router
from backend.app.api.v1.simulation import router as simulation_router
from backend.app.api.v1.remediation import router as remediation_router
from backend.app.api.v1.reliability import router as reliability_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.organizations import router as organizations_router
from backend.app.api.v1.integrations import router as integrations_router
from backend.app.api.v1.workflows import router as workflows_router
from backend.app.api.v1.governance import router as governance_router
from backend.app.api.v1.showcase import router as showcase_router
from backend.app.api.v1.environments import router as environments_router
from backend.app.api.v1.kubernetes import router as kubernetes_router
from backend.app.api.v1.ai import router as ai_router
from backend.app.api.v1.oncall import router as oncall_router
from backend.app.api.v1.alerts import router as alerts_router
from backend.app.api.v1.root_cause import router as root_cause_router
from backend.app.api.v1.resolution import router as resolution_router
from backend.app.api.v1.learning import router as learning_router
from backend.app.api.v1.communication import router as communication_router
from backend.app.api.v1.sre_intelligence import router as sre_intelligence_router
from backend.app.api.v1.demonstration import router as demonstration_router

api_v1_router = APIRouter()

api_v1_router.include_router(alerts_router)
api_v1_router.include_router(root_cause_router)
api_v1_router.include_router(resolution_router)
api_v1_router.include_router(learning_router)
api_v1_router.include_router(communication_router)
api_v1_router.include_router(sre_intelligence_router)
api_v1_router.include_router(demonstration_router)
api_v1_router.include_router(oncall_router)
api_v1_router.include_router(ai_router)
api_v1_router.include_router(environments_router)
api_v1_router.include_router(kubernetes_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(organizations_router)
api_v1_router.include_router(governance_router)
api_v1_router.include_router(showcase_router)
api_v1_router.include_router(integrations_router)
api_v1_router.include_router(workflows_router)
api_v1_router.include_router(health_router)
api_v1_router.include_router(incidents_router)
api_v1_router.include_router(services_router)
api_v1_router.include_router(investigation_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(observability_router)
api_v1_router.include_router(telemetry_router)
api_v1_router.include_router(simulation_router)
api_v1_router.include_router(remediation_router)
api_v1_router.include_router(reliability_router)
