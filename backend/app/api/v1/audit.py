"""
INCIDENTX AI - Audit Logs API Router
Provides authenticated audit log inspection for operational accountability.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.repositories.audit import AuditLogRepository
from backend.app.schemas.audit import AuditLogResponse
from backend.app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/audit-logs", tags=["Audit & Governance"])


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    incident_id: Optional[str] = Query(default=None, description="Filter by incident UUID"),
    actor_type: Optional[str] = Query(default=None, description="Filter by actor type (USER, SYSTEM, AGENT)"),
    db: AsyncSession = Depends(get_db)
):
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
