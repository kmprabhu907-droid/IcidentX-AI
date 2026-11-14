"""
INCIDENTX AI - Live Incident Timeline Engine (Phase 9 Module 9.2)
Records discrete historical and real-time operational events across all investigation,
remediation, infrastructure, and human actions. Provides real-time SSE stream broadcasting.
"""

import asyncio
from datetime import datetime, timezone
import json
from typing import Any, AsyncGenerator, Dict, List, Optional, Set
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.models.timeline import TimelineEvent


class IncidentTimelineBroadcaster:
    """In-memory pub/sub broadcaster for real-time Server-Sent Events (SSE)."""

    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, incident_id: str) -> asyncio.Queue:
        async with self._lock:
            if incident_id not in self._subscribers:
                self._subscribers[incident_id] = set()
            q: asyncio.Queue = asyncio.Queue(maxsize=100)
            self._subscribers[incident_id].add(q)
            logger.debug(f"[TimelineBroadcaster] Client subscribed to incident {incident_id}. Total: {len(self._subscribers[incident_id])}")
            return q

    async def unsubscribe(self, incident_id: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            if incident_id in self._subscribers:
                self._subscribers[incident_id].discard(queue)
                if not self._subscribers[incident_id]:
                    del self._subscribers[incident_id]
            logger.debug(f"[TimelineBroadcaster] Client unsubscribed from incident {incident_id}")

    async def broadcast(self, incident_id: str, event_data: Dict[str, Any]) -> None:
        async with self._lock:
            queues = list(self._subscribers.get(incident_id, []))

        for q in queues:
            try:
                q.put_nowait(event_data)
            except asyncio.QueueFull:
                logger.warning(f"[TimelineBroadcaster] Queue full for subscriber on incident {incident_id}")


# Singleton broadcaster
timeline_broadcaster = IncidentTimelineBroadcaster()


class IncidentTimelineEngine:
    """
    Chronological Timeline Engine for persisting and streaming incident events.
    """

    @classmethod
    async def record_event(
        cls,
        incident_id: str,
        event_type: str,
        service_name: str,
        title: str,
        description: str,
        severity: str = "INFO",
        actor: str = "SYSTEM",
        actor_type: str = "SYSTEM",
        data_source: str = "LIVE",
        raw_data: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> TimelineEvent:
        now = datetime.now(timezone.utc)
        ev = TimelineEvent(
            incident_id=incident_id,
            timestamp=now,
            event_type=event_type,
            service_name=service_name,
            title=title,
            description=description,
            severity=severity,
            actor=actor,
            actor_type=actor_type,
            data_source=data_source,
            raw_data=raw_data,
        )

        if session is not None:
            session.add(ev)
            await session.flush()

        # Broadcast event to SSE subscribers
        event_dict = {
            "id": ev.id,
            "incident_id": incident_id,
            "timestamp": now.isoformat(),
            "event_type": event_type,
            "service_name": service_name,
            "title": title,
            "description": description,
            "severity": severity,
            "actor": actor,
            "actor_type": actor_type,
            "data_source": data_source,
            "raw_data": raw_data,
        }
        asyncio.create_task(timeline_broadcaster.broadcast(incident_id, event_dict))
        return ev

    @classmethod
    async def list_events(
        cls,
        incident_id: str,
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
        event_type: Optional[str] = None,
    ) -> List[TimelineEvent]:
        query = (
            select(TimelineEvent)
            .where(TimelineEvent.incident_id == incident_id)
            .order_by(TimelineEvent.timestamp.asc())
        )
        if event_type:
            query = query.where(TimelineEvent.event_type == event_type)
        query = query.limit(limit).offset(offset)

        res = await session.execute(query)
        return list(res.scalars().all())

    @classmethod
    async def event_generator(
        cls,
        incident_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        Yields Server-Sent Events (SSE) for live timeline streaming.
        """
        q = await timeline_broadcaster.subscribe(incident_id)
        try:
            # Yield connection established heartbeat
            init_payload = json.dumps({"type": "CONNECTED", "incident_id": incident_id})
            yield f"event: connect\ndata: {init_payload}\n\n"

            while True:
                # Wait for next event or heartbeat
                try:
                    event_data = await asyncio.wait_for(q.get(), timeout=20.0)
                    yield f"event: timeline_event\ndata: {json.dumps(event_data)}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat keepalive
                    yield "event: ping\ndata: {}\n\n"
        finally:
            await timeline_broadcaster.unsubscribe(incident_id, q)


# Singleton engine
incident_timeline_engine = IncidentTimelineEngine()
