"""
INCIDENTX AI - Phase 9 Database Migration Helper
Synchronizes tables with Phase 9 Central Incident Lifecycle, Alert Ingestion,
Timeline actors, and Incident Ownership models.
"""

from sqlalchemy import text
from backend.app.core.database import Base, engine
from backend.app.core.logging import logger
import backend.app.models  # noqa: F401


async def run_phase9_migration():
    """
    Safely creates all Phase 9 database tables if missing (alerts, incident_assignments),
    and adds lifecycle, ownership, and timeline actor columns to existing tables.
    """
    logger.info("Starting Phase 9 incident command center schema synchronization...")
    async with engine.begin() as conn:
        # Create any missing tables defined in Base.metadata (alerts, incident_assignments)
        await conn.run_sync(Base.metadata.create_all)

        # Add new columns to incidents table if missing
        incident_cols = [
            ("incidents", "priority", "VARCHAR(20) DEFAULT 'HIGH'"),
            ("incidents", "environment", "VARCHAR(30) DEFAULT 'DEMOMESH'"),
            ("incidents", "source", "VARCHAR(50) DEFAULT 'MANUAL'"),
            ("incidents", "fingerprint", "VARCHAR(64)"),
            ("incidents", "acknowledged_at", "TIMESTAMP"),
            ("incidents", "acknowledged_by", "VARCHAR(100)"),
            ("incidents", "closed_at", "TIMESTAMP"),
            ("incidents", "owner_id", "VARCHAR(100)"),
            ("incidents", "owner_name", "VARCHAR(100)"),
            ("incidents", "assigned_team", "VARCHAR(100) DEFAULT 'Platform SRE'"),
            ("incidents", "oncall_responder", "VARCHAR(100) DEFAULT 'IncidentX AI (Tier-1)'"),
            ("incidents", "escalation_status", "VARCHAR(30) DEFAULT 'NORMAL'"),
            ("incidents", "escalation_deadline", "TIMESTAMP"),
            ("incidents", "is_escalated", "BOOLEAN DEFAULT 0"),
            ("timeline_events", "actor", "VARCHAR(100) DEFAULT 'SYSTEM'"),
            ("timeline_events", "actor_type", "VARCHAR(30) DEFAULT 'SYSTEM'"),
        ]

        for table, col, col_def in incident_cols:
            try:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"))
                logger.info(f"[Phase9 Migration] Added column {col} to {table}")
            except Exception:
                # Column already exists
                pass

        logger.info("[Phase9 Migration] Schema synchronization completed successfully.")
