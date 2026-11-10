"""
INCIDENTX AI - Services & Dependencies API Router
"""

from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.exceptions import EntityConflictException, EntityNotFoundException
from backend.app.models.service import Service, ServiceDependency
from backend.app.repositories.service import ServiceDependencyRepository, ServiceRepository
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.service import (
    DependencyCreate,
    DependencyResponse,
    ServiceCreate,
    ServiceResponse,
)

router = APIRouter(tags=["Services & Topology"])


@router.post("/services", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    payload: ServiceCreate,
    db: AsyncSession = Depends(get_db)
):
    repo = ServiceRepository(db)
    existing = await repo.get_by_name(payload.name)
    if existing:
        raise EntityConflictException(f"Service with name '{payload.name}' already exists.")

    service = Service(
        name=payload.name,
        tier=payload.tier,
        service_type=payload.service_type,
        language=payload.language,
        health_status=payload.health_status,
        repository_url=payload.repository_url,
    )
    return await repo.create(service)


@router.get("/services", response_model=PaginatedResponse[ServiceResponse])
async def list_services(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    repo = ServiceRepository(db)
    items, total = await repo.list_paginated(page=page, page_size=page_size)
    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/services/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: str,
    db: AsyncSession = Depends(get_db)
):
    repo = ServiceRepository(db)
    service = await repo.get_by_id(service_id)
    if not service:
        raise EntityNotFoundException("Service", service_id)
    return service


@router.post("/dependencies", response_model=DependencyResponse, status_code=status.HTTP_201_CREATED)
async def create_dependency(
    payload: DependencyCreate,
    db: AsyncSession = Depends(get_db)
):
    service_repo = ServiceRepository(db)
    dep_repo = ServiceDependencyRepository(db)

    # Validate source and target exist
    source = await service_repo.get_by_id(payload.source_service_id)
    if not source:
        raise EntityNotFoundException("Source Service", payload.source_service_id)

    target = await service_repo.get_by_id(payload.target_service_id)
    if not target:
        raise EntityNotFoundException("Target Service", payload.target_service_id)

    if payload.source_service_id == payload.target_service_id:
        raise EntityConflictException("A service cannot depend on itself.")

    existing = await dep_repo.get_by_endpoints(payload.source_service_id, payload.target_service_id)
    if existing:
        raise EntityConflictException("Dependency link between these services already exists.")

    dependency = ServiceDependency(
        source_service_id=payload.source_service_id,
        target_service_id=payload.target_service_id,
        protocol=payload.protocol,
        is_critical=payload.is_critical,
    )
    return await dep_repo.create(dependency)


@router.get("/dependencies", response_model=PaginatedResponse[DependencyResponse])
async def list_dependencies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    dep_repo = ServiceDependencyRepository(db)
    items, total = await dep_repo.list_paginated(page=page, page_size=page_size)
    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )
