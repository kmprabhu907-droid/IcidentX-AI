"""
INCIDENTX AI - Cryptographic Audit Verifier & Tamper-Evident Ledger Engine
Implements SHA-256 blockchain-style hash chaining for enterprise audit immutability,
sensitive parameter redaction, and integrity verification.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.audit import AuditLog

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"
REDACTED_KEYS = {"password", "token", "secret", "authorization", "api_key", "credentials", "access_token", "refresh_token"}


def sanitize_audit_details(details: Optional[Union[str, Dict[str, Any]]]) -> Optional[str]:
    """
    Recursively redacts credentials and sensitive attributes before writing to the audit ledger.
    """
    if details is None:
        return None

    if isinstance(details, str):
        try:
            parsed = json.loads(details)
            if isinstance(parsed, dict):
                details = parsed
            else:
                return details
        except Exception:
            return details

    if isinstance(details, dict):
        sanitized = {}
        for k, v in details.items():
            if any(sensitive in k.lower() for sensitive in REDACTED_KEYS):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, dict):
                sanitized[k] = json.loads(sanitize_audit_details(v) or "{}")
            else:
                sanitized[k] = v
        return json.dumps(sanitized, sort_keys=True)

    return str(details)


def compute_audit_hash(
    prev_hash: str,
    timestamp_iso: str,
    actor_type: str,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: Optional[str] = None
) -> str:
    """
    Computes deterministic SHA-256 hash linking the audit entry to the preceding block.
    """
    payload = f"{prev_hash}|{timestamp_iso}|{actor_type}|{actor_id}|{action}|{resource_type}|{resource_id}|{details or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def record_audit_event(
    session: AsyncSession,
    actor_type: str,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    incident_id: Optional[str] = None,
    details: Optional[Union[str, Dict[str, Any]]] = None,
    ip_address: Optional[str] = None,
    organization_id: str = "default-org"
) -> AuditLog:
    """
    Appends a new cryptographically chained audit record to the persistent audit ledger.
    """
    # Fetch the latest audit record in this organization to get the previous hash
    query = (
        select(AuditLog)
        .where(AuditLog.organization_id == organization_id)
        .order_by(desc(AuditLog.created_at), desc(AuditLog.id))
        .limit(1)
    )
    result = await session.execute(query)
    last_record = result.scalar_one_or_none()

    prev_hash = last_record.checksum if (last_record and last_record.checksum) else GENESIS_HASH
    now = datetime.now(timezone.utc)
    timestamp_iso = now.isoformat()

    sanitized_details = sanitize_audit_details(details)

    checksum = compute_audit_hash(
        prev_hash=prev_hash,
        timestamp_iso=timestamp_iso,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=sanitized_details,
    )

    audit_entry = AuditLog(
        organization_id=organization_id,
        incident_id=incident_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=sanitized_details,
        ip_address=ip_address,
        prev_hash=prev_hash,
        checksum=checksum,
        created_at=now,
        updated_at=now,
    )
    session.add(audit_entry)
    return audit_entry


async def verify_audit_chain(
    session: AsyncSession,
    organization_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Audits the persistent ledger, verifying cryptographic SHA-256 linkage and detecting tampering.
    """
    query = select(AuditLog)
    if organization_id:
        query = query.where(AuditLog.organization_id == organization_id)
    query = query.order_by(AuditLog.created_at.asc(), AuditLog.id.asc())

    result = await session.execute(query)
    records: List[AuditLog] = list(result.scalars().all())

    expected_prev_hash = GENESIS_HASH
    tampered_records: List[str] = []
    broken_links: List[str] = []
    verified_count = 0
    legacy_count = 0

    for record in records:
        if not record.checksum:
            legacy_count += 1
            continue

        verified_count += 1
        # Check linkage to previous record
        if record.prev_hash != expected_prev_hash:
            broken_links.append(f"AuditRecord(id={record.id}, expected_prev={expected_prev_hash}, actual_prev={record.prev_hash})")

        # Recalculate checksum
        timestamp_str = record.created_at.replace(tzinfo=timezone.utc).isoformat() if record.created_at.tzinfo is None else record.created_at.isoformat()
        recalculated = compute_audit_hash(
            prev_hash=record.prev_hash or GENESIS_HASH,
            timestamp_iso=timestamp_str,
            actor_type=record.actor_type,
            actor_id=record.actor_id,
            action=record.action,
            resource_type=record.resource_type,
            resource_id=record.resource_id,
            details=record.details,
        )

        if recalculated != record.checksum:
            tampered_records.append(f"AuditRecord(id={record.id}, action={record.action}, expected_checksum={recalculated}, actual_checksum={record.checksum})")

        expected_prev_hash = record.checksum

    is_valid = (len(tampered_records) == 0 and len(broken_links) == 0)

    return {
        "is_valid": is_valid,
        "status": "SECURE_INTEGRITY_VERIFIED" if is_valid else "TAMPERING_DETECTED",
        "total_records": len(records),
        "verified_records": verified_count,
        "legacy_unhashed_records": legacy_count,
        "tampered_records": tampered_records,
        "broken_links": broken_links,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
