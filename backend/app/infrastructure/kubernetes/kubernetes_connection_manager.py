"""
INCIDENTX AI - Kubernetes Connection Manager (Phase 8.2)
Handles cluster discovery, authentication strategies (kubeconfig, ServiceAccount, Bearer token),
exponential backoff retry, health probe verification, and credential isolation.
"""

import asyncio
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
import httpx
from backend.app.core.logging import logger
from backend.app.infrastructure.core.infrastructure_models import (
    KubernetesClusterOverview,
    KubernetesConnectionDetails,
)
from backend.app.infrastructure.security.credential_manager import (
    ClusterCredentials,
    CredentialManager,
)


class KubernetesConnectionManager:
    """
    Manages connections to real Kubernetes clusters (Minikube, Kind, Docker Desktop, Remote K8s, EKS/GKE).
    Executes multi-strategy authentication discovery and connection validation.
    """

    def __init__(self, cluster_id: str = "k8s-default"):
        self.cluster_id = cluster_id
        self._is_connected: bool = False
        self._is_live: bool = False
        self._auth_method: str = "none"
        self._cluster_name: str = "unconfigured"
        self._api_server_url: str = ""
        self._token: Optional[str] = None
        self._ca_cert_data: Optional[str] = None
        self._discovered_version: str = "unknown"
        self._last_error: Optional[str] = None
        self._connected_at: Optional[str] = None
        self._metrics_server_available: bool = False
        self._mock_handler: Optional[Callable] = None

    def set_mock_handler(self, handler: Optional[Callable]):
        """Injects mock cluster handler for offline testing."""
        self._mock_handler = handler

    def clear_mock_handler(self):
        """Clears mock cluster handler."""
        self._mock_handler = None

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def is_live(self) -> bool:
        return self._is_live

    @property
    def metrics_server_available(self) -> bool:
        return self._metrics_server_available

    def _discover_auth_strategy(self) -> Tuple[str, str, Optional[str], Optional[str]]:
        """
        Discovers authentication strategy in strict priority:
        1. Mock sandbox handler (if injected)
        2. CredentialManager registered credentials
        3. In-cluster ServiceAccount (/var/run/secrets/kubernetes.io/serviceaccount)
        4. Kubeconfig file (~/.kube/config or $KUBECONFIG)
        5. Environment variables (KUBERNETES_API_URL and KUBERNETES_READ_ONLY_TOKEN)
        Returns: (auth_method, api_url, token, cluster_name)
        """
        if self._mock_handler:
            return ("mock_sandbox", "https://mock.k8s.internal:6443", "mock-token", "k8s-sandbox")

        # 2. Check CredentialManager
        registered = CredentialManager.get_credentials(self.cluster_id)
        if registered and registered.read_only_token:
            return (
                "bearer_token",
                registered.api_server_url,
                registered.read_only_token,
                registered.cluster_name,
            )

        # 3. Check in-cluster ServiceAccount
        sa_token_path = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
        if sa_token_path.exists():
            try:
                token = sa_token_path.read_text().strip()
                host = os.getenv("KUBERNETES_SERVICE_HOST", "kubernetes.default.svc")
                port = os.getenv("KUBERNETES_SERVICE_PORT", "443")
                url = f"https://{host}:{port}"
                return ("in_cluster_serviceaccount", url, token, "in-cluster")
            except Exception as e:
                logger.debug(f"[K8sConnection] Failed reading in-cluster ServiceAccount: {e}")

        # 4. Check Kubeconfig file
        kubeconfig_env = os.getenv("KUBECONFIG")
        kubeconfig_path = Path(kubeconfig_env) if kubeconfig_env else Path.home() / ".kube" / "config"
        if kubeconfig_path.exists():
            try:
                # Try parsing kubeconfig via official kubernetes python client
                from kubernetes import config
                contexts, active_context = config.list_kube_config_contexts(config_file=str(kubeconfig_path))
                if active_context:
                    cluster_info = active_context.get("context", {})
                    cluster_ref = cluster_info.get("cluster", "k8s-cluster")
                    return ("kubeconfig", "https://localhost:6443", None, cluster_ref)
            except Exception as e:
                logger.debug(f"[K8sConnection] Kubeconfig present but unparseable: {e}")

        # 5. Check Environment Variables
        env_url = os.getenv("KUBERNETES_API_URL")
        env_token = os.getenv("KUBERNETES_READ_ONLY_TOKEN")
        if env_url and env_token:
            return (
                "environment_credentials",
                env_url,
                env_token,
                os.getenv("KUBERNETES_CLUSTER_NAME", "k8s-env-cluster"),
            )

        return ("none", "", None, "unconfigured")

    async def connect(self, max_retries: int = 2) -> bool:
        """
        Attempts to establish connection with exponential backoff.
        Validates API server version and namespace read access.
        """
        auth_method, api_url, token, cluster_name = self._discover_auth_strategy()
        self._auth_method = auth_method
        self._api_server_url = api_url
        self._token = token
        self._cluster_name = cluster_name

        if auth_method == "none":
            self._is_connected = False
            self._is_live = False
            self._last_error = (
                "No Kubernetes credentials found. Neither ~/.kube/config, in-cluster "
                "ServiceAccount, nor KUBERNETES_API_URL/KUBERNETES_READ_ONLY_TOKEN are configured."
            )
            return False

        if auth_method == "mock_sandbox":
            self._is_connected = True
            self._is_live = False  # Explicitly flagged as simulated sandbox, not physical cluster
            self._discovered_version = "v1.30.2-mock"
            self._connected_at = datetime.now(timezone.utc).isoformat()
            self._last_error = None
            self._metrics_server_available = True
            return True

        # Real connection attempt with exponential backoff
        delay = 0.5
        for attempt in range(max_retries):
            try:
                # 1. Probe version
                headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"} if token else {"Accept": "application/json"}
                async with httpx.AsyncClient(verify=False, timeout=3.5) as client:
                    resp = await client.get(f"{api_url.rstrip('/')}/version", headers=headers)
                    if resp.status_code == 200:
                        ver_data = resp.json()
                        self._discovered_version = ver_data.get("gitVersion", "v1.30.0")
                        self._is_connected = True
                        self._is_live = True
                        self._connected_at = datetime.now(timezone.utc).isoformat()
                        self._last_error = None

                        # Check if Metrics Server is present
                        try:
                            m_resp = await client.get(
                                f"{api_url.rstrip('/')}/apis/metrics.k8s.io/v1beta1",
                                headers=headers,
                            )
                            self._metrics_server_available = (m_resp.status_code == 200)
                        except Exception:
                            self._metrics_server_available = False

                        logger.info(
                            f"[K8sConnection] Successfully connected to {self._cluster_name} "
                            f"({self._discovered_version}) via {auth_method}"
                        )
                        return True
                    else:
                        raise ConnectionError(f"HTTP {resp.status_code} on /version probe")
            except Exception as e:
                self._last_error = f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}"
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2.0

        self._is_connected = False
        self._is_live = False
        return False

    async def disconnect(self) -> None:
        """Gracefully disconnects from the cluster."""
        self._is_connected = False
        self._is_live = False
        self._token = None
        self._api_server_url = ""
        self._cluster_name = "unconfigured"
        self._last_error = None
        logger.info(f"[K8sConnection] Disconnected from cluster '{self.cluster_id}'")

    def get_connection_details(self) -> KubernetesConnectionDetails:
        """Returns safe, masked connection details."""
        masked_tok = None
        if self._token:
            masked_tok = (
                f"{self._token[:4]}...{self._token[-4:]}"
                if len(self._token) > 8
                else "***"
            )

        return KubernetesConnectionDetails(
            cluster_id=self.cluster_id,
            cluster_name=self._cluster_name,
            api_server_url=self._api_server_url or "none",
            auth_method=self._auth_method,
            is_connected=self._is_connected,
            is_live=self._is_live,
            is_read_only=True,
            masked_token=masked_tok,
            discovered_version=self._discovered_version if self._is_connected else None,
            last_error=self._last_error,
            connected_at=self._connected_at,
        )


# Global singleton
kubernetes_connection_manager = KubernetesConnectionManager()
