"""
INCIDENTX AI - Phase 4 Database Migration Helper
Synchronizes SQLite and PostgreSQL tables with Phase 4 Remediation columns and policies.
"""

import asyncio
from sqlalchemy import text
from backend.app.core.database import Base, engine
from backend.app.core.logging import logger
import backend.app.models  # noqa: F401


async def run_phase4_migration():
    async with engine.begin() as conn:
        # 1. Create any missing tables (e.g. remediation_policies)
        await conn.run_sync(Base.metadata.create_all)

        # 2. Add missing columns to remediation_actions if table already existed from Phase 1
        cols_to_add = [
            ("action_id", "VARCHAR(100) DEFAULT 'act-remediation'"),
            ("name", "VARCHAR(255) DEFAULT 'Remediation Action'"),
            ("description", "TEXT DEFAULT ''"),
            ("target_service_name", "VARCHAR(100) DEFAULT 'unknown-service'"),
            ("parameters", "TEXT DEFAULT '{}'"),
            ("preconditions", "TEXT DEFAULT '[]'"),
            ("expected_outcome", "TEXT DEFAULT ''"),
            ("risk_level", "VARCHAR(20) DEFAULT 'LOW'"),
            ("estimated_cost", "VARCHAR(20) DEFAULT 'LOW'"),
            ("expected_benefit", "FLOAT DEFAULT 0.85"),
            ("recommendation_reason", "TEXT DEFAULT ''"),
            ("contraindications", "TEXT DEFAULT '[]'"),
            ("execution_mode", "VARCHAR(30) DEFAULT 'RECOMMENDATION_ONLY'"),
            ("idempotency_key", "VARCHAR(128)"),
            ("timeout_seconds", "INTEGER DEFAULT 15"),
            ("approved_at", "TIMESTAMP"),
            ("approval_comment", "TEXT"),
            ("executed_at", "TIMESTAMP"),
            ("execution_duration_ms", "INTEGER"),
            ("execution_log", "TEXT"),
            ("snapshot_before", "TEXT"),
            ("snapshot_after", "TEXT"),
            ("verification_status", "VARCHAR(30) DEFAULT 'PENDING'"),
            ("verification_details", "TEXT"),
            ("rollback_status", "VARCHAR(30) DEFAULT 'NONE'"),
            ("rollback_log", "TEXT"),
            ("error_message", "TEXT"),
            ("retry_count", "INTEGER DEFAULT 0"),
        ]

        for col_name, col_def in cols_to_add:
            try:
                await conn.execute(text(f"ALTER TABLE remediation_actions ADD COLUMN {col_name} {col_def}"))
                logger.info(f"Added column {col_name} to remediation_actions")
            except Exception:
                # Column already exists
                pass

        logger.info("Phase 4 schema synchronization complete.")


if __name__ == "__main__":
    asyncio.run(run_phase4_migration())
