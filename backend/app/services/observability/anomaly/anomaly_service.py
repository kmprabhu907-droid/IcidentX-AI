"""
INCIDENTX AI - Anomaly Lifecycle & Persistence Service
Coordinates continuous evaluation, deduplication, lifecycle transitions
(ACTIVE, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE), database persistence,
and baseline inspection across the microservice topology.
"""

import asyncio
from datetime import datetime, timezone
import json
import math
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import and_, delete, desc, func, select, update
from backend.app.core.database import async_session_factory
from backend.app.core.logging import logger
from backend.app.models.reliability import AnomalyRecord
from backend.app.services.observability.anomaly.detector import AnomalyCandidate, UnifiedAnomalyDetector
from backend.app.services.observability.anomaly.rules import AnomalyLifecycleStatus
from backend.app.services.observability.demo_mesh import demo_mesh


class AnomalyLifecycleService:
    """
    Manages end-to-end anomaly detection, deduplication, and persistence lifecycle.
    Prevents duplicate database alerts for ongoing anomalies by updating observation counts.
    """

    def __init__(self, detector: Optional[UnifiedAnomalyDetector] = None):
        self.detector = detector or UnifiedAnomalyDetector()
        self._lock = asyncio.Lock()
        
        # Operational health & metrics
        self.last_detection_cycle: Optional[datetime] = None
        self.total_anomalies_detected: int = 0
        self.active_anomalies_count: int = 0
        self.last_error: Optional[str] = None

    async def run_detection_cycle(self) -> List[Dict[str, Any]]:
        """
        Executes one full detection sweep across all 7 microservices in DemoMesh.
        Deduplicates against active anomalies in database and returns active candidates.
        """
        async with self._lock:
            now = datetime.now(timezone.utc)
            latest_metrics = demo_mesh.get_latest_metrics()
            all_candidates: List[AnomalyCandidate] = []

            for svc_name, snap in latest_metrics.items():
                if not snap:
                    continue
                service_id = snap.get("service_id", str(uuid.uuid5(uuid.NAMESPACE_DNS, svc_name)))
                service_tier = demo_mesh.SERVICE_DEFINITIONS.get(svc_name, {}).get("tier", "Tier-1")

                candidates = self.detector.evaluate_service_snapshot(
                    service_id=service_id,
                    service_name=svc_name,
                    current_metrics=snap,
                    service_tier=service_tier,
                )
                all_candidates.extend(candidates)

            # Persist and deduplicate candidates in database
            persisted_results = await self._persist_and_deduplicate(all_candidates, now)
            self.last_detection_cycle = now
            return persisted_results

    async def _persist_and_deduplicate(
        self,
        candidates: List[AnomalyCandidate],
        cycle_time: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Persists candidates. If an active anomaly already exists for (service_name, metric_name),
        updates its last_observed_at, observed_value, and observation_count instead of inserting a duplicate.
        """
        results: List[Dict[str, Any]] = []

        try:
            async with async_session_factory() as session:
                # Query all currently active anomalies
                stmt = select(AnomalyRecord).where(AnomalyRecord.status.in_(["ACTIVE", "ACKNOWLEDGED"]))
                active_records = (await session.execute(stmt)).scalars().all()
                active_map = {(r.service_name, r.metric_name): r for r in active_records}

                seen_keys = set()
                for c in candidates:
                    key = (c.service_name, c.metric_name)
                    seen_keys.add(key)
                    evidence_json = json.dumps({
                        "evidence": c.supporting_evidence,
                        "explanation": c.explanation_10_questions,
                    })

                    if key in active_map:
                        # Existing active anomaly: update in place (Deduplication)
                        rec = active_map[key]
                        rec.observed_value = c.observed_value
                        rec.deviation = c.deviation
                        rec.ewma_value = c.ewma_value
                        rec.trend_slope = c.trend_slope
                        rec.severity = c.severity.value
                        rec.confidence = max(rec.confidence, c.confidence)
                        rec.observation_count += 1
                        rec.last_observed_at = cycle_time
                        rec.supporting_evidence = evidence_json
                        results.append(c.to_dict())
                    else:
                        # New anomaly: create new record
                        new_rec = AnomalyRecord(
                            id=c.anomaly_id,
                            service_id=c.service_id,
                            service_name=c.service_name,
                            metric_name=c.metric_name,
                            observed_value=c.observed_value,
                            expected_baseline=c.expected_baseline,
                            deviation=c.deviation,
                            ewma_value=c.ewma_value,
                            trend_slope=c.trend_slope,
                            severity=c.severity.value,
                            confidence=c.confidence,
                            detector_type=c.detector_type,
                            supporting_evidence=evidence_json,
                            status="ACTIVE",
                            observation_count=1,
                            first_observed_at=cycle_time,
                            last_observed_at=cycle_time,
                            detected_at=cycle_time,
                            data_source=c.data_source,
                        )
                        session.add(new_rec)
                        self.total_anomalies_detected += 1
                        results.append(c.to_dict())

                await session.commit()
                self.active_anomalies_count = len(seen_keys)
                self.last_error = None
        except Exception as e:
            self.last_error = f"Persistence error: {str(e)}"
            logger.error(f"[AnomalyLifecycleService] Error persisting anomalies: {e}")

        return results

    async def list_anomalies(
        self,
        service_name: Optional[str] = None,
        metric_name: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """Queries historical anomaly records with filtering and pagination."""
        async with async_session_factory() as session:
            query = select(AnomalyRecord)
            conditions = []

            if service_name:
                conditions.append(AnomalyRecord.service_name == service_name)
            if metric_name:
                conditions.append(AnomalyRecord.metric_name == metric_name)
            if severity:
                conditions.append(AnomalyRecord.severity == severity.upper())
            if status:
                conditions.append(AnomalyRecord.status == status.upper())
            if start_time:
                conditions.append(AnomalyRecord.detected_at >= start_time)
            if end_time:
                conditions.append(AnomalyRecord.detected_at <= end_time)

            if conditions:
                query = query.where(and_(*conditions))

            count_query = select(func.count()).select_from(query.subquery())
            total = (await session.execute(count_query)).scalar() or 0

            offset = (page - 1) * page_size
            query = query.order_by(desc(AnomalyRecord.last_observed_at)).offset(offset).limit(page_size)
            records = (await session.execute(query)).scalars().all()

            total_pages = math.ceil(total / page_size) if total > 0 else 1

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "items": [self._format_record(r) for r in records],
            }

    async def get_active_anomalies(self) -> List[Dict[str, Any]]:
        """Returns all currently ACTIVE or ACKNOWLEDGED anomaly records."""
        async with async_session_factory() as session:
            stmt = (
                select(AnomalyRecord)
                .where(AnomalyRecord.status.in_(["ACTIVE", "ACKNOWLEDGED"]))
                .order_by(desc(AnomalyRecord.last_observed_at))
            )
            records = (await session.execute(stmt)).scalars().all()
            return [self._format_record(r) for r in records]

    async def get_anomaly_by_id(self, anomaly_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves full details of a specific anomaly by UUID."""
        async with async_session_factory() as session:
            stmt = select(AnomalyRecord).where(AnomalyRecord.id == anomaly_id)
            rec = (await session.execute(stmt)).scalar_one_or_none()
            return self._format_record(rec) if rec else None

    async def update_anomaly_status(self, anomaly_id: str, new_status: str) -> Optional[Dict[str, Any]]:
        """Updates the lifecycle status of an anomaly (ACTIVE, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE)."""
        valid_statuses = ["ACTIVE", "ACKNOWLEDGED", "RESOLVED", "FALSE_POSITIVE"]
        status_clean = new_status.upper()
        if status_clean not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of {valid_statuses}")

        async with async_session_factory() as session:
            stmt = select(AnomalyRecord).where(AnomalyRecord.id == anomaly_id)
            rec = (await session.execute(stmt)).scalar_one_or_none()
            if not rec:
                return None

            rec.status = status_clean
            await session.commit()
            return self._format_record(rec)

    def get_service_baselines(self, service_identifier: str) -> Dict[str, Any]:
        """
        Inspects dynamic baseline statistics for a service by service_name or service_id.
        """
        # Resolve service name if ID passed
        service_name = service_identifier
        for name, sid in demo_mesh.SERVICE_ID_MAP.items():
            if sid == service_identifier or name == service_identifier:
                service_name = name
                break

        baselines = self.detector.baseline_engine.get_all_service_baselines(service_name)
        return {
            "service_name": service_name,
            "service_id": demo_mesh.SERVICE_ID_MAP.get(service_name, str(uuid.uuid5(uuid.NAMESPACE_DNS, service_name))),
            "baselines": baselines,
        }

    def get_status(self) -> Dict[str, Any]:
        """Provides health and runtime diagnostics for the detection engine."""
        return {
            "status": "HEALTHY" if self.last_error is None else "DEGRADED",
            "last_detection_cycle": self.last_detection_cycle.isoformat() if self.last_detection_cycle else None,
            "total_anomalies_detected": self.total_anomalies_detected,
            "active_anomalies_count": self.active_anomalies_count,
            "monitored_services": len(demo_mesh.SERVICE_DEFINITIONS),
            "last_error": self.last_error,
        }

    @staticmethod
    def _format_record(r: AnomalyRecord) -> Dict[str, Any]:
        """Serializes AnomalyRecord to a rich API dictionary."""
        evidence_dict = {}
        if r.supporting_evidence:
            try:
                evidence_dict = json.loads(r.supporting_evidence)
            except Exception:
                evidence_dict = {"raw": r.supporting_evidence}

        return {
            "id": r.id,
            "service_id": r.service_id,
            "service_name": r.service_name,
            "metric_name": r.metric_name,
            "observed_value": r.observed_value,
            "expected_baseline": r.expected_baseline,
            "deviation": r.deviation,
            "ewma_value": r.ewma_value,
            "trend_slope": r.trend_slope,
            "severity": r.severity,
            "confidence": r.confidence,
            "detector_type": r.detector_type,
            "status": r.status,
            "observation_count": r.observation_count,
            "first_observed_at": r.first_observed_at.isoformat() if r.first_observed_at else None,
            "last_observed_at": r.last_observed_at.isoformat() if r.last_observed_at else None,
            "detected_at": r.detected_at.isoformat() if r.detected_at else None,
            "data_source": r.data_source,
            "supporting_evidence": evidence_dict.get("evidence", {}),
            "explanation": evidence_dict.get("explanation", {}),
        }


# Global singleton instance
anomaly_service = AnomalyLifecycleService()
