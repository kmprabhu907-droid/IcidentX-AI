"""
INCIDENTX AI - Asynchronous Domain Event Bus (Stage 6.5)
Pub/Sub event bus decoupling reliability detection, workflow state machines, integrations, and audit logging.
"""

import asyncio
from typing import Any, Awaitable, Callable, Dict, List
from backend.app.core.logging import logger
from backend.app.services.events.events import DomainEvent


EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    """Thread-safe asynchronous Pub/Sub Event Bus for reliability domain events."""

    def __init__(self):
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register an asynchronous listener for an event type or wildcard '*'."""
        async with self._lock:
            handlers = self._subscribers.setdefault(event_type, [])
            if handler not in handlers:
                handlers.append(handler)
        logger.debug(f"[EventBus] Registered handler {handler.__name__} for event '{event_type}'")

    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unregister an asynchronous listener."""
        async with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type] = [h for h in self._subscribers[event_type] if h != handler]

    async def publish(self, event: DomainEvent) -> List[Any]:
        """
        Dispatches an event concurrently to all matching subscribers.
        Catches and logs handler exceptions to isolate listener failures.
        """
        handlers_to_run: List[EventHandler] = []
        async with self._lock:
            # Type-specific handlers
            if event.type in self._subscribers:
                handlers_to_run.extend(self._subscribers[event.type])
            # Wildcard handlers
            if "*" in self._subscribers:
                handlers_to_run.extend(self._subscribers["*"])

        if not handlers_to_run:
            logger.debug(f"[EventBus] No subscribers for event '{event.type}'")
            return []

        logger.info(f"[EventBus] Publishing event '{event.type}' (id={event.id}) to {len(handlers_to_run)} subscribers")
        results = await asyncio.gather(
            *[self._safe_execute(handler, event) for handler in handlers_to_run],
            return_exceptions=True,
        )
        return list(results)

    async def _safe_execute(self, handler: EventHandler, event: DomainEvent) -> Any:
        try:
            return await handler(event)
        except Exception as e:
            logger.error(f"[EventBus] Handler {handler.__name__} raised error on event {event.type}: {e}", exc_info=True)
            return e

    async def clear(self) -> None:
        """Clear all active subscriptions (used during test teardown)."""
        async with self._lock:
            self._subscribers.clear()


# Global event bus singleton instance
event_bus = EventBus()
