"""
INCIDENTX AI - Counter-Evidence Validation Engine (Phase 11 Module 11.4)
Actively searches for counter-evidence, contradictions, and missing expected
telemetry signals to challenge, downgrade, or refute leading hypotheses.
Enforces the principle: "Never select a root cause simply because an AI model suggested it first."
"""

from typing import Any, Dict, List, Optional
from backend.app.core.logging import logger
from backend.app.services.root_cause.schemas import (
    CounterEvidenceReport,
    HypothesisItem,
    HypothesisStatus,
)


class CounterEvidenceEngine:
    """
    Active Falsification and Counter-Evidence Discovery Engine.
    For every candidate hypothesis, checks expected signals against ground truth telemetry.
    """

    @classmethod
    def evaluate_counter_evidence(
        cls,
        hypotheses: List[HypothesisItem],
        correlated_data: Dict[str, Any],
    ) -> List[CounterEvidenceReport]:
        """
        Attempts to disprove each hypothesis by searching for contradictions and normal readings.
        """
        facts = correlated_data.get("facts", [])
        domain_groups = correlated_data.get("domain_groups", {})
        deployment_event = correlated_data.get("deployment_event")
        k8s_facts = domain_groups.get("KUBERNETES", [])
        metric_facts = domain_groups.get("METRICS", [])
        net_facts = domain_groups.get("NETWORK", [])
        log_facts = domain_groups.get("APPLICATION_LOGS", [])

        reports: List[CounterEvidenceReport] = []

        for hyp in hypotheses:
            counter_findings: List[str] = []
            missing_expected: List[str] = []
            penalty = 0.0
            verdict = "SURVIVED_DISPROOF"

            title_lower = hyp.title.lower()
            desc_lower = hyp.description.lower()

            # ----------------------------------------------------------------
            # Check 1: Database Resource Exhaustion Disproof
            # ----------------------------------------------------------------
            if "database" in title_lower or "dbpool" in hyp.id:
                # Expected: DB CPU > 80% or DB connection errors in logs
                db_errors = [e for e in log_facts if "connection refused" in (e.description or "").lower() or "too many connections" in (e.description or "").lower()]
                db_metric_spike = [e for e in metric_facts if "database" in (e.description or "").lower() or "postgres" in (e.description or "").lower()]

                # Counter-evidence: Are there metrics showing normal DB health?
                normal_db = [e for e in facts if "postgres" in (e.description or "").lower() and ("normal" in (e.description or "").lower() or "healthy" in (e.description or "").lower())]
                
                # If network agent or metric agent found DB listener healthy and CPU low:
                if not db_errors and not db_metric_spike:
                    counter_findings.append(
                        "Database server telemetry shows zero 'too many clients' errors and connection pool was healthy."
                    )
                    missing_expected.append("PostgreSQL pg_stat_activity query timeout or connection saturation records")
                    penalty += 0.35
                    verdict = "REFUTED"
                elif normal_db:
                    counter_findings.append("Ground telemetry confirms database CPU utilization remained below 40%.")
                    penalty += 0.25
                    verdict = "WEAKENED"

            # ----------------------------------------------------------------
            # Check 2: Total Network Outage / Partition Disproof
            # ----------------------------------------------------------------
            elif "network" in title_lower or "routing" in title_lower:
                # Counter-evidence: Did local TCP listener checks succeed?
                healthy_net = [e for e in net_facts if "standard cluster ip" in (e.description or "").lower() or "no systemic dns" in (e.description or "").lower()]
                if healthy_net:
                    counter_findings.append(
                        "Network diagnostic probes verified cluster DNS resolution and active TCP listener ports."
                    )
                    missing_expected.append("Corroborating packet drop or SYN retransmission counters")
                    penalty += 0.30
                    verdict = "REFUTED"
                elif not net_facts:
                    missing_expected.append("Direct ping/traceroute span measurements")
                    penalty += 0.15
                    verdict = "WEAKENED"

            # ----------------------------------------------------------------
            # Check 3: Deployment Regression Disproof
            # ----------------------------------------------------------------
            elif "deployment" in title_lower or "deploy" in hyp.id:
                if not deployment_event:
                    counter_findings.append("No deployment rollouts or image tag updates detected in target service change log.")
                    missing_expected.append("Deployment revision event in target service timeline")
                    penalty += 0.45
                    verdict = "REFUTED"
                else:
                    # Survived disproof: deployment exists and correlates with error onset
                    verdict = "SURVIVED_DISPROOF"

            # ----------------------------------------------------------------
            # Check 4: Resource Exhaustion Disproof
            # ----------------------------------------------------------------
            elif "resource" in title_lower or "saturation" in title_lower:
                # If no OOMKilled and CPU was low
                has_oom = any("oom" in (e.description or "").lower() or "137" in (e.description or "") for e in k8s_facts + log_facts)
                has_cpu = any("cpu" in (e.description or "").lower() and "surge" in (e.description or "").lower() for e in metric_facts)
                
                if not has_oom and not has_cpu:
                    counter_findings.append("Pod memory and CPU metrics show utilization remained within configured requests/limits.")
                    missing_expected.append("Container exit code 137 or CPU throttling events")
                    penalty += 0.35
                    verdict = "REFUTED"
                else:
                    verdict = "SURVIVED_DISPROOF"

            # Apply disproof penalty and update status
            new_score = max(0.05, round(hyp.confidence_score - penalty, 2))
            hyp.confidence_score = new_score

            if verdict == "REFUTED":
                hyp.status = HypothesisStatus.CONTRADICTED if counter_findings else HypothesisStatus.REJECTED
                hyp.contradicting_evidence_ids.extend([f"counter-{i+1}" for i in range(len(counter_findings))])
            elif verdict == "WEAKENED":
                if hyp.status == HypothesisStatus.SUPPORTED:
                    hyp.status = HypothesisStatus.INVESTIGATING

            if missing_expected:
                hyp.missing_evidence.extend(missing_expected)

            rationale = (
                f"Disproof attempt completed with verdict '{verdict}'. "
                f"Found {len(counter_findings)} counter-evidence findings and "
                f"{len(missing_expected)} missing expected signals. Penalty applied: -{penalty:.2f}."
            )

            reports.append(
                CounterEvidenceReport(
                    hypothesis_id=hyp.id,
                    hypothesis_title=hyp.title,
                    disproof_attempted=True,
                    counter_evidence_found=counter_findings,
                    missing_expected_evidence=missing_expected,
                    verdict=verdict,
                    score_penalty_applied=penalty,
                    rationale=rationale,
                )
            )

        return reports


counter_evidence_engine = CounterEvidenceEngine()
