"""
INCIDENTX AI - Telemetry Schemas
Pydantic schemas for the 10 Golden Signals, 1-minute historical rollups, and collector status.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ServiceGoldenSignals(BaseModel):
    service_id: str
    service_name: str
    cpu_utilization: float = Field(..., description="CPU utilization percentage (0-100%)")
    memory_utilization: float = Field(..., description="Memory utilization percentage (0-100%)")
    disk_utilization: float = Field(..., description="Disk utilization percentage (0-100%)")
    network_throughput_mbps: float = Field(..., description="Network throughput in MB/s")
    latency_p50_ms: float = Field(..., description="Median request latency in milliseconds")
    latency_p95_ms: float = Field(..., description="95th percentile request latency in milliseconds")
    latency_p99_ms: float = Field(..., description="99th percentile request latency in milliseconds")
    error_rate: float = Field(..., description="HTTP error rate percentage (0-100%)")
    db_pool_utilization: float = Field(..., description="Database connection-pool utilization percentage (0-100%)")
    availability_pct: float = Field(..., description="Service availability percentage (0-100%)")
    dependency_health: float = Field(..., description="Composite dependency health score (0-100%)")
    request_rate: float = Field(..., description="Request throughput in requests per second (RPS)")
    health_status: str = Field(..., description="Health status (HEALTHY, DEGRADED, CRITICAL)")
    data_source: str = Field(default="SIMULATED", description="Data source attribution (SIMULATED, LIVE, REPLAY)")


class TenGoldenSignalsResponse(BaseModel):
    timestamp: datetime
    data_source: str = Field(default="SIMULATED", description="Data source indicator")
    total_services: int
    services: Dict[str, ServiceGoldenSignals]


class MetricRollupResponse(BaseModel):
    id: str
    service_id: Optional[str] = None
    service_name: str
    metric_name: str
    bucket_start: datetime
    minimum: float
    maximum: float
    average: float
    latest_value: float
    sample_count: int
    data_source: str

    model_config = {"from_attributes": True}


class MetricHistoryResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    data_source: str
    rollups: List[MetricRollupResponse]


class CollectorStatusResponse(BaseModel):
    collector_status: str
    last_collection_time: Optional[str] = None
    last_flush_time: Optional[str] = None
    last_cleanup_time: Optional[str] = None
    next_collection_interval_seconds: int
    monitored_services_count: int
    buffer_stats: Dict[str, Any]
    last_error: Optional[str] = None
