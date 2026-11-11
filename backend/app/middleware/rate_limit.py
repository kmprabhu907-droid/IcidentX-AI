"""
INCIDENTX AI - Sliding-Window Rate Limiting Middleware (Stage 6.1)
Protects API endpoints against brute force, denial-of-service, and resource exhaustion attacks.
"""

import asyncio
import time
from typing import Dict, List, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from backend.app.core.config import settings


class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding-window rate limiter.
    Maintains a rolling 60-second window of request timestamps per key.
    """

    def __init__(self):
        self._windows: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, client_key: str, limit: int, window_seconds: int = 60) -> Tuple[bool, int, int, int]:
        """
        Check if request is allowed under the rate limit.
        Returns: (is_allowed, limit, remaining, retry_after)
        """
        now = time.monotonic()
        cutoff = now - window_seconds

        async with self._lock:
            timestamps = self._windows.setdefault(client_key, [])
            # Prune expired timestamps
            self._windows[client_key] = [ts for ts in timestamps if ts > cutoff]
            timestamps = self._windows[client_key]

            current_count = len(timestamps)
            if current_count >= limit:
                oldest_ts = timestamps[0]
                retry_after = max(1, int(oldest_ts + window_seconds - now))
                return False, limit, 0, retry_after

            # Record this request
            timestamps.append(now)
            remaining = max(0, limit - len(timestamps))
            return True, limit, remaining, 0

    async def reset(self):
        """Clears all tracked rate limit windows (used in test teardown)."""
        async with self._lock:
            self._windows.clear()


# Global singleton instance
rate_limiter = SlidingWindowRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware applying category-aware sliding-window rate limits.
    """

    EXEMPT_PATHS = {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
        "/api/v1/health/ready",
        "/api/v1/health/live",
    }

    def _get_client_identifier(self, request: Request) -> str:
        # Check authorization token if present
        auth_header = request.headers.get("Authorization")
        if auth_header and len(auth_header) > 15:
            # Hash or truncate for tracking key
            return f"auth:{auth_header[-16:]}"

        # Check X-Forwarded-For if behind a proxy / load balancer
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
            return f"ip:{client_ip}"

        # Direct client IP fallback
        if request.client and request.client.host:
            return f"ip:{request.client.host}"

        return "ip:anonymous"

    def _get_limit_for_request(self, request: Request) -> Tuple[str, int]:
        path = request.url.path
        method = request.method.upper()

        if path.startswith(f"{settings.API_V1_PREFIX}/simulation"):
            return "simulation", settings.RATE_LIMIT_SIMULATION_RPM
        elif method in ("POST", "PUT", "DELETE", "PATCH"):
            return "mutation", settings.RATE_LIMIT_MUTATION_RPM
        else:
            return "default", settings.RATE_LIMIT_DEFAULT_RPM

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.ENABLE_RATE_LIMITING:
            return await call_next(request)

        # Check exemptions
        path = request.url.path
        if path in self.EXEMPT_PATHS or path.startswith("/static"):
            return await call_next(request)

        client_id = self._get_client_identifier(request)
        category, limit = self._get_limit_for_request(request)
        key = f"{client_id}:{category}"

        allowed, req_limit, remaining, retry_after = await rate_limiter.is_allowed(key, limit)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "detail": f"Rate limit of {req_limit} requests/minute exceeded for category '{category}'.",
                    "category": category,
                    "retry_after_seconds": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(req_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                },
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(req_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
