"""
INCIDENTX AI - Prometheus Integration Client (Phase 8.3)
Provides asynchronous, resilient HTTP communication with Prometheus API v1.
Implements instant/range queries, health verification, and connection safety.
"""

import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import httpx

from backend.app.core.config import settings
from backend.app.infrastructure.core.infrastructure_models import (
    PrometheusHealthStatus,
    PrometheusMetricMetadata,
    PrometheusMetricSeries,
    PrometheusQueryResult,
)


class PrometheusClient:
    """
    Asynchronous client for interacting with Prometheus HTTP API v1.
    Provides connection pooling, timeout resilience, structured result parsing,
    and honest status reporting when the external server is unreachable.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        bearer_token: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        enabled: Optional[bool] = None,
    ):
        self.base_url = (base_url or settings.PROMETHEUS_URL).rstrip("/")
        self.bearer_token = bearer_token if bearer_token is not None else settings.PROMETHEUS_BEARER_TOKEN
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.PROMETHEUS_TIMEOUT_SECONDS
        self.enabled = enabled if enabled is not None else settings.PROMETHEUS_ENABLED
        self._mock_sandbox_handler: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None

    def set_mock_sandbox_handler(self, handler: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]]) -> None:
        """Inject a deterministic sandbox handler for integration tests."""
        self._mock_sandbox_handler = handler

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    async def check_health(self) -> PrometheusHealthStatus:
        """
        Verify connectivity and measuring response latency to Prometheus /-/healthy.
        Never fabricates health; if connection fails, returns UNAVAILABLE.
        """
        if not self.enabled:
            return PrometheusHealthStatus(
                status="NOT_CONFIGURED",
                endpoint=self.base_url,
                latency_ms=0.0,
                error_message="Prometheus integration is disabled in system configuration.",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )

        if self._mock_sandbox_handler:
            return PrometheusHealthStatus(
                status="AVAILABLE",
                endpoint=self.base_url,
                latency_ms=1.2,
                version="v2.51.0 (sandbox)",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )

        start_t = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(f"{self.base_url}/-/healthy", headers=self._get_headers())
                latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
                if resp.status_code == 200:
                    # Attempt to fetch version metadata
                    version = None
                    try:
                        v_resp = await client.get(f"{self.base_url}/api/v1/status/buildinfo", headers=self._get_headers())
                        if v_resp.status_code == 200:
                            v_data = v_resp.json()
                            version = v_data.get("data", {}).get("version")
                    except Exception:
                        pass

                    return PrometheusHealthStatus(
                        status="AVAILABLE",
                        endpoint=self.base_url,
                        latency_ms=latency_ms,
                        version=version or "v2.x",
                        checked_at=datetime.now(timezone.utc).isoformat(),
                    )
                else:
                    return PrometheusHealthStatus(
                        status="ERROR",
                        endpoint=self.base_url,
                        latency_ms=latency_ms,
                        error_message=f"Prometheus returned HTTP status {resp.status_code}",
                        checked_at=datetime.now(timezone.utc).isoformat(),
                    )
        except httpx.ConnectError as e:
            latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            return PrometheusHealthStatus(
                status="UNAVAILABLE",
                endpoint=self.base_url,
                latency_ms=latency_ms,
                error_message=f"Connection refused at {self.base_url}: {str(e)}",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        except httpx.TimeoutException:
            latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            return PrometheusHealthStatus(
                status="UNAVAILABLE",
                endpoint=self.base_url,
                latency_ms=latency_ms,
                error_message=f"Request to {self.base_url} timed out after {self.timeout_seconds}s",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            return PrometheusHealthStatus(
                status="ERROR",
                endpoint=self.base_url,
                latency_ms=latency_ms,
                error_message=str(e),
                checked_at=datetime.now(timezone.utc).isoformat(),
            )

    async def query(self, promql: str, time_param: Optional[str] = None) -> PrometheusQueryResult:
        """
        Execute an instant PromQL query against Prometheus /api/v1/query.
        """
        if not self.enabled:
            return PrometheusQueryResult(
                status="UNAVAILABLE",
                query=promql,
                error_message="Prometheus integration is disabled in configuration.",
            )

        if self._mock_sandbox_handler:
            mock_resp = self._mock_sandbox_handler("query", {"query": promql, "time": time_param})
            return self._parse_prometheus_response(promql, mock_resp)

        params: Dict[str, Any] = {"query": promql}
        if time_param:
            params["time"] = time_param

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/query",
                    params=params,
                    headers=self._get_headers(),
                )
                if resp.status_code != 200:
                    return PrometheusQueryResult(
                        status="ERROR",
                        query=promql,
                        error_message=f"Prometheus API HTTP {resp.status_code}: {resp.text}",
                    )
                return self._parse_prometheus_response(promql, resp.json())
        except httpx.ConnectError as e:
            return PrometheusQueryResult(
                status="UNAVAILABLE",
                query=promql,
                error_message=f"Unable to connect to Prometheus server at {self.base_url}: {str(e)}",
            )
        except httpx.TimeoutException:
            return PrometheusQueryResult(
                status="UNAVAILABLE",
                query=promql,
                error_message=f"Prometheus query timed out after {self.timeout_seconds} seconds.",
            )
        except Exception as e:
            return PrometheusQueryResult(
                status="ERROR",
                query=promql,
                error_message=f"Unexpected error executing PromQL query: {str(e)}",
            )

    async def query_range(
        self,
        promql: str,
        start: str,
        end: str,
        step: str = "15s",
    ) -> PrometheusQueryResult:
        """
        Execute a range PromQL query against Prometheus /api/v1/query_range.
        """
        if not self.enabled:
            return PrometheusQueryResult(
                status="UNAVAILABLE",
                query=promql,
                error_message="Prometheus integration is disabled in configuration.",
            )

        if self._mock_sandbox_handler:
            mock_resp = self._mock_sandbox_handler("query_range", {"query": promql, "start": start, "end": end, "step": step})
            return self._parse_prometheus_response(promql, mock_resp)

        params = {
            "query": promql,
            "start": start,
            "end": end,
            "step": step,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/query_range",
                    params=params,
                    headers=self._get_headers(),
                )
                if resp.status_code != 200:
                    return PrometheusQueryResult(
                        status="ERROR",
                        query=promql,
                        error_message=f"Prometheus API HTTP {resp.status_code}: {resp.text}",
                    )
                return self._parse_prometheus_response(promql, resp.json())
        except httpx.ConnectError as e:
            return PrometheusQueryResult(
                status="UNAVAILABLE",
                query=promql,
                error_message=f"Unable to connect to Prometheus server at {self.base_url}: {str(e)}",
            )
        except httpx.TimeoutException:
            return PrometheusQueryResult(
                status="UNAVAILABLE",
                query=promql,
                error_message=f"Prometheus range query timed out after {self.timeout_seconds}s.",
            )
        except Exception as e:
            return PrometheusQueryResult(
                status="ERROR",
                query=promql,
                error_message=f"Unexpected error querying Prometheus range: {str(e)}",
            )

    async def get_metadata(self, metric: Optional[str] = None) -> List[PrometheusMetricMetadata]:
        """
        Fetch metric metadata definitions from Prometheus /api/v1/metadata.
        """
        if not self.enabled:
            return []

        if self._mock_sandbox_handler:
            raw = self._mock_sandbox_handler("metadata", {"metric": metric})
            return [
                PrometheusMetricMetadata(
                    metric=m.get("metric", ""),
                    type=m.get("type", "gauge"),
                    help=m.get("help", ""),
                    unit=m.get("unit", ""),
                )
                for m in raw.get("data", [])
            ]

        params = {"metric": metric} if metric else {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/metadata",
                    params=params,
                    headers=self._get_headers(),
                )
                if resp.status_code != 200:
                    return []
                data = resp.json().get("data", {})
                result: List[PrometheusMetricMetadata] = []
                for m_name, items in data.items():
                    for item in items:
                        result.append(
                            PrometheusMetricMetadata(
                                metric=m_name,
                                type=item.get("type", "gauge"),
                                help=item.get("help", ""),
                                unit=item.get("unit", ""),
                            )
                        )
                return result
        except Exception:
            return []

    def _parse_prometheus_response(self, promql: str, data: Dict[str, Any]) -> PrometheusQueryResult:
        """
        Convert Prometheus API JSON envelope into typed PrometheusQueryResult.
        """
        status_field = data.get("status")
        if status_field != "success":
            return PrometheusQueryResult(
                status="ERROR",
                query=promql,
                error_message=data.get("error", "Unknown Prometheus error response"),
            )

        payload = data.get("data", {})
        result_type = payload.get("resultType", "vector")
        results = payload.get("result", [])

        if not results:
            return PrometheusQueryResult(
                status="EMPTY",
                query=promql,
                result_type=result_type,
                series=[],
            )

        series_list: List[PrometheusMetricSeries] = []

        for item in results:
            metric_labels = item.get("metric", {})
            metric_name = metric_labels.get("__name__", "unnamed_metric")

            # In vector result, "value" is [timestamp, "value_str"]
            # In matrix result, "values" is [[timestamp, "value_str"], ...]
            if result_type == "vector":
                raw_val = item.get("value", [])
                parsed_val = None
                values_list = []
                if len(raw_val) >= 2:
                    try:
                        parsed_val = float(raw_val[1])
                        values_list.append([raw_val[0], parsed_val])
                    except (ValueError, TypeError):
                        pass

                series_list.append(
                    PrometheusMetricSeries(
                        metric_name=metric_name,
                        labels=metric_labels,
                        values=values_list,
                        latest_value=parsed_val,
                    )
                )

            elif result_type == "matrix":
                raw_values = item.get("values", [])
                parsed_values = []
                latest_val = None
                for point in raw_values:
                    if len(point) >= 2:
                        try:
                            val_float = float(point[1])
                            parsed_values.append([point[0], val_float])
                            latest_val = val_float
                        except (ValueError, TypeError):
                            continue

                series_list.append(
                    PrometheusMetricSeries(
                        metric_name=metric_name,
                        labels=metric_labels,
                        values=parsed_values,
                        latest_value=latest_val,
                    )
                )

        return PrometheusQueryResult(
            status="SUCCESS",
            query=promql,
            result_type=result_type,
            series=series_list,
        )


# Global singleton instance
prometheus_client = PrometheusClient()
