"""
INCIDENTX AI - Continuous Observability Collector
Periodically ingests 10 Golden Reliability Signals from DemoMesh, aggregates
them into 1-minute statistical time-buckets (min, max, avg, latest, sample_count),
persists rollups into the database, and enforces rolling 7-day retention.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import math
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from backend.app.core.database import async_session_factory
from backend.app.core.logging import logger
from backend.app.models.telemetry import MetricRollup
from backend.app.services.observability.demo_mesh import demo_mesh


class MetricBucketAccumulator:
    """Accumulates raw samples within a 1-minute time bucket."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        metric_name: str,
        bucket_start: datetime,
        data_source: str = "SIMULATED",
    ):
        self.service_id = service_id
        self.service_name = service_name
        self.metric_name = metric_name
        self.bucket_start = bucket_start
        self.data_source = data_source
        self.values: List[float] = []

    def add_sample(self, value: Any):
        """Safely appends a numeric sample, skipping None, NaN, and Inf."""
        if value is None:
            return
        try:
            val_f = float(value)
            if math.isnan(val_f) or math.isinf(val_f):
                return
            self.values.append(val_f)
        except (ValueError, TypeError):
            pass

    def compute_summary(self) -> Optional[Dict[str, Any]]:
        """Calculates min, max, average, and latest value for the bucket."""
        if not self.values:
            return None
        return {
            "id": str(uuid.uuid4()),
            "service_id": self.service_id,
            "service_name": self.service_name,
            "metric_name": self.metric_name,
            "bucket_start": self.bucket_start,
            "minimum": round(min(self.values), 2),
            "maximum": round(max(self.values), 2),
            "average": round(sum(self.values) / len(self.values), 2),
            "latest_value": round(self.values[-1], 2),
            "sample_count": len(self.values),
            "data_source": self.data_source,
        }


