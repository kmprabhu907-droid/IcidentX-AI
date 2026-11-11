"""
INCIDENTX AI - Phase 5 Database Migration Helper
Synchronizes SQLite and PostgreSQL tables with Phase 5 Telemetry Rollups,
SLOs, Anomaly Records, Regression Records, and Predictive Warnings.
"""

import asyncio
from sqlalchemy import text
from backend.app.core.database import Base, engine
from backend.app.core.logging import logger
import backend.app.models  # noqa: F401


async def run_phase5_migration():
    """
    Safely creates all Phase 5 database tables if missing,
    preserving existing tables and rows.
    """
    logger.info("Starting Phase 5 schema synchronization...")
    async with engine.begin() as conn:
        # Create any missing tables defined in Base.metadata
        await conn.run_sync(Base.metadata.create_all)
        
        # Verify tables exist
        tables_to_check = [
            "metric_rollups",
            "slo_definitions",
            "slo_measurements",
            "anomaly_records",
            "regression_records",
            "predictive_warnings",
        ]
        for tbl in tables_to_check:
            try:
                res = await conn.execute(text(f"SELECT COUNT(*) FROM {tbl}"))
                cnt = res.scalar()
                logger.info(f"Verified table '{tbl}': {cnt} existing records.")
            except Exception as e:
                logger.warning(f"Could not verify table '{tbl}': {e}")

    logger.info("Phase 5 database migration completed successfully.")


if __name__ == "__main__":
    asyncio.run(run_phase5_migration())
