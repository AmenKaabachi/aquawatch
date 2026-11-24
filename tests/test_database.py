"""Tests de la base de données AquaWatch.

Vérifie l'initialisation, la structure des tables,
les contraintes et l'idempotence du script d'initialisation.
"""

import sqlite3

import pytest

from backend.database.connection import get_connection
from backend.database.init_db import init_database


class TestDatabaseInitialization:
    """Tests d'initialisation de la base de données."""

    def test_init_succeeds(self, test_db_path):
        """L'initialisation doit retourner True."""
        result = init_database(test_db_path)
        assert result is True

    def test_tables_exist(self, test_db):
        """Toutes les tables attendues doivent exister."""
        cursor = test_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}
        expected = {"governorates", "monitoring_zones", "sensors", "measurements"}
        assert expected.issubset(tables), f"Tables manquantes : {expected - tables}"

    def test_foreign_keys_enabled(self, test_db):
        """Les clés étrangères doivent être activées."""
        cursor = test_db.execute("PRAGMA foreign_keys")
        assert cursor.fetchone()[0] == 1

    def test_four_governorates(self, test_db):
        """Exactement 4 gouvernorats doivent être insérés."""
        cursor = test_db.execute("SELECT COUNT(*) FROM governorates")
        assert cursor.fetchone()[0] == 4

    def test_governorate_names(self, test_db):
        """Les gouvernorats attendus doivent exister."""
        cursor = test_db.execute("SELECT name FROM governorates ORDER BY name")
        names = [row[0] for row in cursor.fetchall()]
        assert names == ["Ariana", "Ben Arous", "Manouba", "Tunis"]

    def test_eight_monitoring_zones(self, test_db):
        """Exactement 8 zones de surveillance doivent être créées."""
        cursor = test_db.execute("SELECT COUNT(*) FROM monitoring_zones")
        assert cursor.fetchone()[0] == 8

    def test_two_zones_per_governorate(self, test_db):
        """Chaque gouvernorat doit avoir exactement 2 zones."""
        cursor = test_db.execute(
            """
            SELECT governorate_id, COUNT(*) AS zone_count
            FROM monitoring_zones
            GROUP BY governorate_id
            """
        )
        for row in cursor.fetchall():
            assert row[1] == 2, (
                f"Le gouvernorat {row[0]} a {row[1]} zones au lieu de 2"
            )

    def test_twentyfour_sensors(self, test_db):
        """24 capteurs doivent être créés (3 par zone × 8 zones)."""
        cursor = test_db.execute("SELECT COUNT(*) FROM sensors")
        assert cursor.fetchone()[0] == 24

    def test_three_sensors_per_zone(self, test_db):
        """Chaque zone doit avoir exactement 3 capteurs."""
        cursor = test_db.execute(
            """
            SELECT zone_id, COUNT(*) AS sensor_count
            FROM sensors
            GROUP BY zone_id
            """
        )
        for row in cursor.fetchall():
            assert row[1] == 3, (
                f"La zone {row[0]} a {row[1]} capteurs au lieu de 3"
            )

    def test_sensors_have_valid_zones(self, test_db):
        """Tous les capteurs doivent être associés à des zones valides."""
        cursor = test_db.execute(
            """
            SELECT s.id FROM sensors s
            LEFT JOIN monitoring_zones z ON s.zone_id = z.id
            WHERE z.id IS NULL
            """
        )
        orphans = cursor.fetchall()
        assert len(orphans) == 0, "Des capteurs orphelins ont été trouvés"

    def test_foreign_key_enforcement(self, test_db):
        """L'insertion avec un zone_id invalide doit être rejetée."""
        with pytest.raises(Exception):
            test_db.execute(
                "INSERT INTO sensors (zone_id, name, sensor_type) "
                "VALUES (999, 'capteur_invalide', 'pressure')"
            )

    @pytest.mark.parametrize(
        "sensor_id,pressure,flow",
        [
            (1, 3.5, None),
            (2, None, 180.0),
            (3, 3.4, 175.0),
        ],
    )
    def test_measurement_insert_matches_sensor_type(
        self, test_db, sensor_id, pressure, flow
    ):
        test_db.execute(
            """
            INSERT INTO measurements
                (sensor_id, timestamp, pressure_bar, flow_m3_h)
            VALUES (?, '2026-01-01T00:00:00Z', ?, ?)
            """,
            (sensor_id, pressure, flow),
        )
        test_db.commit()
        row = test_db.execute(
            "SELECT pressure_bar, flow_m3_h FROM measurements WHERE sensor_id = ?",
            (sensor_id,),
        ).fetchone()
        assert row[0] == pressure
        assert row[1] == flow

    @pytest.mark.parametrize(
        "sensor_id,pressure,flow",
        [
            (1, 3.5, 180.0),
            (1, None, None),
            (2, 3.5, 180.0),
            (2, None, None),
            (3, 3.5, None),
            (3, None, 180.0),
        ],
    )
    def test_invalid_measurement_combinations_rejected(
        self, test_db, sensor_id, pressure, flow
    ):
        with pytest.raises(
            sqlite3.IntegrityError, match="measurement values do not match"
        ):
            test_db.execute(
                """
                INSERT INTO measurements
                    (sensor_id, timestamp, pressure_bar, flow_m3_h)
                VALUES (?, '2026-01-01T00:00:00Z', ?, ?)
                """,
                (sensor_id, pressure, flow),
            )

    def test_sensor_type_change_cannot_invalidate_existing_measurements(self, test_db):
        test_db.execute(
            """
            INSERT INTO measurements
                (sensor_id, timestamp, pressure_bar, flow_m3_h)
            VALUES (1, '2026-01-01T00:00:00Z', 3.5, NULL)
            """
        )
        with pytest.raises(
            sqlite3.IntegrityError,
            match="sensor type conflicts with existing measurements",
        ):
            test_db.execute("UPDATE sensors SET sensor_type = 'combined' WHERE id = 1")

    def test_idempotent_initialization(self, test_db_path):
        """Exécuter l'init deux fois ne doit pas dupliquer les données."""
        init_database(test_db_path)
        init_database(test_db_path)

        conn = get_connection(test_db_path)
        try:
            assert conn.execute("SELECT COUNT(*) FROM governorates").fetchone()[0] == 4
            assert conn.execute("SELECT COUNT(*) FROM monitoring_zones").fetchone()[0] == 8
            assert conn.execute("SELECT COUNT(*) FROM sensors").fetchone()[0] == 24
        finally:
            conn.close()

    def test_indexes_exist(self, test_db):
        """Les index de performance doivent être créés."""
        cursor = test_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name LIKE 'idx_%'"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        expected = {
            "idx_measurements_sensor_id",
            "idx_measurements_timestamp",
            "idx_measurements_sensor_timestamp",
            "idx_sensors_zone_id",
            "idx_zones_governorate_id",
        }
        assert expected.issubset(indexes), f"Index manquants : {expected - indexes}"
