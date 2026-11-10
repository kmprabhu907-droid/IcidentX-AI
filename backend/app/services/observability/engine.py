"""
INCIDENTX AI - Real-Time Observability & Intelligent Anomaly Detection Engine
Coordinates telemetry ingestion from DemoMesh, executes the 5 anomaly detection modules,
correlates alerts via CorrelationEngine, and automatically creates Incident, Evidence,
and Hypothesis database records.
"""

import asyncio
from collections import deque
from datetime import datetime, timezone
import json
from typing import Any, Deque, Dict, List, Optional
import uuid

from sqlalchemy import select
from backend.app.core.database import async_session_factory
from backend.app.core.logging import logger
from backend.app.models.audit import AuditLog
from backend.app.models.incident import Incident
from backend.app.models.investigation import Evidence, RootCauseHypothesis
from backend.app.models.service import Service, ServiceDependency
from backend.app.models.telemetry import TelemetryEvent
from backend.app.services.observability.correlation import CorrelationEngine
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.observability.detectors.baseline import BaselineDetector
from backend.app.services.observability.detectors.error import ErrorIntelligenceDetector
from backend.app.services.observability.detectors.latency import LatencyDetector
from backend.app.services.observability.detectors.models import (
    AlertSeverity,
    AnomalyAlert,
)
from backend.app.services.observability.detectors.threshold import StaticThresholdDetector
from backend.app.services.observability.detectors.traffic import TrafficIntelligenceDetector


