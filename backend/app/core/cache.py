"""
INCIDENTX AI - High-Performance In-Memory & Distributed Cache (Stage 6.7)
Implements LRU cache with TTL expiration and @cached decorator for topology and SLO queries.
"""

import asyncio
from collections import OrderedDict
from dataclasses import dataclass
import functools
import hashlib
import json
import time
from typing import Any, Callable, Dict, Optional
from backend.app.core.logging import logger


@dataclass
class CacheEntry:
    value: Any
    expires_at: Optional[float]


class InMemoryCache:
    """
    Thread-safe and async-safe LRU in-memory cache with TTL support and statistics tracking.
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self.hits: int = 0
        self.misses: int = 0
        self.evictions: int = 0

    async def get(self, key: str) -> Optional[Any]:
        now = time.monotonic()
        async with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None

            entry = self._cache[key]
            # Check TTL
            if entry.expires_at is not None and now > entry.expires_at:
                del self._cache[key]
                self.misses += 1
                return None

            # LRU hit: move to end
            self._cache.move_to_end(key)
            self.hits += 1
            return entry.value

    async def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        now = time.monotonic()
        expires_at = (now + ttl_seconds) if ttl_seconds is not None else None

        async with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self.max_size:
                # Evict oldest entry
                self._cache.popitem(last=False)
                self.evictions += 1

            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self, prefix: Optional[str] = None) -> int:
        async with self._lock:
            if prefix is None:
                count = len(self._cache)
                self._cache.clear()
                return count

            keys_to_del = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_del:
                del self._cache[k]
            return len(keys_to_del)

    async def stats(self) -> Dict[str, Any]:
        async with self._lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total) if total > 0 else 0.0
            return {
                "hits": self.hits,
                "misses": self.misses,
                "total_requests": total,
                "hit_rate": hit_rate,
                "evictions": self.evictions,
                "active_keys": len(self._cache),
                "max_size": self.max_size,
            }

    async def reset_stats(self) -> None:
        async with self._lock:
            self.hits = 0
            self.misses = 0
            self.evictions = 0


# Global singleton cache instance
cache = InMemoryCache(max_size=2000)


def cached(
    ttl_seconds: float = 60.0,
    key_prefix: str = "cache",
):
    """
    Decorator to cache the results of async functions using argument serialization.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if skip_cache is requested
            skip = kwargs.pop("skip_cache", False)

            # Build deterministic hash of arguments
            arg_str = json.dumps([str(a) for a in args], sort_keys=True)
            kwarg_str = json.dumps({k: str(v) for k, v in kwargs.items()}, sort_keys=True)
            arg_hash = hashlib.md5(f"{arg_str}:{kwarg_str}".encode()).hexdigest()[:12]
            cache_key = f"{key_prefix}:{func.__name__}:{arg_hash}"

            if not skip:
                cached_val = await cache.get(cache_key)
                if cached_val is not None:
                    return cached_val

            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl_seconds=ttl_seconds)
            return result

        return wrapper
    return decorator
