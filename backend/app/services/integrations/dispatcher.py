"""
INCIDENTX AI - Enterprise Integration Event Dispatcher (Stage 6.4)
Coordinates multi-channel broadcasting across Slack, PagerDuty, GitHub, Jira, and Webhooks.
"""

import json
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.models.integration import IntegrationConfig, IntegrationProvider
from backend.app.services.integrations.base import BaseIntegrationConnector
from backend.app.services.integrations.github import GitHubConnector
from backend.app.services.integrations.jira import JiraConnector
from backend.app.services.integrations.pagerduty import PagerDutyConnector
from backend.app.services.integrations.slack import SlackConnector
from backend.app.services.integrations.webhook import WebhookConnector


PROVIDER_MAP = {
    IntegrationProvider.SLACK.value: SlackConnector,
    IntegrationProvider.PAGERDUTY.value: PagerDutyConnector,
    IntegrationProvider.GITHUB.value: GitHubConnector,
    IntegrationProvider.JIRA.value: JiraConnector,
    IntegrationProvider.WEBHOOK.value: WebhookConnector,
}


class IntegrationDispatcher:
    """Manages connector instantiations and asynchronous fan-out event dispatching."""

    @staticmethod
    def get_connector(provider: str, config: Dict[str, Any]) -> BaseIntegrationConnector:
        connector_cls = PROVIDER_MAP.get(provider.lower())
        if not connector_cls:
            raise ValueError(f"Unsupported integration provider: '{provider}'")
        return connector_cls(config)

    @classmethod
    async def dispatch_event(
        cls,
        organization_id: str,
        event_type: str,
        data: Dict[str, Any],
        db: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """
        Broadcasts a domain event to all enabled integration connectors for the organization.
        """
        stmt = select(IntegrationConfig).where(
            IntegrationConfig.organization_id == organization_id,
            IntegrationConfig.is_enabled == True,
        )
        result = await db.execute(stmt)
        configs = result.scalars().all()

        delivery_results = []
        for cfg in configs:
            try:
                subscribed_events = json.loads(cfg.events_subscribed) if cfg.events_subscribed else []
            except Exception:
                subscribed_events = []

            # Check if this connector subscribes to this event
            if event_type not in subscribed_events and "*" not in subscribed_events:
                continue

            try:
                config_dict = json.loads(cfg.config_json) if cfg.config_json else {}
                connector = cls.get_connector(cfg.provider, config_dict)
                outcome = await connector.send_alert(event_type, data)
                outcome["connector_id"] = cfg.id
                outcome["connector_name"] = cfg.name
                delivery_results.append(outcome)
            except Exception as e:
                logger.error(f"Failed to dispatch event '{event_type}' to connector '{cfg.name}' ({cfg.provider}): {e}")
                delivery_results.append({
                    "connector_id": cfg.id,
                    "connector_name": cfg.name,
                    "provider": cfg.provider,
                    "status": "failed",
                    "error": str(e),
                })

        return delivery_results


integration_dispatcher = IntegrationDispatcher()