class ContinuousObservabilityCollector:
    """
    Background collector service responsible for:
    - Polling DemoMesh telemetry at configurable intervals (default: 5s).
    - Aggregating all 10 Golden Signals into 1-minute buckets.
    - Persisting rollups into `metric_rollups` with duplicate prevention.
    - Running 7-day retention cleanup.
    - Providing health and buffer diagnostics.
    """

    METRIC_NAMES = [
        "cpu_utilization",
        "memory_utilization",
        "disk_utilization",
        "network_throughput_mbps",
        "latency_p50_ms",
        "latency_p95_ms",
        "latency_p99_ms",
        "error_rate",
        "db_pool_utilization",
        "availability_pct",
        "dependency_health",
        "request_rate",
    ]

    def __init__(
        self,
        collection_interval_seconds: int = 5,
        retention_days: int = 7,
    ):
        self.collection_interval_seconds = collection_interval_seconds
        self.retention_days = retention_days
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # In-memory accumulators: key = (service_name, metric_name, bucket_start_timestamp)
        self._accumulators: Dict[Tuple[str, str, int], MetricBucketAccumulator] = {}
        
        # Operational health statistics
        self.status = "IDLE"
        self.last_collection_time: Optional[datetime] = None
        self.last_flush_time: Optional[datetime] = None
        self.last_cleanup_time: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.total_samples_collected: int = 0
        self.total_rollups_persisted: int = 0

    async def start(self):
        """Starts the background collection loop gracefully without blocking startup."""
        async with self._lock:
            if self._running:
                logger.info("[ObservabilityCollector] Already running.")
                return
            self._running = True
            self.status = "RUNNING"
            self._task = asyncio.create_task(self._run_loop(), name="observability-collector-loop")
            logger.info(
                f"[ObservabilityCollector] Started continuous collection loop "
                f"(interval={self.collection_interval_seconds}s, retention={self.retention_days}d)"
            )

    async def stop(self):
        """Stops the background collection loop gracefully and flushes remaining buffers."""
        async with self._lock:
            if not self._running:
                return
            self._running = False
            self.status = "STOPPED"
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            self._task = None
            
            # Flush any pending finished buckets
            try:
                await self.flush_pending_buckets(force_all=True)
            except Exception as e:
                logger.warning(f"[ObservabilityCollector] Flush on shutdown encountered warning: {e}")
            logger.info("[ObservabilityCollector] Gracefully stopped.")

    async def _run_loop(self):
        """Main periodic asyncio execution loop."""
        tick_counter = 0
        while self._running:
            try:
                await self.collect_and_aggregate()
                tick_counter += 1

                # Flush completed buckets every 30 seconds
                if tick_counter % max(1, 30 // self.collection_interval_seconds) == 0:
                    await self.flush_pending_buckets(force_all=False)

                # Run retention cleanup once per hour
                if tick_counter % max(1, 3600 // self.collection_interval_seconds) == 0:
                    await self.run_retention_cleanup()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.last_error = f"Collector cycle error: {str(e)}"
                logger.error(f"[ObservabilityCollector] Exception in collection cycle: {e}")
            
            await asyncio.sleep(self.collection_interval_seconds)

    async def collect_and_aggregate(self):
        """
        Polls current snapshot from DemoMesh and feeds metric values into
        their corresponding 1-minute bucket accumulators.
        """
        now = datetime.now(timezone.utc)
        bucket_start = now.replace(second=0, microsecond=0)
        bucket_ts = int(bucket_start.timestamp())

        metrics_map = demo_mesh.get_latest_metrics()
        if not metrics_map:
            return

        for svc_name, snap in metrics_map.items():
            if not snap:
                continue

            service_id = snap.get("service_id", str(uuid.uuid5(uuid.NAMESPACE_DNS, svc_name)))
            data_source = snap.get("data_source", "SIMULATED")

            for m_name in self.METRIC_NAMES:
                val = snap.get(m_name)
                key = (svc_name, m_name, bucket_ts)

                if key not in self._accumulators:
                    self._accumulators[key] = MetricBucketAccumulator(
                        service_id=service_id,
                        service_name=svc_name,
                        metric_name=m_name,
                        bucket_start=bucket_start,
                        data_source=data_source,
                    )

                self._accumulators[key].add_sample(val)
                self.total_samples_collected += 1

        self.last_collection_time = now

    async def flush_pending_buckets(self, force_all: bool = False) -> int:
        """
        Persists completed 1-minute statistical rollups to the database.
        If force_all is True, flushes even current active buckets (used on shutdown or tests).
        Returns the number of rollups persisted.
        """
        now = datetime.now(timezone.utc)
        current_bucket_ts = int(now.replace(second=0, microsecond=0).timestamp())

        keys_to_flush = []
        for key in list(self._accumulators.keys()):
            _, _, bucket_ts = key
            if force_all or bucket_ts < current_bucket_ts:
                keys_to_flush.append(key)

        if not keys_to_flush:
            return 0

        summaries: List[Dict[str, Any]] = []
        for k in keys_to_flush:
            acc = self._accumulators.pop(k, None)
            if acc:
                summary = acc.compute_summary()
                if summary:
                    summaries.append(summary)

        if not summaries:
            return 0

        persisted_count = 0
        try:
            async with async_session_factory() as session:
                for s in summaries:
                    # Idempotent write: check if record already exists for (service_name, metric_name, bucket_start)
                    stmt = select(MetricRollup).where(
                        MetricRollup.service_name == s["service_name"],
                        MetricRollup.metric_name == s["metric_name"],
                        MetricRollup.bucket_start == s["bucket_start"],
                    )
                    existing = (await session.execute(stmt)).scalar_one_or_none()

                    if existing:
                        # Update existing rollup
                        existing.minimum = min(existing.minimum, s["minimum"])
                        existing.maximum = max(existing.maximum, s["maximum"])
                        total_count = existing.sample_count + s["sample_count"]
                        existing.average = round(
                            ((existing.average * existing.sample_count) + (s["average"] * s["sample_count"])) / total_count,
                            2
                        )
                        existing.latest_value = s["latest_value"]
                        existing.sample_count = total_count
                        existing.data_source = s["data_source"]
                    else:
                        rollup = MetricRollup(
                            id=s["id"],
                            service_id=s["service_id"],
                            service_name=s["service_name"],
                            metric_name=s["metric_name"],
                            bucket_start=s["bucket_start"],
                            minimum=s["minimum"],
                            maximum=s["maximum"],
                            average=s["average"],
                            latest_value=s["latest_value"],
                            sample_count=s["sample_count"],
                            data_source=s["data_source"],
                        )
                        session.add(rollup)
                    persisted_count += 1

                await session.commit()
                self.total_rollups_persisted += persisted_count
                self.last_flush_time = datetime.now(timezone.utc)
                self.last_error = None
                logger.info(f"[ObservabilityCollector] Flushed {persisted_count} rollups to database.")
        except Exception as e:
            self.last_error = f"Flush error: {str(e)}"
            logger.error(f"[ObservabilityCollector] Error flushing metric rollups: {e}")
            raise

        return persisted_count

    async def run_retention_cleanup(self) -> int:
        """
        Deletes one-minute metric rollups older than the configured retention period (default: 7 days).
        Does NOT touch audit logs, incident records, or investigation evidence.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        deleted_count = 0

        try:
            async with async_session_factory() as session:
                stmt = delete(MetricRollup).where(MetricRollup.bucket_start < cutoff)
                res = await session.execute(stmt)
                deleted_count = res.rowcount or 0
                await session.commit()
                self.last_cleanup_time = datetime.now(timezone.utc)
                logger.info(
                    f"[ObservabilityCollector] Retention cleanup pruned {deleted_count} "
                    f"rollups older than {self.retention_days} days (cutoff: {cutoff.isoformat()})."
                )
        except Exception as e:
            self.last_error = f"Retention cleanup error: {str(e)}"
            logger.error(f"[ObservabilityCollector] Error during retention cleanup: {e}")

        return deleted_count

    def get_status(self) -> Dict[str, Any]:
        """Provides status and buffer metrics for health reporting."""
        return {
            "collector_status": self.status,
            "last_collection_time": self.last_collection_time.isoformat() if self.last_collection_time else None,
            "last_flush_time": self.last_flush_time.isoformat() if self.last_flush_time else None,
            "last_cleanup_time": self.last_cleanup_time.isoformat() if self.last_cleanup_time else None,
            "next_collection_interval_seconds": self.collection_interval_seconds,
            "monitored_services_count": len(demo_mesh.SERVICE_DEFINITIONS),
            "buffer_stats": {
                "active_buckets_in_memory": len(self._accumulators),
                "total_samples_collected": self.total_samples_collected,
                "total_rollups_persisted": self.total_rollups_persisted,
            },
            "last_error": self.last_error,
        }


# Singleton instance for application lifecycle
observability_collector = ContinuousObservabilityCollector(
    collection_interval_seconds=5,
    retention_days=7,
)
