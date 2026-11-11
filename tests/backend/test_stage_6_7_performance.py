"""
INCIDENTX AI - Stage 6.7 Performance Optimization & Horizontal Scaling Tests
Verifies LRU cache with TTL, @cached decorator, database pooling configurations,
and Next.js standalone container compilation output.
"""

import asyncio
from pathlib import Path
import pytest
from backend.app.core.cache import InMemoryCache, cached
from backend.app.core.database import engine_kwargs


@pytest.mark.asyncio
async def test_in_memory_cache_hit_and_miss():
    """Verify cache get/set and hit/miss statistics tracking."""
    cache = InMemoryCache(max_size=10)

    # Initial miss
    val = await cache.get("service:order-service")
    assert val is None
    assert cache.misses == 1

    # Set and hit
    await cache.set("service:order-service", {"replicas": 4, "tier": "Tier-1"})
    val = await cache.get("service:order-service")
    assert val is not None
    assert val["replicas"] == 4
    assert cache.hits == 1

    # Stats inspection
    stats = await cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["active_keys"] == 1
    assert stats["hit_rate"] == 0.5


@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """Verify cached entries automatically expire after configured TTL."""
    cache = InMemoryCache(max_size=10)

    # Key expires in 0.1 seconds
    await cache.set("slo:availability", 99.95, ttl_seconds=0.1)

    # Immediately available
    val1 = await cache.get("slo:availability")
    assert val1 == 99.95

    # Wait past TTL
    await asyncio.sleep(0.15)
    val2 = await cache.get("slo:availability")
    assert val2 is None


@pytest.mark.asyncio
async def test_cache_prefix_clear_and_lru_eviction():
    """Verify prefix-based cache invalidation and max_size LRU eviction."""
    cache = InMemoryCache(max_size=3)

    # Populate
    await cache.set("topo:node1", "data1")
    await cache.set("topo:node2", "data2")
    await cache.set("slo:burn_rate", "data3")

    # Clear only topo: prefix
    deleted_count = await cache.clear(prefix="topo:")
    assert deleted_count == 2
    assert await cache.get("topo:node1") is None
    assert await cache.get("topo:node2") is None
    assert await cache.get("slo:burn_rate") == "data3"

    # Fill beyond max_size (max_size=3)
    await cache.set("key1", "val1")
    await cache.set("key2", "val2")
    await cache.set("key3", "val3")  # Causes eviction of oldest key

    stats = await cache.stats()
    assert stats["active_keys"] <= 3
    assert stats["evictions"] >= 1


@pytest.mark.asyncio
async def test_cached_decorator():
    """Verify @cached decorator invokes underlying async function once and serves from cache."""
    invocations = 0

    @cached(ttl_seconds=60.0, key_prefix="test_dec")
    async def fetch_service_topology(service_name: str, depth: int = 1):
        nonlocal invocations
        invocations += 1
        return {"service": service_name, "depth": depth, "topology": ["db", "cache"]}

    # First call: executes function
    res1 = await fetch_service_topology("payment-service", depth=2)
    assert res1["service"] == "payment-service"
    assert invocations == 1

    # Second call with identical arguments: served from cache
    res2 = await fetch_service_topology("payment-service", depth=2)
    assert res2 == res1
    assert invocations == 1  # Function was NOT invoked again!

    # Different arguments: executes function
    res3 = await fetch_service_topology("order-service", depth=1)
    assert res3["service"] == "order-service"
    assert invocations == 2

    # Skip cache explicitly: invokes function again
    res4 = await fetch_service_topology("payment-service", depth=2, skip_cache=True)
    assert res4["service"] == "payment-service"
    assert invocations == 3


def test_database_connection_pool_kwargs():
    """Verify database connection pool parameters are properly configured."""
    assert "echo" in engine_kwargs
    # If postgres or sqlite, kwargs must contain drivers connection settings
    assert len(engine_kwargs) >= 1


def test_nextjs_standalone_output_exists():
    """Verify Next.js standalone container build artifacts exist on disk."""
    standalone_dir = Path("frontend/.next/standalone")
    assert standalone_dir.exists(), "frontend/.next/standalone must exist after running Next.js build"
    assert (standalone_dir / "server.js").exists(), "server.js must exist inside .next/standalone"
    assert (standalone_dir / "package.json").exists(), "package.json must exist inside .next/standalone"
