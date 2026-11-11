"""
INCIDENTX AI - Stage 6.6 Fault Tolerance, Resilience & Disaster Recovery Tests
Verifies 3-state Circuit Breaker, exponential backoff retries with jitter,
Kubernetes health/readiness/startup probes, and hot backup/restore integrity.
"""

import asyncio
from pathlib import Path
import pytest
from httpx import AsyncClient
from backend.app.core.resilience import (
    CircuitBreaker,
    CircuitBreakerOpenException,
    CircuitBreakerState,
    with_retry,
)
from infrastructure.scripts.backup import create_backup
from infrastructure.scripts.restore import verify_and_restore


@pytest.mark.asyncio
async def test_circuit_breaker_closed_to_open_transition():
    """Circuit breaker transitions from CLOSED to OPEN after consecutive failures and fast-fails."""
    breaker = CircuitBreaker(name="test-llm", failure_threshold=3, recovery_timeout=0.5)

    calls = 0

    async def flaky_service():
        nonlocal calls
        calls += 1
        raise ConnectionError("Upstream timeout")

    # 3 failures trip the circuit
    for _ in range(3):
        with pytest.raises(ConnectionError):
            await breaker.call(flaky_service)

    assert breaker.state == CircuitBreakerState.OPEN
    assert calls == 3

    # 4th attempt should fast-fail with CircuitBreakerOpenException without invoking service
    with pytest.raises(CircuitBreakerOpenException) as exc_info:
        await breaker.call(flaky_service)

    assert "is OPEN" in str(exc_info.value)
    assert calls == 3  # Downstream was NOT invoked


@pytest.mark.asyncio
async def test_circuit_breaker_open_to_half_open_recovery():
    """Circuit breaker recovers from OPEN -> HALF_OPEN -> CLOSED on successful probes."""
    breaker = CircuitBreaker(
        name="test-api",
        failure_threshold=2,
        recovery_timeout=0.2,
        half_open_success_threshold=2,
    )

    async def fail_call():
        raise RuntimeError("Service failure")

    async def success_call():
        return "healthy-response"

    # Trip circuit to OPEN
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await breaker.call(fail_call)

    assert breaker.state == CircuitBreakerState.OPEN

    # Fast-fail while waiting
    with pytest.raises(CircuitBreakerOpenException):
        await breaker.call(success_call)

    # Wait for recovery timeout
    await asyncio.sleep(0.25)

    # First probe call transitions to HALF_OPEN and succeeds
    res1 = await breaker.call(success_call)
    assert res1 == "healthy-response"
    assert breaker.state == CircuitBreakerState.HALF_OPEN

    # Second probe call completes threshold and resets to CLOSED
    res2 = await breaker.call(success_call)
    assert res2 == "healthy-response"
    assert breaker.state == CircuitBreakerState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_failure_re_trips():
    """Failing during HALF_OPEN immediately re-trips state back to OPEN."""
    breaker = CircuitBreaker(
        name="test-webhook",
        failure_threshold=1,
        recovery_timeout=0.15,
        half_open_success_threshold=2,
    )

    async def fail_call():
        raise RuntimeError("Webhook endpoint unreachable")

    # Trip to OPEN
    with pytest.raises(RuntimeError):
        await breaker.call(fail_call)
    assert breaker.state == CircuitBreakerState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(0.2)

    # Probe fails -> immediately re-trips to OPEN
    with pytest.raises(RuntimeError):
        await breaker.call(fail_call)

    assert breaker.state == CircuitBreakerState.OPEN


@pytest.mark.asyncio
async def test_with_retry_decorator_recovers_after_transient_failure():
    """@with_retry retries transient errors and succeeds upon recovery."""
    attempts = 0

    @with_retry(max_attempts=3, base_delay=0.05, max_delay=0.2, jitter=False)
    async def transient_operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TimeoutError(f"Transient network glitch attempt {attempts}")
        return "operation-recovered"

    result = await transient_operation()
    assert result == "operation-recovered"
    assert attempts == 3


@pytest.mark.asyncio
async def test_with_retry_exceeds_max_attempts():
    """@with_retry raises final exception when errors persist beyond max_attempts."""
    attempts = 0

    @with_retry(max_attempts=2, base_delay=0.05, max_delay=0.1, jitter=False)
    async def persistent_failure():
        nonlocal attempts
        attempts += 1
        raise ValueError("Non-recoverable failure")

    with pytest.raises(ValueError, match="Non-recoverable failure"):
        await persistent_failure()

    assert attempts == 2


@pytest.mark.asyncio
async def test_kubernetes_probes(client: AsyncClient):
    """Verify Kubernetes liveness, readiness, and startup health endpoints."""
    # 1. Liveness Probe
    live_res = await client.get("/api/v1/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "alive"

    # 2. Readiness Probe
    ready_res = await client.get("/api/v1/health/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"
    assert ready_res.json()["subsystems"]["database"] == "ready"

    # 3. Startup Probe
    startup_res = await client.get("/api/v1/health/startup")
    assert startup_res.status_code == 200
    assert startup_res.json()["status"] == "started"


def test_disaster_recovery_backup_and_restore(tmp_path: Path):
    """Verify hot database snapshot generation, SHA256 manifest, and verified restoration."""
    import sqlite3

    # Create dummy source database with table
    source_db = tmp_path / "source_incidentx.db"
    conn = sqlite3.connect(str(source_db))
    conn.execute("CREATE TABLE test_incidents (id TEXT PRIMARY KEY, title TEXT);")
    conn.execute("INSERT INTO test_incidents VALUES ('1', 'Critical Outage');")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"

    # 1. Create backup
    manifest = create_backup(source_db_path=source_db, backup_dir=backup_dir)
    assert manifest["table_count"] >= 1
    assert "test_incidents" in manifest["tables"]
    assert manifest["tables"]["test_incidents"] == 1

    backup_file = backup_dir / manifest["backup_filename"]
    assert backup_file.exists()

    # 2. Restore to new destination
    restored_db = tmp_path / "restored_incidentx.db"
    restore_result = verify_and_restore(backup_file=backup_file, target_db_path=restored_db)
    assert restore_result["status"] == "restored"
    assert restore_result["integrity_check"] == "ok"

    # Verify content in restored database
    r_conn = sqlite3.connect(str(restored_db))
    r_cursor = r_conn.cursor()
    r_cursor.execute("SELECT title FROM test_incidents WHERE id='1';")
    assert r_cursor.fetchone()[0] == "Critical Outage"
    r_conn.close()

    # 3. Corrupted backup fails checksum check
    with open(backup_file, "ab") as f:
        f.write(b"corrupted_bytes")

    target_fail_db = tmp_path / "fail.db"
    with pytest.raises(ValueError, match="Checksum mismatch"):
        verify_and_restore(backup_file=backup_file, target_db_path=target_fail_db)
