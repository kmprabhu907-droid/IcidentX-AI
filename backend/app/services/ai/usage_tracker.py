"""
INCIDENTX AI - AI Cost, Token & Performance Usage Tracker (Phase 8.4)
Tracks token consumption, latency, error/fallback rates, and estimated dollar costs
per model, per provider, and per incident.
"""

import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.services.ai.models import AIUsageRecord


class AIUsageTracker:
    """
    In-memory ledger and analytics aggregator for LLM token usage and operational expenditure.
    """

    def __init__(self, max_records: int = 1000):
        self._records: deque = deque(maxlen=max_records)
        self.daily_budget_tokens: int = getattr(settings, "AI_DAILY_TOKEN_BUDGET", 500000)

    def record_usage(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        estimated_cost_usd: float,
        latency_ms: int,
        is_fallback: bool = False,
        incident_id: Optional[str] = None,
        agent_name: str = "InvestigationAgent",
        status: str = "SUCCESS",
    ) -> AIUsageRecord:
        record = AIUsageRecord(
            id=f"ai-use-{uuid.uuid4().hex[:8]}",
            incident_id=incident_id,
            agent_name=agent_name,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=round(estimated_cost_usd, 6),
            latency_ms=latency_ms,
            is_fallback=is_fallback,
            status=status,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._records.append(record)
        return record

    def get_summary(self) -> Dict[str, Any]:
        """Compute cluster-wide aggregated token, latency, and cost analytics."""
        records = list(self._records)
        total_reqs = len(records)
        total_p_tokens = sum(r.prompt_tokens for r in records)
        total_c_tokens = sum(r.completion_tokens for r in records)
        total_tokens = sum(r.total_tokens for r in records)
        total_cost = sum(r.estimated_cost_usd for r in records)
        fallback_count = sum(1 for r in records if r.is_fallback)
        avg_latency = (sum(r.latency_ms for r in records) / total_reqs) if total_reqs > 0 else 0.0

        by_provider: Dict[str, Dict[str, Any]] = {}
        by_model: Dict[str, Dict[str, Any]] = {}

        for r in records:
            # Aggregate by provider
            if r.provider not in by_provider:
                by_provider[r.provider] = {"requests": 0, "tokens": 0, "cost_usd": 0.0}
            by_provider[r.provider]["requests"] += 1
            by_provider[r.provider]["tokens"] += r.total_tokens
            by_provider[r.provider]["cost_usd"] = round(by_provider[r.provider]["cost_usd"] + r.estimated_cost_usd, 6)

            # Aggregate by model
            if r.model not in by_model:
                by_model[r.model] = {"requests": 0, "tokens": 0, "cost_usd": 0.0}
            by_model[r.model]["requests"] += 1
            by_model[r.model]["tokens"] += r.total_tokens
            by_model[r.model]["cost_usd"] = round(by_model[r.model]["cost_usd"] + r.estimated_cost_usd, 6)

        return {
            "total_requests": total_reqs,
            "total_prompt_tokens": total_p_tokens,
            "total_completion_tokens": total_c_tokens,
            "total_tokens": total_tokens,
            "total_estimated_cost_usd": round(total_cost, 6),
            "average_latency_ms": round(avg_latency, 1),
            "fallback_count": fallback_count,
            "daily_token_budget": self.daily_budget_tokens,
            "budget_consumed_percent": round((total_tokens / self.daily_budget_tokens * 100.0), 2) if self.daily_budget_tokens > 0 else 0.0,
            "usage_by_provider": by_provider,
            "usage_by_model": by_model,
        }

    def get_incident_usage(self, incident_id: str) -> Dict[str, Any]:
        """Retrieve usage records and breakdown for a specific incident."""
        records = [r for r in self._records if r.incident_id == incident_id]
        total_tokens = sum(r.total_tokens for r in records)
        total_cost = sum(r.estimated_cost_usd for r in records)

        return {
            "incident_id": incident_id,
            "requests_count": len(records),
            "request_count": len(records),
            "total_tokens": total_tokens,
            "total_estimated_cost_usd": round(total_cost, 6),
            "records": [r.model_dump() for r in records],
        }

    def clear(self) -> None:
        self._records.clear()


# Global singleton instance
ai_usage_tracker = AIUsageTracker()
