"""
INCIDENTX AI - Enterprise HTTP Security Headers Middleware (Stage 6.1)
Implements defense-in-depth headers for clickjacking, MIME sniffing, XSS, and transport security.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from backend.app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects enterprise security headers into all outgoing HTTP responses.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        if not settings.ENABLE_SECURITY_HEADERS:
            return response

        # 1. Anti-Clickjacking: Disallow embedding in iframes
        response.headers["X-Frame-Options"] = "DENY"

        # 2. MIME Sniffing Defense: Enforce declared content types
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 3. Modern XSS Defense: Disable legacy, buggy XSS auditor
        response.headers["X-XSS-Protection"] = "0"

        # 4. Referrer Policy: Send full referrer on same-origin, domain-only cross-origin
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 5. Permissions / Feature Policy: Restrict browser hardware APIs
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), microphone=(), payment=(), usb=()"
        )

        # 6. Content Security Policy (CSP)
        if settings.CSP_POLICY:
            response.headers["Content-Security-Policy"] = settings.CSP_POLICY

        # 7. HTTP Strict Transport Security (HSTS)
        # Enforced in production or when connection is over HTTPS
        is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
        if settings.ENABLE_HSTS or settings.APP_ENV == "production" or is_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return response
