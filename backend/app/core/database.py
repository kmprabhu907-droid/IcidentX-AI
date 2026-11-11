"""
INCIDENTX AI - Asynchronous Database Management
Configures SQLAlchemy async engine, session factory, and base model mixins.
Supports both PostgreSQL (asyncpg) and SQLite (aiosqlite) seamlessly.
"""

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator
from sqlalchemy import DateTime, String, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from backend.app.core.config import settings
from backend.app.core.logging import logger

# Engine kwargs based on driver
engine_kwargs = {"echo": settings.DATABASE_ECHO}

if "sqlite" in settings.DATABASE_URL:
    # SQLite async compatibility
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL async connection pooling
    engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 1800
    engine_kwargs["pool_timeout"] = 30

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy entities."""
    pass


class TimestampMixin:
    """Standardized timestamp mixin for audit trails."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class UUIDMixin:
    """Standardized UUID primary key mixin."""
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
        index=True
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection yield for FastAPI request lifecycle."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> bool:
    """Verifies active connectivity to the underlying database."""
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
