"""
INCIDENTX AI - Automated Disaster Recovery Restoration Script (Stage 6.6)
Validates SHA256 integrity checksum before safely restoring persistent database state.
"""

import hashlib
from pathlib import Path
import shutil
import sqlite3
from typing import Any, Dict


def verify_and_restore(
    backup_file: Path,
    target_db_path: Path = Path("incidentx.db"),
    checksum_file: Path = None,
) -> Dict[str, Any]:
    """
    Validates SHA256 checksum against accompanying .sha256 file,
    and safely restores the database snapshot.
    """
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file '{backup_file}' does not exist.")

    if checksum_file is None:
        checksum_file = backup_file.parent / f"{backup_file.name}.sha256"

    if checksum_file.exists():
        with open(checksum_file, "r", encoding="utf-8") as f:
            line = f.readline().strip()
            expected_checksum = line.split()[0]

        h = hashlib.sha256()
        with open(backup_file, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        actual_checksum = h.hexdigest()

        if actual_checksum.lower() != expected_checksum.lower():
            raise ValueError(
                f"Checksum mismatch for '{backup_file.name}'! "
                f"Expected: {expected_checksum}, Actual: {actual_checksum}. "
                f"Aborting restore to prevent corrupted data loading."
            )

    # Perform restore via copy
    target_db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_file, target_db_path)

    # Verify integrity of restored database using SQLite PRAGMA
    conn = sqlite3.connect(str(target_db_path))
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check;")
    check_result = cursor.fetchone()[0]
    conn.close()

    if check_result != "ok":
        raise RuntimeError(f"Database PRAGMA integrity check failed: '{check_result}'")

    return {
        "status": "restored",
        "restored_from": str(backup_file),
        "target_path": str(target_db_path),
        "integrity_check": check_result,
    }
