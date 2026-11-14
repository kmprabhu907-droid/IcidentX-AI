"""
INCIDENTX AI - Base Infrastructure Adapter (Phase 8.1)
Abstract Interface providing standardized infrastructure operations across DemoMesh and Kubernetes.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from backend.app.infrastructure.core.infrastructure_models import (
    EnvironmentHealth,
    EnvironmentMetadata,
    EnvironmentMode,
    InfrastructureEvent,
    InfrastructureService,
    InfrastructureWorkload,
    ResourceMetric,
    WorkloadStatus,
)


class BaseInfrastructureAdapter(ABC):
    """
    Abstract Base Class for Infrastructure Adapters.
    Exposes unified operational methods for DemoMesh and Kubernetes engines.
    """

    @property
    @abstractmethod
    def mode(self) -> EnvironmentMode:
        """Returns the EnvironmentMode supported by this adapter."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if the adapter is currently connected and operational."""
        pass

    @property
    @abstractmethod
    def is_read_only(self) -> bool:
        """Returns True if the adapter only supports read-only operations."""
        pass

    @property
    @abstractmethod
    def data_source(self) -> str:
        """Returns the data source tag ('SIMULATED' vs 'LIVE_K8S')."""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """Establishes connection to the infrastructure engine."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Safely terminates connection and cleans up sessions."""
        pass

    @abstractmethod
    async def health_check(self) -> EnvironmentHealth:
        """Performs live connectivity and health probe."""
        pass

    @abstractmethod
    async def list_services(self) -> List[InfrastructureService]:
        """Discovers and returns all registered microservices."""
        pass

    @abstractmethod
    async def list_workloads(self, namespace: Optional[str] = None) -> List[InfrastructureWorkload]:
        """Discovers workloads (Pods, Deployments, or Simulated Containers)."""
        pass

    @abstractmethod
    async def get_workload_status(
        self, workload_id: str, namespace: Optional[str] = None
    ) -> Optional[WorkloadStatus]:
        """Retrieves real-time status, phase, and conditions for a specific workload."""
        pass

    @abstractmethod
    async def get_events(
        self, limit: int = 50, namespace: Optional[str] = None
    ) -> List[InfrastructureEvent]:
        """Retrieves recent cluster/mesh warning and normal events."""
        pass

    @abstractmethod
    async def get_resource_metrics(
        self, workload_id: Optional[str] = None
    ) -> List[ResourceMetric]:
        """Fetches current CPU, memory, and performance metrics."""
        pass

    @abstractmethod
    async def get_environment_metadata(self) -> EnvironmentMetadata:
        """Returns standardized environment information, cluster version, and status."""
        pass
