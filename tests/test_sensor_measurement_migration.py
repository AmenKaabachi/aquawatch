import sqlite3

import pytest

from backend.database.connection import get_connection
from backend.database.init_db import init_database
from backend.database.migrate_sensor_measurements import (
    migrate_sensor_measurements,
)


def _create_legacy_measurements(db_path):
    init_database(db_path)
    conn = get_connection(db_path)
    conn.execute("DROP TRIGGER trg_measurements_sensor_type_insert")
    conn.execute("DROP TRIGGER trg_measurements_sensor_type_update")
    conn.executemany(
        """
        INSERT INTO measurements
            (sensor_id, timestamp, pressure_bar, flow_m3_h)
        VALUES (?, ?, ?, ?)
        """,
        [
            (1, "2026-01-01T00:00:00Z", 3.5, 180.0),
            (2, "2026-01-01T00:00:00Z", 3.6, 181.0),
            (3, "2026-01-01T00:00:00Z", 3.7, 182.0),
        ],
    )
    conn.commit()
    conn.close()


def test_migration_preserves_rows_and_is_idempotent(test_db_path):
    _create_legacy_measurements(test_db_path)
    conn = get_connection(test_db_path)
    original_rows = conn.execute(
        "SELECT id, sensor_id, timestamp FROM measurements ORDER BY id"
    ).fetchall()
    conn.close()

    result = migrate_sensor_measurements(test_db_path)
    assert result["measurement_count"] == 3
    assert result["counts_by_type"] == {
        "pressure": 1,
        "flow": 1,
        "combined": 1,
    }
    assert result["pressure_nulls"] == 1
    assert result["flow_nulls"] == 1
    assert result["integrity"] == "ok"

    backup = sqlite3.connect(f"file:{result['backup_path'].as_posix()}?mode=ro", uri=True)
    try:
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert backup.execute("SELECT COUNT(*) FROM measurements").fetchone()[0] == 3
    finally:
        backup.close()

    conn = get_connection(test_db_path)
    migrated_rows = conn.execute(
        """
        SELECT id, sensor_id, timestamp, pressure_bar, flow_m3_h
        FROM measurements ORDER BY id
        """
    ).fetchall()
    assert [tuple(row[:3]) for row in migrated_rows] == [
        tuple(row) for row in original_rows
    ]
    assert tuple(migrated_rows[0][3:]) == (3.5, None)
    assert tuple(migrated_rows[1][3:]) == (None, 181.0)
    assert tuple(migrated_rows[2][3:]) == (3.7, 182.0)
    conn.close()

    second_result = migrate_sensor_measurements(test_db_path)
    assert second_result["measurement_count"] == 3
    assert second_result["pressure_nulls"] == 1
    assert second_result["flow_nulls"] == 1


def test_migration_rolls_back_partial_updates(test_db_path):
    _create_legacy_measurements(test_db_path)
    conn = get_connection(test_db_path)
    conn.execute(
        """
        CREATE TRIGGER fail_flow_migration
        BEFORE UPDATE ON measurements
        WHEN OLD.sensor_id = 2
        BEGIN
            SELECT RAISE(ABORT, 'forced migration failure');
        END
        """
    )
    conn.commit()
    conn.close()

    with pytest.raises(sqlite3.IntegrityError, match="forced migration failure"):
        migrate_sensor_measurements(test_db_path)

    conn = get_connection(test_db_path)
    rows = conn.execute(
        "SELECT pressure_bar, flow_m3_h FROM measurements ORDER BY id"
    ).fetchall()
    assert [tuple(row) for row in rows] == [
        (3.5, 180.0),
        (3.6, 181.0),
        (3.7, 182.0),
    ]
    conn.close()


def test_dashboard_displays_missing_measurement_as_unavailable():
    from dashboard.measurements import _format_measurement

    assert _format_measurement(None, "bar") == "—"
    assert _format_measurement(0.0, "bar") == "0.00 bar"
    assert _format_measurement(3.5) == "3.50"