class ObservabilityEngine:
    """
    Central Autonomous Observability & Detection Engine.
    """

    def __init__(self):
        # Detectors
        self.threshold_detector = StaticThresholdDetector()
        self.baseline_detector = BaselineDetector(min_samples=10, z_score_threshold=3.0)
        self.latency_detector = LatencyDetector()
        self.error_detector = ErrorIntelligenceDetector()
        self.traffic_detector = TrafficIntelligenceDetector()

        # Multi-signal correlation engine
        self.correlation_engine = CorrelationEngine(cooldown_seconds=180)

        # Recent alerts buffer (up to 200)
        self.recent_alerts: Deque[AnomalyAlert] = deque(maxlen=200)

        # State & lifecycle
        self._running = False
        self._background_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def seed_services_if_needed(self):
        """Seed the 7 demo microservices and dependencies into database if not present."""
        try:
            async with async_session_factory() as session:
                async with session.begin():
                    # 1. Seed Services
                    svc_map: Dict[str, Service] = {}
                    for name, defs in demo_mesh.SERVICE_DEFINITIONS.items():
                        stmt = select(Service).where(Service.name == name)
                        res = await session.execute(stmt)
                        existing = res.scalar_one_or_none()
                        if not existing:
                            new_svc = Service(
                                name=name,
                                tier=defs["tier"],
                                service_type=defs["type"],
                                language=defs["language"],
                                health_status="HEALTHY",
                                repository_url=f"https://github.com/incidentx-ai/{name}",
                            )
                            session.add(new_svc)
                            await session.flush()
                            svc_map[name] = new_svc
                            logger.info(f"[ObservabilityEngine] Seeded service '{name}'")
                        else:
                            svc_map[name] = existing

                    # 2. Seed Dependencies
                    for src_name, tgt_name, proto, is_crit in demo_mesh.DEPENDENCY_TOPOLOGY:
                        src_svc = svc_map.get(src_name)
                        tgt_svc = svc_map.get(tgt_name)
                        if src_svc and tgt_svc:
                            dep_stmt = select(ServiceDependency).where(
                                ServiceDependency.source_service_id == src_svc.id,
                                ServiceDependency.target_service_id == tgt_svc.id,
                            )
                            res = await session.execute(dep_stmt)
                            if not res.scalar_one_or_none():
                                dep = ServiceDependency(
                                    source_service_id=src_svc.id,
                                    target_service_id=tgt_svc.id,
                                    protocol=proto,
                                    is_critical=is_crit,
                                )
                                session.add(dep)
                                logger.info(f"[ObservabilityEngine] Seeded dependency {src_name} -> {tgt_name}")
            logger.info("[ObservabilityEngine] Service mesh topology verification complete.")
        except Exception as e:
            logger.error(f"[ObservabilityEngine] Failed to seed services: {e}", exc_info=True)

    async def evaluate_cycle(self) -> List[AnomalyAlert]:
        """
        Runs all 5 detectors on current telemetry snapshots, collects alerts,
        correlates them, and triggers automated incident creation if detected.
        """
        async with self._lock:
            latest_metrics = demo_mesh.get_latest_metrics()
            recent_logs = demo_mesh.get_logs(limit=50)
            recent_traces = demo_mesh.get_traces(limit=20)

            cycle_alerts: List[AnomalyAlert] = []

            # Evaluate metric detectors per service
            for svc_name, snapshot in latest_metrics.items():
                if not snapshot:
                    continue

                # 1. Static threshold detector
                t_alerts = self.threshold_detector.evaluate(snapshot)
                cycle_alerts.extend(t_alerts)

                # 2. Baseline detector
                history = demo_mesh.get_service_history(svc_name, seconds=60)
                b_alerts = self.baseline_detector.evaluate(snapshot, history)
                cycle_alerts.extend(b_alerts)

                # 3. Latency detector
                l_alerts = self.latency_detector.evaluate(snapshot)
                cycle_alerts.extend(l_alerts)

                # 4. Error detector (metrics)
                prev_hist = history[-2] if len(history) >= 2 else None
                e_alerts = self.error_detector.evaluate_metrics(snapshot, prev_hist)
                cycle_alerts.extend(e_alerts)

                # 5. Traffic detector
                base_rps = demo_mesh.SERVICE_DEFINITIONS.get(svc_name, {}).get("base_rps", 10.0)
                tr_alerts = self.traffic_detector.evaluate(snapshot, base_rps)
                cycle_alerts.extend(tr_alerts)

            # Evaluate log-level patterns
            log_alerts = self.error_detector.evaluate_logs(recent_logs)
            cycle_alerts.extend(log_alerts)

            # Store recent alerts in ring buffer
            for a in cycle_alerts:
                self.recent_alerts.append(a)

            # Correlate alerts into actionable incident candidates
            if cycle_alerts:
                candidates = self.correlation_engine.correlate(
                    alerts=cycle_alerts,
                    recent_logs=recent_logs,
                    recent_traces=recent_traces,
                )

                for candidate in candidates:
                    await self._persist_correlated_incident(candidate)

            return cycle_alerts

    async def _persist_correlated_incident(self, candidate):
        """
        Automatically persists the correlated incident, evidence exhibits,
        root cause hypothesis, audit log, and telemetry events in database.
        """
        try:
            async with async_session_factory() as session:
                async with session.begin():
                    # Look up culprit service record
                    culprit_stmt = select(Service).where(Service.name == candidate.culprit_service)
                    culprit_res = await session.execute(culprit_stmt)
                    culprit_svc = culprit_res.scalar_one_or_none()
                    culprit_svc_id = culprit_svc.id if culprit_svc else None

                    # 1. Create Incident
                    incident = Incident(
                        title=candidate.title,
                        summary=candidate.summary,
                        severity=candidate.severity,
                        status="DETECTED",
                        impact_scope=", ".join(candidate.impacted_services),
                    )
                    session.add(incident)
                    await session.flush()
                    await session.refresh(incident)

                    # Update culprit service status to DEGRADED or CRITICAL
                    if culprit_svc:
                        culprit_svc.health_status = "CRITICAL" if candidate.severity in ["SEV-1", "SEV-2"] else "DEGRADED"

                    # 2. Add Evidence items
                    for ev in candidate.evidence_items:
                        evidence_row = Evidence(
                            incident_id=incident.id,
                            evidence_type=ev["evidence_type"],
                            source_system=ev["source_system"],
                            description=ev["description"],
                            confidence_score=ev["confidence_score"],
                            is_contradictory=ev["is_contradictory"],
                            raw_data=ev.get("raw_data"),
                        )
                        session.add(evidence_row)

                    # 3. Add initial Root Cause Hypothesis
                    hyp = RootCauseHypothesis(
                        incident_id=incident.id,
                        culprit_service_id=culprit_svc_id,
                        hypothesis_text=candidate.hypothesis_text,
                        probability_score=candidate.confidence_score,
                        status="PROPOSED",
                        prosecutor_argument=f"High-frequency telemetry and topological causality indicate {candidate.culprit_service} as the root anomaly epicenter.",
                        defense_argument=f"Cross-examination required to rule out external cloud network blips or client misconfiguration.",
                        is_confirmed_root_cause=False,
                    )
                    session.add(hyp)

                    # 4. Add TelemetryEvent rows
                    for item in candidate.evidence_items:
                        if item["evidence_type"] == "metric_anomaly":
                            session.add(TelemetryEvent(
                                service_id=culprit_svc_id,
                                incident_id=incident.id,
                                event_type="metric_anomaly",
                                metric_name=item["source_system"],
                                severity=candidate.severity,
                                raw_payload=item["description"],
                            ))

                    # 5. Add Audit Log
                    audit = AuditLog(
                        incident_id=incident.id,
                        actor_type="SYSTEM",
                        actor_id="AutonomousDetectionEngine",
                        action="CREATE_INCIDENT",
                        resource_type="INCIDENT",
                        resource_id=incident.id,
                        details=f"Autonomous detection created {candidate.severity} incident for {candidate.culprit_service}. Dedup: {candidate.dedup_key}",
                    )
                    session.add(audit)

            logger.info(
                f"[ObservabilityEngine] Created autonomous incident '{incident.title}' (ID: {incident.id}, Severity: {candidate.severity})"
            )
        except Exception as e:
            logger.error(f"[ObservabilityEngine] Failed to persist autonomous incident: {e}", exc_info=True)

    def get_cluster_overview(self) -> Dict[str, Any]:
        """Compute aggregated real-time cluster health and metrics."""
        latest = demo_mesh.get_latest_metrics()
        total_rps = 0.0
        total_errors = 0
        total_requests = 0
        p95_latencies = []
        healthy_count = 0
        degraded_count = 0
        critical_count = 0

        for s in latest.values():
            if not s:
                continue
            total_rps += s.get("request_rate", 0.0)
            total_requests += s.get("request_count", 0)
            total_errors += s.get("error_count", 0)
            p95_latencies.append(s.get("latency_p95_ms", 0.0))
            h = s.get("health_status", "HEALTHY")
            if h == "HEALTHY":
                healthy_count += 1
            elif h == "DEGRADED":
                degraded_count += 1
            else:
                critical_count += 1

        overall_error_rate = (total_errors / max(1, total_requests)) * 100.0 if total_requests > 0 else 0.0
        avg_p95 = sum(p95_latencies) / len(p95_latencies) if p95_latencies else 0.0
        max_p95 = max(p95_latencies) if p95_latencies else 0.0

        is_simulated = len(demo_mesh.active_faults) > 0

        return {
            "cluster_status": "CRITICAL" if critical_count > 0 else ("DEGRADED" if degraded_count > 0 else "HEALTHY"),
            "data_source": "SIMULATED" if is_simulated else "LIVE",
            "total_request_rate": round(total_rps, 1),
            "overall_error_rate": round(overall_error_rate, 2),
            "avg_p95_latency_ms": round(avg_p95, 1),
            "max_p95_latency_ms": round(max_p95, 1),
            "total_services": len(latest),
            "healthy_services": healthy_count,
            "degraded_services": degraded_count,
            "critical_services": critical_count,
            "active_anomalies_count": len(self.recent_alerts),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the most recent anomaly alerts."""
        alerts = list(self.recent_alerts)[-limit:]
        return [a.to_dict() for a in reversed(alerts)]

    def export_prometheus_metrics(self) -> str:
        """Expose standard text format Prometheus metrics."""
        lines = [
            "# HELP incidentx_request_rate_seconds Current requests per second",
            "# TYPE incidentx_request_rate_seconds gauge",
        ]
        latest = demo_mesh.get_latest_metrics()
        for svc, s in latest.items():
            if s:
                lines.append(f'incidentx_request_rate_seconds{{service="{svc}"}} {s.get("request_rate", 0.0):.2f}')

        lines.extend([
            "# HELP incidentx_error_rate_percent Current error percentage",
            "# TYPE incidentx_error_rate_percent gauge",
        ])
        for svc, s in latest.items():
            if s:
                lines.append(f'incidentx_error_rate_percent{{service="{svc}"}} {s.get("error_rate", 0.0):.2f}')

        lines.extend([
            "# HELP incidentx_latency_p95_ms 95th percentile response latency in milliseconds",
            "# TYPE incidentx_latency_p95_ms gauge",
        ])
        for svc, s in latest.items():
            if s:
                lines.append(f'incidentx_latency_p95_ms{{service="{svc}"}} {s.get("latency_p95_ms", 0.0):.2f}')

        lines.extend([
            "# HELP incidentx_cpu_utilization_percent CPU utilization percentage",
            "# TYPE incidentx_cpu_utilization_percent gauge",
        ])
        for svc, s in latest.items():
            if s:
                lines.append(f'incidentx_cpu_utilization_percent{{service="{svc}"}} {s.get("cpu_utilization", 0.0):.2f}')

        return "\n".join(lines) + "\n"

    async def start(self):
        """Start the background observability evaluation loop."""
        if self._running:
            return
        self._running = True

        # Ensure demo services and dependencies exist in DB
        await self.seed_services_if_needed()

        # Start DemoMesh generator
        await demo_mesh.start()

        async def _detection_loop():
            logger.info("[ObservabilityEngine] Autonomous anomaly detection loop started.")
            while self._running:
                try:
                    await self.evaluate_cycle()
                except Exception as e:
                    logger.error(f"[ObservabilityEngine] Error during evaluation cycle: {e}", exc_info=True)
                await asyncio.sleep(2.0)
            logger.info("[ObservabilityEngine] Detection loop terminated.")

        self._background_task = asyncio.create_task(_detection_loop())

    async def stop(self):
        """Stop observability background loop."""
        self._running = False
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
        await demo_mesh.stop()


# Singleton engine instance
observability_engine = ObservabilityEngine()
