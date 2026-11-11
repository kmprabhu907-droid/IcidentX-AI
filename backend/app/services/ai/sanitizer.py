"""
INCIDENTX AI - Prompt Injection Defense & Data Sanitizer
Treats all logs, trace payloads, and metric tags as untrusted input.
Redacts secrets, masks credentials, and neutralizes prompt injection vectors.
"""

import re
from typing import Any, Dict, List, Union


class PromptSanitizer:
    """
    Sanitizes untrusted operational telemetry before passing it to LLM prompts
    or analytical reasoning engines.
    """

    # Secret / credential patterns to redact
    SECRET_PATTERNS = [
        (re.compile(r'(?i)(bearer\s+[a-zA-Z0-9_\-\.]{15,})'), "[REDACTED_BEARER_TOKEN]"),
        (re.compile(r'(?i)(api[_-]?key["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{16,}["\']?)'), "api_key=[REDACTED_API_KEY]"),
        (re.compile(r'(?i)(password["\']?\s*[:=]\s*["\']?[^"\'\s]{6,}["\']?)'), "password=[REDACTED_PASSWORD]"),
        (re.compile(r'(?i)(secret["\']?\s*[:=]\s*["\']?[^"\'\s]{8,}["\']?)'), "secret=[REDACTED_SECRET]"),
        (re.compile(r'-----BEGIN\s+PRIVATE\s+KEY-----[\s\S]+?-----END\s+PRIVATE\s+KEY-----'), "[REDACTED_PRIVATE_KEY]"),
        (re.compile(r'(?i)(authorization:\s*(Basic|Bearer)\s+[^\s]+)'), "authorization: [REDACTED_AUTH_HEADER]"),
    ]

    # Prompt injection vectors common in attack strings
    INJECTION_PATTERNS = [
        re.compile(r'(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions'),
        re.compile(r'(?i)you\s+are\s+now\s+in\s+developer\s+mode'),
        re.compile(r'(?i)system\s*override'),
        re.compile(r'(?i)disregard\s+all\s+(prior|above)\s+rules'),
        re.compile(r'(?i)bypass\s+all\s+safety'),
        re.compile(r'(?i)act\s+as\s+an\s+unrestricted'),
        re.compile(r'(?i)execute\s+command\s*:\s*rm\s+-rf'),
        re.compile(r'(?i)dump\s+database\s+credentials'),
    ]

    @classmethod
    def sanitize_text(cls, text: str, max_length: int = 4000) -> str:
        """
        Sanitize raw text from logs, error messages, or telemetry.
        """
        if not text:
            return ""

        sanitized = text

        # 1. Truncate excessive input to prevent context stuffing
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "... [TRUNCATED]"

        # 2. Redact sensitive credentials and API tokens
        for pattern, replacement in cls.SECRET_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

        # 3. Detect and neutralize prompt injection attempts
        for pattern in cls.INJECTION_PATTERNS:
            if pattern.search(sanitized):
                sanitized = pattern.sub("[UNTRUSTED_INJECTION_VECTOR_NEUTRALIZED]", sanitized)

        # 4. Strip dangerous terminal escape codes
        sanitized = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', sanitized)

        return sanitized

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively sanitize dictionary values.
        """
        cleaned = {}
        for k, v in data.items():
            if isinstance(v, str):
                cleaned[k] = cls.sanitize_text(v)
            elif isinstance(v, dict):
                cleaned[k] = cls.sanitize_dict(v)
            elif isinstance(v, list):
                cleaned[k] = [
                    cls.sanitize_text(x) if isinstance(x, str)
                    else (cls.sanitize_dict(x) if isinstance(x, dict) else x)
                    for x in v
                ]
            else:
                cleaned[k] = v
        return cleaned
