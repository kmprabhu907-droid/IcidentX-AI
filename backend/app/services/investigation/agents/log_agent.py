"""
INCIDENTX AI - Log Analysis Agent
Scans structured logs, groups repeated exceptions into clusters, and applies prompt sanitization.
"""

from collections import Counter
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.ai.sanitizer import PromptSanitizer
from backend.app.services.investigation.agents.base import BaseInvestigationAgent
from backend.app.services.investigation.schemas import (
    LogAnalysisResult,
    LogExceptionCluster,
)
from backend.app.services.observability.demo_mesh import demo_mesh


class LogAnalysisAgent(BaseInvestigationAgent):
    def __init__(self):
        super().__init__(
            name="LogAnalysisAgent",
            role="log",
            execution_phase="LOG_ANALYSIS",
            timeout_seconds=10.0,
        )

    async def execute(
        self,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        # Fetch recent logs from DemoMesh
        raw_logs = demo_mesh.get_logs(limit=150)
        error_logs = [log for log in raw_logs if log.get("level") in ["ERROR", "WARN"]]

        cluster_counts: Dict[str, Counter] = {}
        samples: Dict[str, str] = {}
        first_seens: Dict[str, str] = {}
        injection_flag = False

        for log in error_logs:
            svc = log.get("service_name", "unknown")
            msg = log.get("message", "")

            # Check for prompt injection attempt
            clean_msg = PromptSanitizer.sanitize_text(msg)
            if "[UNTRUSTED_INJECTION_VECTOR_NEUTRALIZED]" in clean_msg:
                injection_flag = True

            sig = clean_msg.split(":")[0].strip() if ":" in clean_msg else clean_msg[:40]
            if svc not in cluster_counts:
                cluster_counts[svc] = Counter()

            cluster_counts[svc][sig] += 1
            if sig not in samples:
                samples[sig] = clean_msg
                first_seens[sig] = log.get("timestamp", "")

        clusters: List[LogExceptionCluster] = []
        for svc, counts in cluster_counts.items():
            for sig, count in counts.items():
                clusters.append(LogExceptionCluster(
                    service_name=svc,
                    signature=sig,
                    count=count,
                    first_seen=first_seens.get(sig, ""),
                    sample_message=samples.get(sig, "")[:200],
                ))

        clusters.sort(key=lambda c: c.count, reverse=True)
        summary = (
            f"Analyzed {len(raw_logs)} logs. Found {len(error_logs)} fatal/error log lines "
            f"distributed across {len(clusters)} distinct exception clusters."
        )

        res = LogAnalysisResult(
            exception_clusters=clusters[:5],
            fatal_errors_count=len(error_logs),
            prompt_injection_detected=injection_flag,
            log_summary=summary,
        )

        state["logs"] = res.model_dump()
        return state
