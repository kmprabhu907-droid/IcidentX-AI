"""
INCIDENTX AI - Phase 10 Database Migration Helper
Synchronizes tables with Phase 10 Advanced Multi-Agent Investigation Engine,
Shared Evidence Intelligence, and Collaborative Protocol models.
"""

from sqlalchemy import text
from backend.app.core.database import Base, engine
from backend.app.core.logging import logger
import backend.app.models  # noqa: F401


async def run_phase10_migration():
    """
    Safely creates all Phase 10 database tables if missing (investigation_messages),
    and adds shared evidence metadata and fact-vs-interpretation columns to evidence table.
    """
    logger.info("Starting Phase 10 multi-agent investigation schema synchronization...")
    async with engine.begin() as conn:
        # Create any missing tables defined in Base.metadata (e.g. investigation_messages)
        await conn.run_sync(Base.metadata.create_all)

        # Add new columns to evidence table if missing
        evidence_cols = [
            ("evidence", "investigation_id", "VARCHAR(36)"),
            ("evidence", "evidence_category", "VARCHAR(50) DEFAULT 'METRICS'"),
            ("evidence", "source_agent", "VARCHAR(50)"),
            ("evidence", "is_fact", "BOOLEAN DEFAULT 1"),
            ("evidence", "environment", "VARCHAR(20) DEFAULT 'DEMOMESH'"),
            ("evidence", "deduplication_hash", "VARCHAR(64)"),
        ]

        for table, col, col_def in evidence_cols:
            try:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"))
                logger.info(f"[Phase10 Migration] Added column {col} to {table}")
            except Exception:
                # Column already exists
                pass

        logger.info("[Phase10 Migration] Schema synchronization completed successfully.")
