"""
INCIDENTX AI - Grafana Integration Client (Phase 8.3)
Interacts with Grafana REST APIs:
- Discovers dashboards via /api/search
- Generates incident-specific deep links with time bounds and template variables
- Posts lifecycle annotations to dashboards without exposing API tokens to the client
"""

import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlencode
import httpx

from backend.app.core.config import settings
from backend.app.infrastructure.core.infrastructure_models import (
    GrafanaAnnotation,
    GrafanaDashboardInfo,
)


class GrafanaClient:
    """
    Client for interacting with Grafana REST API.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        enabled: Optional[bool] = None,
        timeout_seconds: float = 5.0,
    ):
        self.base_url = (base_url or settings.GRAFANA_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.GRAFANA_API_KEY
        self.enabled = enabled if enabled is not None else settings.GRAFANA_ENABLED
        self.timeout_seconds = timeout_seconds
        self._mock_sandbox_handler: Optional[Callable[[str, Dict[str, Any]], Any]] = None

    def set_mock_sandbox_handler(self, handler: Optional[Callable[[str, Dict[str, Any]], Any]]) -> None:
        self._mock_sandbox_handler = handler

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def check_health(self) -> Dict[str, Any]:
        """Verify connectivity to Grafana /api/health."""
        if not self.enabled:
            return {
                "status": "NOT_CONFIGURED",
                "endpoint": self.base_url,
                "latency_ms": 0.0,
                "version": None,
                "error_message": "Grafana integration is disabled in configuration.",
            }

        if self._mock_sandbox_handler:
            return {
                "status": "AVAILABLE",
                "endpoint": self.base_url,
                "latency_ms": 2.1,
                "version": "10.4.0 (sandbox)",
                "error_message": None,
            }

        start_t = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(f"{self.base_url}/api/health", headers=self._get_headers())
                latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "status": "AVAILABLE",
                        "endpoint": self.base_url,
                        "latency_ms": latency_ms,
                        "version": data.get("version", "10.x"),
                        "database": data.get("database", "ok"),
                        "error_message": None,
                    }
                else:
                    return {
                        "status": "ERROR",
                        "endpoint": self.base_url,
                        "latency_ms": latency_ms,
                        "version": None,
                        "error_message": f"Grafana returned HTTP {resp.status_code}",
                    }
        except httpx.ConnectError as e:
            latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            return {
                "status": "UNAVAILABLE",
                "endpoint": self.base_url,
                "latency_ms": latency_ms,
                "version": None,
                "error_message": f"Connection refused at {self.base_url}: {str(e)}",
            }
        except httpx.TimeoutException:
            latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            return {
                "status": "UNAVAILABLE",
                "endpoint": self.base_url,
                "latency_ms": latency_ms,
                "version": None,
                "error_message": f"Request to {self.base_url} timed out after {self.timeout_seconds}s",
            }
        except Exception as e:
            latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            return {
                "status": "ERROR",
                "endpoint": self.base_url,
                "latency_ms": latency_ms,
                "version": None,
                "error_message": str(e),
            }

    async def search_dashboards(self, query: str = "") -> List[GrafanaDashboardInfo]:
        """Search Grafana dashboards via /api/search."""
        if not self.enabled:
            return []

        if self._mock_sandbox_handler:
            raw = self._mock_sandbox_handler("search_dashboards", {"query": query})
            return [GrafanaDashboardInfo(**item) for item in raw]

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                params = {"type": "dash-db"}
                if query:
                    params["query"] = query
                resp = await client.get(
                    f"{self.base_url}/api/search",
                    params=params,
                    headers=self._get_headers(),
                )
                if resp.status_code != 200:
                    return []
                dashboards = resp.json()
                return [
                    GrafanaDashboardInfo(
                        uid=d.get("uid", ""),
                        title=d.get("title", ""),
                        url=f"{self.base_url}{d.get('url', '')}",
                        tags=d.get("tags", []),
                        type=d.get("type", "dash-db"),
                        is_starred=d.get("isStarred", False),
                    )
                    for d in dashboards
                ]
        except Exception:
            return []

    def generate_incident_deep_link(
        self,
        dashboard_uid: Optional[str] = None,
        from_time_ms: Optional[int] = None,
        to_time_ms: Optional[int] = None,
        namespace: Optional[str] = None,
        service: Optional[str] = None,
        incident_id: Optional[str] = None,
    ) -> str:
        """
        Build deep link to Grafana dashboard with time window and template variables.
        Never embeds authorization secrets in the generated URL.
        """
        uid = dashboard_uid or getattr(settings, "GRAFANA_DEFAULT_DASHBOARD_UID", "incidentx-overview")
        now_ms = int(time.time() * 1000)
        from_ms = from_time_ms or (now_ms - 3600 * 1000)  # Default 1h lookback
        to_ms = to_time_ms or now_ms

        params: Dict[str, Any] = {
            "from": from_ms,
            "to": to_ms,
        }
        if namespace:
            params["var-namespace"] = namespace
        if service:
            params["var-service"] = service
        if incident_id:
            params["var-incident"] = incident_id

        query_str = urlencode(params)
        return f"{self.base_url}/d/{uid}/incident-view?{query_str}"

    async def create_annotation(
        self,
        text: str,
        tags: Optional[List[str]] = None,
        dashboard_uid: Optional[str] = None,
        time_ms: Optional[int] = None,
        time_end_ms: Optional[int] = None,
    ) -> Optional[GrafanaAnnotation]:
        """
        Post annotation to Grafana /api/annotations.
        """
        if not self.enabled:
            return None

        t_ms = time_ms or int(time.time() * 1000)
        annotation_tags = list(tags or [])
        if "incidentx" not in annotation_tags:
            annotation_tags.append("incidentx")

        payload: Dict[str, Any] = {
            "text": text,
            "tags": annotation_tags,
            "time": t_ms,
        }
        if time_end_ms:
            payload["timeEnd"] = time_end_ms
        if dashboard_uid:
            payload["dashboardUID"] = dashboard_uid

        if self._mock_sandbox_handler:
            mock_res = self._mock_sandbox_handler("create_annotation", payload)
            return GrafanaAnnotation(
                id=mock_res.get("id", 1),
                dashboard_uid=dashboard_uid,
                time_ms=t_ms,
                time_end_ms=time_end_ms,
                tags=annotation_tags,
                text=text,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(
                    f"{self.base_url}/api/annotations",
                    json=payload,
                    headers=self._get_headers(),
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return GrafanaAnnotation(
                        id=data.get("id"),
                        dashboard_uid=dashboard_uid,
                        time_ms=t_ms,
                        time_end_ms=time_end_ms,
                        tags=annotation_tags,
                        text=text,
                        created_at=datetime.now(timezone.utc).isoformat(),
                    )
                return None
        except Exception:
            return None


# Global singleton instance
grafana_client = GrafanaClient()
