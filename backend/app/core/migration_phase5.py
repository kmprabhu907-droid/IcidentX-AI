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
        
        # Add any newly introduced columns to anomaly_records
        cols_to_add = [
            ("ewma_value", "FLOAT"),
            ("trend_slope", "FLOAT"),
            ("status", "VARCHAR(30) DEFAULT 'ACTIVE'"),
            ("observation_count", "INTEGER DEFAULT 1"),
            ("first_observed_at", "TIMESTAMP"),
            ("last_observed_at", "TIMESTAMP"),
        ]
        for col_name, col_def in cols_to_add:
            try:
                await conn.execute(text(f"ALTER TABLE anomaly_records ADD COLUMN {col_name} {col_def}"))
                logger.info(f"Added column {col_name} to anomaly_records")
            except Exception:
                # Column already exists
                pass

        # Add any newly introduced columns to regression_records
        regression_cols_to_add = [
            ("current_incident_id", "VARCHAR(36)"),
            ("affected_services", "TEXT DEFAULT '[]'"),
            ("matching_incident_ids", "TEXT DEFAULT '[]'"),
            ("pre_incident_value", "FLOAT"),
            ("similarity_score", "FLOAT DEFAULT 0.0"),
            ("classification", "VARCHAR(30) DEFAULT 'POSSIBLE_REGRESSION'"),
            ("evidence", "TEXT"),
            ("comparison_windows", "TEXT"),
            ("previous_remediation_ids", "TEXT DEFAULT '[]'"),
            ("explanation", "TEXT"),
            ("data_source", "VARCHAR(20) DEFAULT 'SIMULATED'"),
            ("first_observed_at", "TIMESTAMP"),
            ("last_observed_at", "TIMESTAMP"),
        ]
        for col_name, col_def in regression_cols_to_add:
            try:
                await conn.execute(text(f"ALTER TABLE regression_records ADD COLUMN {col_name} {col_def}"))
                logger.info(f"Added column {col_name} to regression_records")
            except Exception:
                # Column already exists
                pass

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
