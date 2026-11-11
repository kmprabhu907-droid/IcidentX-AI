"""
INCIDENTX AI - Regression Lifecycle & Persistence Service
Manages persistence to `regression_records`, deduplication to prevent alert fatigue,
status transitions (ACTIVE -> INVESTIGATING -> CONFIRMED -> RESOLVED / FALSE_POSITIVE),
audit trail recording, and structured queries.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.models.incident import Incident
from backend.app.models.reliability import RegressionRecord
from backend.app.models.remediation import RemediationAction
from backend.app.models.service import Service
from backend.app.services.observability.engine import ObservabilityEngine
from backend.app.services.observability.regression.fingerprint import FingerprintBuilder
from backend.app.services.observability.regression.regression_detector import (
    RegressionCandidate,
    UnifiedRegressionDetector,
)


class RegressionLifecycleService:
    """
    Coordinates regression detection, deduplication, lifecycle transitions,
    and database persistence for Stage 5.3.
    """

    @classmethod
    async def evaluate_and_record_regressions(
        cls,
        db: AsyncSession,
        data_source: str = "SIMULATED",
    ) -> List[RegressionRecord]:
        """
        Executes a cluster-wide regression detection cycle across all monitored services,
        matching live telemetry against past resolved incidents.
        """
        records_updated: List[RegressionRecord] = []

        try:
            # 1. Fetch live telemetry from demo_mesh
            from backend.app.services.observability.demo_mesh import demo_mesh
            live_services = demo_mesh.get_latest_metrics()
            if not live_services:
                return []

            # 2. Fetch past incidents with remediation records
            inc_query = (
                select(Incident)
                .order_by(desc(Incident.detected_at))
                .limit(10)
            )
            inc_res = await db.execute(inc_query)
            historical_incidents = inc_res.scalars().all()
            if not historical_incidents:
                return []

            # 3. For each service and historical incident, evaluate regression
            for svc_name, svc_data in live_services.items():
                current_metrics = {
                    "cpu_utilization": float(svc_data.get("cpu_utilization", svc_data.get("cpu_usage_percent", 25.0))),
                    "memory_utilization": float(svc_data.get("memory_utilization", svc_data.get("memory_usage_percent", 45.0))),
                    "disk_utilization": float(svc_data.get("disk_utilization", svc_data.get("disk_usage_percent", 35.0))),
                    "network_throughput_mbps": float(svc_data.get("network_throughput_mbps", svc_data.get("network_mbps", 8.0))),
                    "latency_p50_ms": float(svc_data.get("latency_p50_ms", svc_data.get("p50_latency_ms", 45.0))),
                    "latency_p95_ms": float(svc_data.get("latency_p95_ms", svc_data.get("p95_latency_ms", 120.0))),
                    "latency_p99_ms": float(svc_data.get("latency_p99_ms", svc_data.get("p99_latency_ms", 220.0))),
                    "error_rate": float(svc_data.get("error_rate", svc_data.get("error_rate_percent", 0.1))),
                    "db_pool_utilization": float(svc_data.get("db_pool_utilization", 20.0)),
                    "availability_pct": float(svc_data.get("availability_pct", 99.9)),
                    "dependency_health": float(svc_data.get("dependency_health", 100.0)),
                    "request_rate": float(svc_data.get("request_rate", 12.0)),
                }

                # Construct nominal healthy baseline
                healthy_baseline = {
                    "cpu_utilization": 25.0,
                    "memory_utilization": 45.0,
                    "disk_utilization": 35.0,
                    "network_throughput_mbps": 8.0,
                    "latency_p50_ms": 45.0,
                    "latency_p95_ms": 110.0,
                    "latency_p99_ms": 200.0,
                    "error_rate": 0.1,
                    "db_pool_utilization": 18.0,
                    "availability_pct": 99.9,
                    "dependency_health": 100.0,
                    "request_rate": 12.0,
                }

                # Match against historical incidents
                for inc in historical_incidents:
                    # Check if service is within incident impact scope or title
                    impact_scope = (inc.impact_scope or "").lower()
                    title_norm = inc.title.lower().replace(" ", "-")
                    svc_norm = svc_name.lower().replace(" ", "-")
                    if (
                        svc_name not in impact_scope
                        and svc_norm not in title_norm
                        and svc_norm.replace("-", " ") not in inc.title.lower()
                    ):
                        continue

                    # Fetch remediation action for this incident if present
                    rem_query = (
                        select(RemediationAction)
                        .where(RemediationAction.incident_id == inc.id)
                        .order_by(desc(RemediationAction.created_at))
                        .limit(1)
                    )
                    rem_res = await db.execute(rem_query)
                    rem_action = rem_res.scalar_one_or_none()

                    rem_dict: Optional[Dict[str, Any]] = None
                    post_telemetry: Dict[str, float] = healthy_baseline.copy()
                    pre_telemetry: Dict[str, float] = healthy_baseline.copy()

                    if rem_action:
                        rem_dict = {
                            "id": rem_action.id,
                            "action_id": rem_action.action_id,
                            "name": rem_action.name,
                            "target_service_name": rem_action.target_service_name,
                            "status": rem_action.status,
                            "verification_status": rem_action.verification_status,
                            "rollback_status": rem_action.rollback_status,
                            "executed_at": rem_action.executed_at.isoformat() if rem_action.executed_at else None,
                        }
                        # Pre-incident failure telemetry
                        if "pool" in inc.title.lower() or "db" in inc.title.lower():
                            pre_telemetry["db_pool_utilization"] = 98.0
                            pre_telemetry["error_rate"] = 12.5
                            pre_telemetry["latency_p95_ms"] = 1450.0
                        elif "memory" in inc.title.lower():
                            pre_telemetry["memory_utilization"] = 94.0
                            pre_telemetry["error_rate"] = 8.0
                        elif "latency" in inc.title.lower():
                            pre_telemetry["latency_p95_ms"] = 2800.0
                            pre_telemetry["error_rate"] = 15.0

                    # Evaluate regression candidates
                    candidates = UnifiedRegressionDetector.evaluate_service_regression(
                        service_name=svc_name,
                        current_telemetry=current_metrics,
                        healthy_baseline=healthy_baseline,
                        historical_incident={
                            "id": inc.id,
                            "title": inc.title,
                            "summary": inc.summary or inc.title,
                            "impact_scope": inc.impact_scope,
                            "severity": inc.severity,
                        },
                        pre_incident_telemetry=pre_telemetry,
                        post_remediation_telemetry=post_telemetry,
                        remediation_action=rem_dict,
                        data_source=data_source,
                    )

                    for cand in candidates:
                        rec = await cls._persist_or_dedup_candidate(cand, db)
                        records_updated.append(rec)

            await db.commit()
        except Exception as e:
            logger.error(f"Error in evaluate_and_record_regressions: {e}", exc_info=True)
            await db.rollback()

        return records_updated

    @classmethod
    async def _persist_or_dedup_candidate(
        cls,
        cand: RegressionCandidate,
        db: AsyncSession,
    ) -> RegressionRecord:
        """
        Deduplicates regression records on (service_name, metric_name, original_incident_id)
        while the existing record is in ACTIVE or INVESTIGATING status.
        """
        now = datetime.now(timezone.utc)

        # Check existing active regression
        query = (
            select(RegressionRecord)
            .where(
                RegressionRecord.service_name == cand.service_name,
                RegressionRecord.metric_name == cand.metric_name,
                RegressionRecord.incident_id == cand.original_incident_id,
                RegressionRecord.status.in_(["ACTIVE", "DETECTED", "INVESTIGATING", "CONFIRMED"]),
            )
            .limit(1)
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        comparison_json = json.dumps(cand.comparison.to_dict()) if cand.comparison else None
        evidence_json = json.dumps({
            "detected_pattern": cand.detected_pattern,
            "similarity_result": cand.similarity_result.to_dict() if cand.similarity_result else None,
            "remediation_report": cand.remediation_report.to_dict() if cand.remediation_report else None,
            "score_breakdown": cand.score_breakdown,
        })
        explanation_json = json.dumps(cand.explanation.to_dict()) if cand.explanation else None

        if existing:
            # Deduplicate by updating existing ongoing regression
            existing.current_value = cand.observed_value
            existing.regression_score = cand.regression_score
            existing.similarity_score = cand.similarity_score
            existing.classification = cand.classification
            existing.comparison_windows = comparison_json
            existing.evidence = evidence_json
            existing.explanation = explanation_json
            existing.last_observed_at = now
            existing.data_source = cand.data_source
            return existing

        # Fetch service_id if available
        svc_q = select(Service.id).where(Service.name == cand.service_name).limit(1)
        svc_r = await db.execute(svc_q)
        service_id = svc_r.scalar_one_or_none()

        # Insert fresh regression record
        record = RegressionRecord(
            service_id=service_id,
            service_name=cand.service_name,
            incident_id=cand.original_incident_id,
            current_incident_id=cand.current_incident_id,
            metric_name=cand.metric_name,
            affected_services=json.dumps(cand.affected_services),
            matching_incident_ids=json.dumps(cand.matching_incident_ids),
            baseline_value=cand.expected_baseline,
            pre_incident_value=cand.pre_incident_value,
            post_remediation_value=cand.post_remediation_value,
            current_value=cand.observed_value,
            similarity_score=cand.similarity_score,
            regression_score=cand.regression_score,
            classification=cand.classification,
            status="ACTIVE",
            evidence=evidence_json,
            comparison_windows=comparison_json,
            previous_remediation_ids=json.dumps(cand.previous_remediation_ids),
            details=f"Regression pattern: {cand.detected_pattern} with score {cand.regression_score:.2f}",
            explanation=explanation_json,
            data_source=cand.data_source,
            first_observed_at=now,
            last_observed_at=now,
            detected_at=cand.detected_at,
        )
        db.add(record)
        return record

    @classmethod
    async def list_regressions(
        cls,
        db: AsyncSession,
        service_name: Optional[str] = None,
        metric_name: Optional[str] = None,
        status: Optional[str] = None,
        classification: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """Queries regression records with full filtering, sorting, and pagination."""
        query = select(RegressionRecord)

        if service_name:
            query = query.where(RegressionRecord.service_name == service_name)
        if metric_name:
            query = query.where(RegressionRecord.metric_name == metric_name)
        if status:
            query = query.where(RegressionRecord.status == status)
        if classification:
            query = query.where(RegressionRecord.classification == classification)
        if start_time:
            query = query.where(RegressionRecord.detected_at >= start_time)
        if end_time:
            query = query.where(RegressionRecord.detected_at <= end_time)

        # Count total matching rows
        count_query = select(func.count()).select_from(query.subquery())
        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        # Sort and paginate
        query = query.order_by(desc(RegressionRecord.last_observed_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        records = result.scalars().all()

        items = [cls._format_record(r) for r in records]
        total_pages = max(1, (total + page_size - 1) // page_size)

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "items": items,
        }

    @classmethod
    async def get_regression_by_id(
        cls,
        regression_id: str,
        db: AsyncSession,
    ) -> Optional[Dict[str, Any]]:
        query = select(RegressionRecord).where(RegressionRecord.id == regression_id)
        result = await db.execute(query)
        record = result.scalar_one_or_none()
        if not record:
            return None
        return cls._format_record(record)

    @classmethod
    async def get_active_regressions(
        cls,
        db: AsyncSession,
    ) -> List[Dict[str, Any]]:
        query = (
            select(RegressionRecord)
            .where(RegressionRecord.status.in_(["ACTIVE", "DETECTED", "INVESTIGATING", "CONFIRMED"]))
            .order_by(desc(RegressionRecord.last_observed_at))
        )
        result = await db.execute(query)
        records = result.scalars().all()
        return [cls._format_record(r) for r in records]

    @classmethod
    async def update_status(
        cls,
        regression_id: str,
        new_status: str,
        db: AsyncSession,
    ) -> Optional[Dict[str, Any]]:
        valid_statuses = ["ACTIVE", "INVESTIGATING", "CONFIRMED", "RESOLVED", "FALSE_POSITIVE"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Allowed: {valid_statuses}")

        now = datetime.now(timezone.utc)
        stmt = (
            update(RegressionRecord)
            .where(RegressionRecord.id == regression_id)
            .values(status=new_status, last_observed_at=now)
            .returning(RegressionRecord)
        )
        result = await db.execute(stmt)
        updated = result.scalar_one_or_none()
        await db.commit()
        if not updated:
            return None
        return cls._format_record(updated)

    @classmethod
    async def get_comparison(
        cls,
        regression_id: str,
        db: AsyncSession,
    ) -> Optional[Dict[str, Any]]:
        query = select(RegressionRecord).where(RegressionRecord.id == regression_id)
        result = await db.execute(query)
        record = result.scalar_one_or_none()
        if not record or not record.comparison_windows:
            return None
        try:
            return json.loads(record.comparison_windows)
        except Exception:
            return None

    @classmethod
    async def get_history(
        cls,
        regression_id: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        rec = await cls.get_regression_by_id(regression_id, db)
        if not rec:
            return {"error": "Regression record not found"}

        # Fetch original incident details
        orig_inc = None
        if rec.get("incident_id"):
            inc_q = select(Incident).where(Incident.id == rec["incident_id"])
            inc_r = await db.execute(inc_q)
            inc_obj = inc_r.scalar_one_or_none()
            if inc_obj:
                orig_inc = {
                    "id": inc_obj.id,
                    "title": inc_obj.title,
                    "severity": inc_obj.severity,
                    "status": inc_obj.status,
                    "detected_at": inc_obj.detected_at.isoformat() if inc_obj.detected_at else None,
                    "resolved_at": inc_obj.resolved_at.isoformat() if inc_obj.resolved_at else None,
                }

        # Fetch previous remediation actions
        rem_actions = []
        if rec.get("incident_id"):
            rem_q = select(RemediationAction).where(RemediationAction.incident_id == rec["incident_id"])
            rem_r = await db.execute(rem_q)
            rem_objs = rem_r.scalars().all()
            for a in rem_objs:
                rem_actions.append({
                    "id": a.id,
                    "action_id": a.action_id,
                    "name": a.name,
                    "status": a.status,
                    "verification_status": a.verification_status,
                    "rollback_status": a.rollback_status,
                    "executed_at": a.executed_at.isoformat() if a.executed_at else None,
                })

        return {
            "regression_id": regression_id,
            "service_name": rec.get("service_name"),
            "metric_name": rec.get("metric_name"),
            "original_incident": orig_inc,
            "previous_remediations": rem_actions,
            "first_observed_at": rec.get("first_observed_at"),
            "last_observed_at": rec.get("last_observed_at"),
            "lifecycle_status": rec.get("status"),
        }

    @classmethod
    async def get_remediation_effectiveness_overview(
        cls,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Returns cluster-wide summary of Phase 4 remediation stability and outcomes."""
        query = select(RemediationAction).order_by(desc(RemediationAction.created_at)).limit(50)
        result = await db.execute(query)
        actions = result.scalars().all()

        total = len(actions)
        verified = sum(1 for a in actions if a.verification_status == "VERIFIED")
        rolled_back = sum(1 for a in actions if a.rollback_status in ["EXECUTING", "ROLLED_BACK", "ROLLBACK_FAILED"])
        failed = sum(1 for a in actions if a.status == "FAILED" or a.verification_status == "FAILED")

        # Check how many regression records reference these actions
        regr_q = select(RegressionRecord).where(RegressionRecord.status.in_(["ACTIVE", "CONFIRMED"]))
        regr_r = await db.execute(regr_q)
        regressions = regr_r.scalars().all()

        return {
            "total_remediations_analyzed": total,
            "verified_immediately": verified,
            "rolled_back_count": rolled_back,
            "execution_failed_count": failed,
            "active_regressions_count": len(regressions),
            "remediation_stability_ratio": round((verified - len(regressions)) / max(1, verified), 2) if verified > 0 else 1.0,
            "actions": [
                {
                    "id": a.id,
                    "action_id": a.action_id,
                    "name": a.name,
                    "target_service_name": a.target_service_name,
                    "verification_status": a.verification_status,
                    "rollback_status": a.rollback_status,
                    "executed_at": a.executed_at.isoformat() if a.executed_at else None,
                }
                for a in actions[:15]
            ],
        }

    @staticmethod
    def _format_record(r: RegressionRecord) -> Dict[str, Any]:
        aff_services = []
        matching_ids = []
        prev_rem_ids = []
        evidence = None
        comparison = None
        explanation = None

        try:
            if r.affected_services:
                aff_services = json.loads(r.affected_services)
        except Exception:
            pass

        try:
            if r.matching_incident_ids:
                matching_ids = json.loads(r.matching_incident_ids)
        except Exception:
            pass

        try:
            if r.previous_remediation_ids:
                prev_rem_ids = json.loads(r.previous_remediation_ids)
        except Exception:
            pass

        try:
            if r.evidence:
                evidence = json.loads(r.evidence)
        except Exception:
            pass

        try:
            if r.comparison_windows:
                comparison = json.loads(r.comparison_windows)
        except Exception:
            pass

        try:
            if r.explanation:
                explanation = json.loads(r.explanation)
        except Exception:
            pass

        return {
            "id": r.id,
            "service_id": r.service_id,
            "service_name": r.service_name,
            "incident_id": r.incident_id,
            "current_incident_id": r.current_incident_id,
            "metric_name": r.metric_name,
            "affected_services": aff_services,
            "matching_incident_ids": matching_ids,
            "baseline_value": r.baseline_value,
            "pre_incident_value": r.pre_incident_value,
            "post_remediation_value": r.post_remediation_value,
            "current_value": r.current_value,
            "similarity_score": r.similarity_score,
            "regression_score": r.regression_score,
            "classification": r.classification,
            "status": r.status,
            "evidence": evidence,
            "comparison_windows": comparison,
            "previous_remediation_ids": prev_rem_ids,
            "details": r.details,
            "explanation": explanation,
            "data_source": r.data_source,
            "first_observed_at": r.first_observed_at.isoformat() if r.first_observed_at else None,
            "last_observed_at": r.last_observed_at.isoformat() if r.last_observed_at else None,
            "detected_at": r.detected_at.isoformat() if r.detected_at else None,
        }
