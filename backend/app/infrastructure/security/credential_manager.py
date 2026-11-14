"""
INCIDENTX AI - Credential Manager (Phase 8.1)
Safely handles, resolves, and isolates read-only observability credentials from
restricted remediation credentials. Prevents credential leakage into logs and AI prompts.
"""

import os
from typing import Dict, Optional
from pydantic import BaseModel, Field


class ClusterCredentials(BaseModel):
    cluster_id: str
    cluster_name: str
    api_server_url: str
    read_only_token: str = Field(..., description="Read-only Bearer token for observability")
    remediation_token: Optional[str] = Field(
        default=None, description="Restricted Bearer token for remediation"
    )
    ca_cert_data: Optional[str] = None
    namespace: str = "default"

    def get_masked_read_token(self) -> str:
        if not self.read_only_token:
            return ""
        if len(self.read_only_token) <= 8:
            return "***"
        return f"{self.read_only_token[:4]}...{self.read_only_token[-4:]}"

    def get_masked_remediation_token(self) -> str:
        if not self.remediation_token:
            return "NONE"
        if len(self.remediation_token) <= 8:
            return "***"
        return f"{self.remediation_token[:4]}...{self.remediation_token[-4:]}"

    def __str__(self) -> str:
        return (
            f"ClusterCredentials(cluster_id='{self.cluster_id}', "
            f"cluster_name='{self.cluster_name}', "
            f"api_server_url='{self.api_server_url}', "
            f"read_only_token='{self.get_masked_read_token()}', "
            f"remediation_token='{self.get_masked_remediation_token()}', "
            f"namespace='{self.namespace}')"
        )

    def __repr__(self) -> str:
        return self.__str__()


KubernetesCredentials = ClusterCredentials


class CredentialManager:
    """Centralized credential resolution for Kubernetes clusters."""

    _credentials_store: Dict[str, ClusterCredentials] = {}

    @classmethod
    def register_cluster_credentials(cls, creds: ClusterCredentials) -> None:
        """Stores credentials securely in memory."""
        cls._credentials_store[creds.cluster_id] = creds

    @classmethod
    def get_credentials(cls, cluster_id: str) -> Optional[ClusterCredentials]:
        """Resolves credentials by cluster ID."""
        # 1. Check in-memory store
        if cluster_id in cls._credentials_store:
            return cls._credentials_store[cluster_id]

        # 2. Check environment variable defaults
        env_url = os.getenv("KUBERNETES_API_URL", "https://127.0.0.1:6443")
        env_ro_token = os.getenv("KUBERNETES_READ_ONLY_TOKEN", "")
        env_rem_token = os.getenv("KUBERNETES_REMEDIATION_TOKEN", "")

        if env_ro_token:
            creds = ClusterCredentials(
                cluster_id=cluster_id,
                cluster_name=os.getenv("KUBERNETES_CLUSTER_NAME", "k8s-default"),
                api_server_url=env_url,
                read_only_token=env_ro_token,
                remediation_token=env_rem_token or None,
                namespace=os.getenv("KUBERNETES_NAMESPACE", "default"),
            )
            cls._credentials_store[cluster_id] = creds
            return creds

        return None

    @classmethod
    def clear(cls) -> None:
        """Clears stored credentials."""
        cls._credentials_store.clear()
