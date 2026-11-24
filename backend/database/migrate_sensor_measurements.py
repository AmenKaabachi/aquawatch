"""Safely migrate measurements to match their sensor types.

Run with ``python -m backend.database.migrate_sensor_measurements``.
The migration creates a timestamped backup before changing the database.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from backend.config import DATABASE_PATH, SCHEMA_PATH
from backend.database.connection import get_connection


def _create_backup(db_path: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = db_path.with_name(
        f"{db_path.stem}.backup-{timestamp}{db_path.suffix}"
    )
    if backup_path.exists():
        raise FileExistsError(f"Backup already exists: {backup_path}")

    source = sqlite3.connect(str(db_path))
    target = sqlite3.connect(str(backup_path))
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()

    backup = sqlite3.connect(f"file:{backup_path.as_posix()}?mode=ro", uri=True)
    source = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        integrity = backup.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"Backup integrity check failed: {integrity}")
        if backup.execute("SELECT COUNT(*) FROM measurements").fetchone()[0] != (
            source.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
        ):
            raise RuntimeError("Backup measurement count does not match source")
    finally:
        backup.close()
        source.close()
    return backup_path


def migrate_sensor_measurements(
    db_path: Optional[Path] = None,
) -> Dict[str, object]:
    """Null non-applicable metric values without replacing or deleting rows."""
    path = Path(db_path or DATABASE_PATH)
    if not path.is_file():
        raise FileNotFoundError(f"Database does not exist: {path}")

    backup_path = _create_backup(path)
    conn = get_connection(path)
    try:
        # Install the type-validation triggers on databases created by older code.
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        conn.execute("BEGIN IMMEDIATE")
        original_rows = conn.execute(
            """
            SELECT id, sensor_id, timestamp, quality_status, data_origin, created_at
            FROM measurements
            ORDER BY id
            """
        ).fetchall()
        original_sensor_types = conn.execute(
            "SELECT id, sensor_type FROM sensors ORDER BY id"
        ).fetchall()

        conn.execute(
            """
            UPDATE measurements
            SET flow_m3_h = NULL
            WHERE sensor_id IN (
                SELECT id FROM sensors WHERE sensor_type = 'pressure'
            )
            """
        )
        conn.execute(
            """
            UPDATE measurements
            SET pressure_bar = NULL
            WHERE sensor_id IN (
                SELECT id FROM sensors WHERE sensor_type = 'flow'
            )
            """
        )

        invalid_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM measurements m
            JOIN sensors s ON s.id = m.sensor_id
            WHERE (s.sensor_type = 'pressure'
                   AND (m.pressure_bar IS NULL OR m.flow_m3_h IS NOT NULL))
               OR (s.sensor_type = 'flow'
                   AND (m.pressure_bar IS NOT NULL OR m.flow_m3_h IS NULL))
               OR (s.sensor_type = 'combined'
                   AND (m.pressure_bar IS NULL OR m.flow_m3_h IS NULL))
            """
        ).fetchone()[0]
        if invalid_count:
            raise RuntimeError(f"{invalid_count} invalid measurement rows remain")

        migrated_rows = conn.execute(
            """
            SELECT id, sensor_id, timestamp, quality_status, data_origin, created_at
            FROM measurements
            ORDER BY id
            """
        ).fetchall()
        if [tuple(row) for row in original_rows] != [
            tuple(row) for row in migrated_rows
        ]:
            raise RuntimeError("Measurement identifiers or metadata changed")

        foreign_key_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise RuntimeError(f"Foreign-key check failed: {foreign_key_errors}")

        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"Database integrity check failed: {integrity}")

        counts_by_type = {name: 0 for name in ("pressure", "flow", "combined")}
        for row in conn.execute(
            """
            SELECT s.sensor_type, COUNT(*)
            FROM measurements m
            JOIN sensors s ON s.id = m.sensor_id
            GROUP BY s.sensor_type
            """
        ):
            counts_by_type[row[0]] = row[1]

        null_counts = conn.execute(
            """
            SELECT SUM(pressure_bar IS NULL), SUM(flow_m3_h IS NULL)
            FROM measurements
            """
        ).fetchone()
        conn.commit()
        return {
            "backup_path": backup_path,
            "measurement_count": len(original_rows),
            "sensor_types": [tuple(row) for row in original_sensor_types],
            "counts_by_type": counts_by_type,
            "pressure_nulls": null_counts[0] or 0,
            "flow_nulls": null_counts[1] or 0,
            "integrity": integrity,
        }
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    result = migrate_sensor_measurements()
    print(f"Backup: {result['backup_path']}")
    print(f"Measurements preserved: {result['measurement_count']}")
    print(f"Measurements by type: {result['counts_by_type']}")
    print(
        "NULL values — pressure: "
        f"{result['pressure_nulls']}, flow: {result['flow_nulls']}"
    )
    print(f"Integrity check: {result['integrity']}")
