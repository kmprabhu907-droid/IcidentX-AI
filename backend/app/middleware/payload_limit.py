"""
INCIDENTX AI - Request Payload Size Limiting Middleware (Stage 6.1)
Prevents memory exhaustion, buffer overflow, and denial-of-service via oversized request payloads.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from backend.app.core.config import settings


class PayloadLimitMiddleware(BaseHTTPMiddleware):
    """
    Enforces maximum payload size restrictions on incoming requests.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length_header = request.headers.get("content-length")

        if content_length_header:
            try:
                content_length = int(content_length_header)
                if content_length > settings.MAX_REQUEST_BODY_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Payload Too Large",
                            "detail": (
                                f"Request body size ({content_length} bytes) exceeds maximum "
                                f"allowed limit of {settings.MAX_REQUEST_BODY_BYTES} bytes."
                            ),
                        },
                    )
            except ValueError:
                # Invalid content length header format
                pass

        return await call_next(request)
