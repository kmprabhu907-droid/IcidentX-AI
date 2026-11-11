"""
INCIDENTX AI - Structured Logging Setup
Provides standardized, structured JSON-formatted logs for observability and audit trails.
"""

import sys
import logging
import json
import re
from datetime import datetime, timezone
from backend.app.core.config import settings


class SensitiveDataFilter(logging.Filter):
    """
    Redacts passwords, tokens, API keys, and sensitive authorization strings
    from log records before emission to standard streams.
    """
    PATTERNS = [
        (re.compile(r'(?i)(bearer\s+[a-zA-Z0-9_\-\.]{15,})'), "Bearer [REDACTED_TOKEN]"),
        (re.compile(r'(?i)(api[_-]?key["\']?\s*[:=]\s*["\']?)[a-zA-Z0-9_\-]{16,}(["\']?)'), r"\1[REDACTED_API_KEY]\2"),
        (re.compile(r'(?i)(password["\']?\s*[:=]\s*["\']?)[^"\'\s,}{]{4,}(["\']?)'), r"\1[REDACTED_PASSWORD]\2"),
        (re.compile(r'(?i)(secret["\']?\s*[:=]\s*["\']?)[^"\'\s,}{]{6,}(["\']?)'), r"\1[REDACTED_SECRET]\2"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, repl in self.PATTERNS:
                record.msg = pattern.sub(repl, record.msg)
        return True


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON."""
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logging():
    """Initializes root logger configuration."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers = []

    handler = logging.StreamHandler(sys.stdout)
    if settings.APP_ENV == "production":
        handler.setFormatter(JSONFormatter())
    else:
        # Developer-friendly formatted logs for development
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)

    root_logger.addHandler(handler)
    root_logger.addFilter(SensitiveDataFilter())

    # Quiet external verbose loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


logger = logging.getLogger("incidentx")
