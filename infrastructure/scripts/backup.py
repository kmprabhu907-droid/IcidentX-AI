"""
INCIDENTX AI - Automated Disaster Recovery & Backup Script (Stage 6.6)
Performs consistent hot-snapshots of the incident persistence tier with SHA256 integrity validation.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Dict


def compute_sha256(file_path: Path) -> str:
    """Computes SHA256 checksum of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def create_backup(
    source_db_path: Path = Path("incidentx.db"),
    backup_dir: Path = Path("backups"),
) -> Dict[str, Any]:
    """
    Creates a point-in-time consistent snapshot of the SQLite database
    using the official online backup API, and outputs checksum and manifest.
    """
    if not source_db_path.exists():
        raise FileNotFoundError(f"Source database file '{source_db_path}' does not exist.")

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"incidentx_snapshot_{timestamp_str}.db"
    backup_path = backup_dir / backup_filename
    checksum_path = backup_dir / f"{backup_filename}.sha256"
    manifest_path = backup_dir / f"{backup_filename}.manifest.json"

    # 1. Hot online backup using sqlite3 backup API
    src_conn = sqlite3.connect(str(source_db_path))
    dest_conn = sqlite3.connect(str(backup_path))
    with dest_conn:
        src_conn.backup(dest_conn)
    dest_conn.close()

    # Query table counts for the manifest
    cursor = src_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall() if not r[0].startswith("sqlite_")]
    table_counts = {}
    for tbl in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
            table_counts[tbl] = cursor.fetchone()[0]
        except Exception:
            pass
    src_conn.close()

    # 2. Compute SHA256 checksum
    checksum = compute_sha256(backup_path)
    with open(checksum_path, "w", encoding="utf-8") as f:
        f.write(f"{checksum}  {backup_filename}\n")

    # 3. Write metadata manifest
    manifest_data = {
        "backup_filename": backup_filename,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": checksum,
        "size_bytes": backup_path.stat().st_size,
        "table_count": len(tables),
        "tables": table_counts,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    return manifest_data


if __name__ == "__main__":
    result = create_backup()
    print(f"Backup created successfully: {result['backup_filename']} (SHA256: {result['sha256'][:16]}...)")
