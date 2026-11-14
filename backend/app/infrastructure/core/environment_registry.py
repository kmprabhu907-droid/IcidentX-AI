"""
INCIDENTX AI - Environment Registry (Phase 8.1)
Maintains registered BaseInfrastructureAdapter implementations for DemoMesh and Kubernetes.
"""

from typing import Dict, List, Optional
from backend.app.infrastructure.core.base_adapter import BaseInfrastructureAdapter
from backend.app.infrastructure.core.infrastructure_models import EnvironmentMode
from backend.app.infrastructure.demomesh.demomesh_adapter import DemoMeshAdapter
from backend.app.infrastructure.kubernetes.kubernetes_adapter import KubernetesAdapter


class EnvironmentRegistry:
    """Registry holding infrastructure adapters."""

    def __init__(self):
        self._adapters: Dict[EnvironmentMode, BaseInfrastructureAdapter] = {
            EnvironmentMode.DEMOMESH: DemoMeshAdapter(),
            EnvironmentMode.KUBERNETES: KubernetesAdapter(),
        }

    def register_adapter(self, mode: EnvironmentMode, adapter: BaseInfrastructureAdapter) -> None:
        """Registers or replaces an infrastructure adapter."""
        self._adapters[mode] = adapter

    def get_adapter(self, mode: EnvironmentMode) -> Optional[BaseInfrastructureAdapter]:
        """Returns the adapter for the requested mode."""
        return self._adapters.get(mode)

    def list_available_modes(self) -> List[EnvironmentMode]:
        """Lists all registered environment modes."""
        return list(self._adapters.keys())


# Singleton instance
environment_registry = EnvironmentRegistry()
