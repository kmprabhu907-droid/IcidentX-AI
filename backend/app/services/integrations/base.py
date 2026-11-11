"""
INCIDENTX AI - Enterprise Base Integration Connector (Stage 6.4)
Defines the standard abstract contract for all enterprise notification and ticketing providers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseIntegrationConnector(ABC):
    """Abstract Base Class for third-party enterprise integrations."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def format_alert_payload(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Formats internal domain event data into the provider's specific API payload structure."""
        pass

    @abstractmethod
    async def send_alert(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches an alert or notification to the third-party provider."""
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Validates credential configuration, webhook endpoint reachability, or API token validity."""
        pass
