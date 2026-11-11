"""
INCIDENTX AI - Enterprise Integrations API Router (Stage 6.4)
Configures and dispatches alerts to Slack, PagerDuty, GitHub, Jira, and Webhooks.
"""

import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import get_current_user, require_roles
from backend.app.core.database import get_db
from backend.app.core.tenant import get_current_tenant
from backend.app.models.integration import IntegrationConfig, IntegrationProvider
from backend.app.models.organization import Organization
from backend.app.models.user import User, UserRole
from backend.app.schemas.auth import MessageResponse
from backend.app.schemas.integration import (
    EventDispatchTestRequest,
    IntegrationConfigCreateRequest,
    IntegrationConfigResponse,
    IntegrationConfigUpdateRequest,
    IntegrationTestResponse,
)
from backend.app.services.integrations.dispatcher import integration_dispatcher

router = APIRouter(prefix="/integrations", tags=["Enterprise Integrations & Connectors"])


def _to_response(cfg: IntegrationConfig) -> IntegrationConfigResponse:
    try:
        events = json.loads(cfg.events_subscribed) if cfg.events_subscribed else []
    except Exception:
        events = []
    return IntegrationConfigResponse(
        id=cfg.id,
        organization_id=cfg.organization_id,
        provider=cfg.provider,
        name=cfg.name,
        is_enabled=cfg.is_enabled,
        events_subscribed=events,
        created_at=cfg.created_at,
        updated_at=cfg.updated_at,
    )


@router.post(
    "/configs",
    response_model=IntegrationConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create integration connector configuration",
)
async def create_integration_config(
    payload: IntegrationConfigCreateRequest,
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_cfg = IntegrationConfig(
        organization_id=tenant.id,
        provider=payload.provider.value,
        name=payload.name.strip(),
        is_enabled=payload.is_enabled,
        config_json=json.dumps(payload.config_dict),
        events_subscribed=json.dumps(payload.events_subscribed),
    )
    db.add(new_cfg)
    await db.commit()
    await db.refresh(new_cfg)

    return _to_response(new_cfg)


@router.get(
    "/configs",
    response_model=List[IntegrationConfigResponse],
    summary="List integration connectors for the current tenant",
)
async def list_integration_configs(
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(IntegrationConfig)
        .where(IntegrationConfig.organization_id == tenant.id)
        .order_by(IntegrationConfig.created_at.desc())
    )
    result = await db.execute(stmt)
    configs = result.scalars().all()
    return [_to_response(c) for c in configs]


@router.get(
    "/configs/{config_id}",
    response_model=IntegrationConfigResponse,
    summary="Get integration connector details",
)
async def get_integration_config(
    config_id: str,
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(IntegrationConfig).where(
        IntegrationConfig.id == config_id,
        IntegrationConfig.organization_id == tenant.id,
    )
    cfg = (await db.execute(stmt)).scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail="Integration connector not found.")
    return _to_response(cfg)


@router.delete(
    "/configs/{config_id}",
    response_model=MessageResponse,
    summary="Delete integration connector",
)
async def delete_integration_config(
    config_id: str,
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(IntegrationConfig).where(
        IntegrationConfig.id == config_id,
        IntegrationConfig.organization_id == tenant.id,
    )
    cfg = (await db.execute(stmt)).scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail="Integration connector not found.")

    await db.delete(cfg)
    await db.commit()
    return MessageResponse(message=f"Integration '{cfg.name}' successfully deleted.")


@router.post(
    "/configs/{config_id}/test",
    response_model=IntegrationTestResponse,
    summary="Test integration connector connectivity",
)
async def test_integration_connection(
    config_id: str,
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(IntegrationConfig).where(
        IntegrationConfig.id == config_id,
        IntegrationConfig.organization_id == tenant.id,
    )
    cfg = (await db.execute(stmt)).scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail="Integration connector not found.")

    config_dict = json.loads(cfg.config_json) if cfg.config_json else {}
    connector = integration_dispatcher.get_connector(cfg.provider, config_dict)
    test_result = await connector.test_connection()

    return IntegrationTestResponse(
        status=test_result.get("status", "unknown"),
        message=test_result.get("message", "Test completed"),
        provider=cfg.provider,
    )


@router.post(
    "/dispatch-test",
    summary="Dispatch a synthetic test event across all enabled connectors",
)
async def dispatch_test_event(
    payload: EventDispatchTestRequest,
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event_data = {
        "severity": payload.severity,
        "service_name": payload.service_name,
        "title": payload.title,
        "root_cause": payload.root_cause,
        "confidence": payload.confidence,
        "action_name": payload.action_name,
        "incident_id": "test-incident-uuid-001",
    }

    results = await integration_dispatcher.dispatch_event(
        organization_id=tenant.id,
        event_type=payload.event_type,
        data=event_data,
        db=db,
    )

    return {
        "status": "completed",
        "tenant_id": tenant.id,
        "event_type": payload.event_type,
        "dispatched_count": len(results),
        "results": results,
    }
