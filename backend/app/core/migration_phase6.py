"""
INCIDENTX AI - Phase 6 Database Migration Helper
Synchronizes tables with Phase 6 Enterprise Multi-Tenancy (Organizations, Memberships)
and adds tenant scoping columns (organization_id) to legacy tables.
"""

import asyncio
from sqlalchemy import text
from backend.app.core.database import Base, engine
from backend.app.core.logging import logger
import backend.app.models  # noqa: F401


async def run_phase6_migration():
    """
    Safely creates all Phase 6 database tables if missing (organizations, organization_memberships),
    and adds organization_id columns to existing tables.
    """
    logger.info("Starting Phase 6 multi-tenancy schema synchronization...")
    async with engine.begin() as conn:
        # Create any missing tables defined in Base.metadata
        await conn.run_sync(Base.metadata.create_all)

        # Add organization_id column to existing tables if missing
        tenant_cols = [
            ("incidents", "organization_id", "VARCHAR(36) DEFAULT 'default-org'"),
            ("remediation_actions", "organization_id", "VARCHAR(36) DEFAULT 'default-org'"),
            ("slo_definitions", "organization_id", "VARCHAR(36) DEFAULT 'default-org'"),
            ("users", "organization_id", "VARCHAR(36)"),
            ("audit_logs", "organization_id", "VARCHAR(36) DEFAULT 'default-org'"),
            ("audit_logs", "prev_hash", "VARCHAR(64)"),
            ("audit_logs", "checksum", "VARCHAR(64)"),
        ]

        for table, col, col_def in tenant_cols:
            try:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"))
                logger.info(f"Added column {col} to {table}")
            except Exception:
                # Column already exists
                pass

        # Verify organizations table
        try:
            res = await conn.execute(text("SELECT COUNT(*) FROM organizations"))
            cnt = res.scalar()
            logger.info(f"Verified 'organizations' table: {cnt} records.")
        except Exception as e:
            logger.warning(f"Could not verify organizations table: {e}")

    logger.info("Phase 6 database migration completed successfully.")


if __name__ == "__main__":
    asyncio.run(run_phase6_migration())
