"""
INCIDENTX AI - Kubernetes API Client Wrapper (Phase 8.1)
Connects to official Kubernetes API server using in-cluster ServiceAccount,
kubeconfig, or explicit Bearer tokens. Supports high-fidelity mock injection for sandboxes.
"""

import asyncio
from datetime import datetime, timezone
import os
from typing import Any, Callable, Dict, List, Optional
import httpx
from backend.app.core.logging import logger
from backend.app.infrastructure.security.credential_manager import ClusterCredentials, CredentialManager


class KubernetesClient:
    """Official/REST-compatible Kubernetes API client with read-only enforcement."""

    def __init__(
        self,
        cluster_id: str = "k8s-default",
        namespace: str = "default",
        custom_creds: Optional[ClusterCredentials] = None,
    ):
        self.cluster_id = cluster_id
        self.namespace = namespace
        self._custom_creds = custom_creds
        self._mock_handler: Optional[Callable] = None

    def set_mock_handler(self, handler: Optional[Callable]):
        """Injects mock cluster handler for offline sandbox/unit tests."""
        self._mock_handler = handler

    def clear_mock_handler(self) -> None:
        """Clears injected mock handler."""
        self._mock_handler = None

    def _resolve_credentials(self) -> Optional[ClusterCredentials]:
        if self._custom_creds:
            return self._custom_creds
        registered = CredentialManager.get_credentials(self.cluster_id)
        if registered:
            return registered

        from backend.app.infrastructure.kubernetes.kubernetes_connection_manager import (
            kubernetes_connection_manager,
        )
        if kubernetes_connection_manager._token and kubernetes_connection_manager._api_server_url:
            return ClusterCredentials(
                cluster_id=self.cluster_id,
                cluster_name=kubernetes_connection_manager._cluster_name,
                api_server_url=kubernetes_connection_manager._api_server_url,
                read_only_token=kubernetes_connection_manager._token,
                namespace=self.namespace,
            )
        return None

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dispatches an authenticated GET request to Kubernetes API server."""
        # Check mock sandbox handler first
        if self._mock_handler:
            import inspect
            try:
                sig = inspect.signature(self._mock_handler)
                if len(sig.parameters) == 1:
                    return self._mock_handler(path)
            except Exception:
                pass
            return self._mock_handler("GET", path, params or {})

        creds = self._resolve_credentials()
        if not creds:
            raise ConnectionError(
                f"Kubernetes cluster credentials for '{self.cluster_id}' are not configured. "
                "Set KUBERNETES_API_URL and KUBERNETES_READ_ONLY_TOKEN, or register cluster via API."
            )

        base_url = creds.api_server_url.rstrip("/")
        url = f"{base_url}{path}"
        headers = {
            "Authorization": f"Bearer {creds.read_only_token}",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to Kubernetes API server at {base_url}: {e}")
        except httpx.HTTPStatusError as e:
            raise ConnectionError(f"Kubernetes API returned HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise ConnectionError(f"Kubernetes API request failed: {e}")

    async def get_version(self) -> Dict[str, Any]:
        """Queries /version endpoint."""
        return await self.get("/version")

    async def list_namespaces(self) -> List[str]:
        """Queries /api/v1/namespaces."""
        data = await self.get("/api/v1/namespaces")
        items = data.get("items", [])
        return [item.get("metadata", {}).get("name", "default") for item in items]

    async def list_services(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """Queries /api/v1/services or namespaced services."""
        ns = namespace or (self.namespace if self.namespace != "default" else None)
        path = f"/api/v1/namespaces/{ns}/services" if ns else "/api/v1/services"
        data = await self.get(path)
        return data.get("items", [])

    async def list_pods(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """Queries /api/v1/pods or namespaced pods."""
        ns = namespace or (self.namespace if self.namespace != "default" else None)
        path = f"/api/v1/namespaces/{ns}/pods" if ns else "/api/v1/pods"
        data = await self.get(path)
        return data.get("items", [])

    async def list_deployments(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """Queries /apis/apps/v1/deployments."""
        ns = namespace or (self.namespace if self.namespace != "default" else None)
        path = f"/apis/apps/v1/namespaces/{ns}/deployments" if ns else "/apis/apps/v1/deployments"
        data = await self.get(path)
        return data.get("items", [])

    async def list_events(self, namespace: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Queries /api/v1/events."""
        ns = namespace or (self.namespace if self.namespace != "default" else None)
        path = f"/api/v1/namespaces/{ns}/events" if ns else "/api/v1/events"
        data = await self.get(path, params={"limit": limit})
        return data.get("items", [])

    async def list_nodes(self) -> List[Dict[str, Any]]:
        """Queries /api/v1/nodes."""
        data = await self.get("/api/v1/nodes")
        return data.get("items", [])

    async def list_namespaces_detailed(self) -> List[Dict[str, Any]]:
        """Queries /api/v1/namespaces returning full namespace item metadata."""
        data = await self.get("/api/v1/namespaces")
        return data.get("items", [])

    async def list_endpoints(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """Queries /api/v1/endpoints."""
        ns = namespace or (self.namespace if self.namespace != "default" else None)
        path = f"/api/v1/namespaces/{ns}/endpoints" if ns else "/api/v1/endpoints"
        data = await self.get(path)
        return data.get("items", [])

    async def get_node_metrics(self) -> List[Dict[str, Any]]:
        """Queries /apis/metrics.k8s.io/v1beta1/nodes. Returns empty list if Metrics Server unavailable."""
        try:
            data = await self.get("/apis/metrics.k8s.io/v1beta1/nodes")
            return data.get("items", [])
        except Exception as e:
            logger.debug(f"[KubernetesClient] Node metrics unavailable: {e}")
            return []

    async def get_pod_metrics(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """Queries /apis/metrics.k8s.io/v1beta1/pods. Returns empty list if Metrics Server unavailable."""
        try:
            ns = namespace or (self.namespace if self.namespace != "default" else None)
            path = f"/apis/metrics.k8s.io/v1beta1/namespaces/{ns}/pods" if ns else "/apis/metrics.k8s.io/v1beta1/pods"
            data = await self.get(path)
            return data.get("items", [])
        except Exception as e:
            logger.debug(f"[KubernetesClient] Pod metrics unavailable: {e}")
            return []
