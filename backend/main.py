"""
INCIDENTX AI - Application Entry Point
FastAPI master application configuring routers, middleware, exception handlers, and lifespan events.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from backend.app.core.config import settings
from backend.app.core.database import Base, check_db_health, engine
from backend.app.core.exceptions import (
    IncidentXException,
    generic_exception_handler,
    incidentx_exception_handler,
    validation_exception_handler,
)
from backend.app.core.logging import logger, setup_logging
from backend.app.middleware.request_id import RequestContextMiddleware
from backend.app.api.v1.router import api_v1_router
# Import all models to ensure DeclarativeBase metadata is complete
import backend.app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    setup_logging()
    logger.info(f"Initializing {settings.APP_NAME} v{settings.APP_VERSION} ({settings.APP_ENV})")

    # Ensure database schema exists (Alembic or auto-create)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema synchronized successfully.")

    # Start autonomous observability & detection engine
    from backend.app.services.observability.engine import observability_engine
    await observability_engine.start()
    logger.info("Observability and detection engine started.")

    # Start continuous observability telemetry collector (Phase 5 Stage 5.1)
    from backend.app.services.observability.collector import observability_collector
    await observability_collector.start()
    logger.info("Continuous telemetry collector started.")

    yield

    # Teardown sequence
    logger.info(f"Shutting down {settings.APP_NAME}...")
    await observability_collector.stop()
    await observability_engine.stop()
    await engine.dispose()
    logger.info("Database connection engine disposed cleanly.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Autonomous AI Incident Investigation and Self-Healing Platform API",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# 1. Custom Request Context & Timing Middleware
app.add_middleware(RequestContextMiddleware)

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Exception Handlers
app.add_exception_handler(IncidentXException, incidentx_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# 4. API Routers
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


# 5. Root & Direct Kubernetes Probes
@app.get("/", tags=["Root"])
async def root():
    return {
        "service": settings.APP_NAME,
        "tagline": "The Autonomous Reliability Intelligence System",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "docs_url": "/docs",
        "api_v1": settings.API_V1_PREFIX,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/healthz", tags=["Health"])
async def kubernetes_healthz():
    db_ok = await check_db_health()
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.APP_DEBUG,
    )
