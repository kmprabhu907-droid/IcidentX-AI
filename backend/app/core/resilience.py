"""
INCIDENTX AI - Fault Tolerance & Resilience Substrate (Stage 6.6)
Implements Circuit Breakers for external dependencies and Exponential Backoff Retries with Jitter.
"""

import asyncio
from datetime import datetime, timezone
import enum
import functools
import inspect
import random
import time
from typing import Any, Callable, Dict, Optional, Tuple, Type
from backend.app.core.logging import logger


class CircuitBreakerState(str, enum.Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted while the Circuit Breaker is in the OPEN state."""
    def __init__(self, name: str, retry_after_seconds: float):
        super().__init__(
            f"Circuit breaker '{name}' is OPEN. Fast-failing request to protect downstream service. "
            f"Retry after {retry_after_seconds:.1f}s."
        )
        self.name = name
        self.retry_after_seconds = retry_after_seconds


class CircuitBreaker:
    """
    Thread-safe and async-safe Circuit Breaker implementing the 3-state pattern:
    - CLOSED: Normal operation. Successes reset failure count; consecutive failures trip to OPEN.
    - OPEN: Fast-fails all requests without invoking downstream. After recovery_timeout, moves to HALF_OPEN.
    - HALF_OPEN: Allows probe requests. If probe succeeds, resets to CLOSED. If probe fails, trips back to OPEN.
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_success_threshold = half_open_success_threshold

        self.state: CircuitBreakerState = CircuitBreakerState.CLOSED
        self.failure_count: int = 0
        self.success_count: int = 0
        self.last_state_change: float = time.monotonic()
        self.last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Executes the function protected by the circuit breaker state machine."""
        now = time.monotonic()

        async with self._lock:
            # Check state transition from OPEN to HALF_OPEN after recovery timeout
            if self.state == CircuitBreakerState.OPEN:
                elapsed = now - self.last_state_change
                if elapsed >= self.recovery_timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.last_state_change = now
                    self.success_count = 0
                    logger.info(f"[CircuitBreaker:{self.name}] Transitioned from OPEN to HALF_OPEN (probing recovery)")
                else:
                    retry_after = max(0.1, self.recovery_timeout - elapsed)
                    raise CircuitBreakerOpenException(self.name, retry_after)

        # Invoke wrapped function
        try:
            if inspect.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise e

    async def _on_success(self) -> None:
        async with self._lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.half_open_success_threshold:
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    self.last_state_change = time.monotonic()
                    logger.info(f"[CircuitBreaker:{self.name}] Probe succeeded! Circuit recovered to CLOSED state.")
            elif self.state == CircuitBreakerState.CLOSED:
                self.failure_count = 0

    async def _on_failure(self) -> None:
        now = time.monotonic()
        async with self._lock:
            self.last_failure_time = now
            if self.state == CircuitBreakerState.HALF_OPEN:
                # Any failure in half-open immediately trips back to OPEN
                self.state = CircuitBreakerState.OPEN
                self.last_state_change = now
                logger.warning(f"[CircuitBreaker:{self.name}] Probe failed in HALF_OPEN. Tripping back to OPEN state.")
            elif self.state == CircuitBreakerState.CLOSED:
                self.failure_count += 1
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitBreakerState.OPEN
                    self.last_state_change = now
                    logger.warning(
                        f"[CircuitBreaker:{self.name}] Failure threshold ({self.failure_threshold}) reached. "
                        f"Circuit tripped to OPEN state for {self.recovery_timeout}s."
                    )

    async def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        async with self._lock:
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_state_change = time.monotonic()


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator for retrying asynchronous operations with exponential backoff and full jitter.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 1
            delay = base_delay

            while True:
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    if attempt >= max_attempts:
                        logger.error(
                            f"[Retry] Function '{func.__name__}' failed after {max_attempts} attempts. Final error: {e}"
                        )
                        raise e

                    sleep_time = min(delay, max_delay)
                    if jitter:
                        sleep_time = random.uniform(0, sleep_time)

                    logger.warning(
                        f"[Retry] Attempt {attempt}/{max_attempts} for '{func.__name__}' failed: {e}. "
                        f"Retrying in {sleep_time:.2f}s..."
                    )
                    await asyncio.sleep(sleep_time)

                    delay *= backoff_factor
                    attempt += 1

        return wrapper
    return decorator
