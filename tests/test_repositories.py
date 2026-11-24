"""Tests des repositories.

Vérifie l'accès aux données des gouvernorats, zones,
capteurs et mesures, y compris les filtres.
"""

import pytest

from backend.repositories import (
    governorate_repository,
    measurement_repository,
    sensor_repository,
    zone_repository,
)
from backend.services import simulation_service


class TestGovernorateRepository:
    """Tests du repository des gouvernorats."""

    def test_get_all_returns_four(self, test_db):
        """Doit retourner exactement 4 gouvernorats."""
        govs = governorate_repository.get_all(test_db)
        assert len(govs) == 4

    def test_get_by_id_exists(self, test_db):
        """Doit retourner le gouvernorat Tunis pour l'ID 1."""
        gov = governorate_repository.get_by_id(test_db, 1)
        assert gov is not None
        assert gov["name"] == "Tunis"

    def test_get_by_id_not_found(self, test_db):
        """Doit retourner None pour un ID inexistant."""
        gov = governorate_repository.get_by_id(test_db, 999)
        assert gov is None

    def test_count(self, test_db):
        """Doit compter 4 gouvernorats."""
        assert governorate_repository.count(test_db) == 4

    def test_all_have_population(self, test_db):
        """Tous les gouvernorats doivent avoir une population."""
        govs = governorate_repository.get_all(test_db)
        for g in govs:
            assert g["population"] is not None
            assert g["population"] > 0


class TestZoneRepository:
    """Tests du repository des zones de surveillance."""

    def test_get_all_returns_eight(self, test_db):
        """Doit retourner exactement 8 zones."""
        zones = zone_repository.get_all(test_db)
        assert len(zones) == 8

    def test_get_by_governorate(self, test_db):
        """Doit retourner 2 zones pour chaque gouvernorat."""
        for gov_id in range(1, 5):
            zones = zone_repository.get_by_governorate(test_db, gov_id)
            assert len(zones) == 2

    def test_zones_include_governorate_name(self, test_db):
        """Les zones doivent contenir le nom du gouvernorat."""
        zones = zone_repository.get_all(test_db)
        valid_names = {"Tunis", "Ariana", "Ben Arous", "Manouba"}
        for z in zones:
            assert "governorate_name" in z
            assert z["governorate_name"] in valid_names

    def test_get_by_id(self, test_db):
        """Doit retourner la zone correcte par ID."""
        zone = zone_repository.get_by_id(test_db, 1)
        assert zone is not None
        assert zone["code"] == "TUN-Z1"

    def test_count_and_count_active(self, test_db):
        """Les compteurs doivent être cohérents."""
        total = zone_repository.count(test_db)
        active = zone_repository.count_active(test_db)
        assert total == 8
        assert active == 8  # toutes actives au départ


class TestSensorRepository:
    """Tests du repository des capteurs."""

    def test_get_all_returns_twentyfour(self, test_db):
        """Doit retourner 24 capteurs."""
        sensors = sensor_repository.get_all(test_db)
        assert len(sensors) == 24

    def test_get_by_zone(self, test_db):
        """Doit retourner 3 capteurs par zone."""
        for zone_id in range(1, 9):
            sensors = sensor_repository.get_by_zone(test_db, zone_id)
            assert len(sensors) == 3

    def test_get_active_all(self, test_db):
        """Tous les capteurs doivent être actifs au départ."""
        active = sensor_repository.get_active(test_db)
        assert len(active) == 24

    def test_sensors_have_zone_info(self, test_db):
        """Les capteurs doivent contenir les infos de zone."""
        sensors = sensor_repository.get_all(test_db)
        for s in sensors:
            assert "zone_name" in s
            assert "zone_code" in s

    def test_sensor_types(self, test_db):
        """Chaque zone doit avoir des capteurs de types variés."""
        sensors = sensor_repository.get_by_zone(test_db, 1)
        types = {s["sensor_type"] for s in sensors}
        assert types == {"pressure", "flow", "combined"}


class TestMeasurementRepository:
    """Tests du repository des mesures."""

    def test_insert_and_retrieve(self, test_db):
        """Doit pouvoir insérer et récupérer des mesures."""
        test_data = [
            {
                "sensor_id": 1,
                "timestamp": "2024-01-15T10:00:00Z",
                "pressure_bar": 3.5,
                "flow_m3_h": None,
                "quality_status": "valid",
                "data_origin": "SIMULATED",
            }
        ]
        inserted = measurement_repository.insert_many(test_db, test_data)
        assert inserted == 1

        recent = measurement_repository.get_recent(test_db, limit=10)
        assert len(recent) >= 1
        assert recent[0]["pressure_bar"] == 3.5
        assert recent[0]["flow_m3_h"] is None

    def test_nullable_values_round_trip_as_none(self, test_db):
        """SQLite NULL values remain Python None through repository reads."""
        measurement_repository.insert_many(
            test_db,
            [
                {
                    "sensor_id": 1,
                    "timestamp": "2024-01-15T10:00:00Z",
                    "pressure_bar": 3.5,
                    "flow_m3_h": None,
                    "quality_status": "valid",
                    "data_origin": "SIMULATED",
                }
            ],
        )
        row = measurement_repository.get_by_sensor(test_db, 1)[0]
        assert row["pressure_bar"] == 3.5
        assert row["flow_m3_h"] is None

    def test_get_by_sensor(self, test_db):
        """Le filtrage par capteur doit fonctionner."""
        simulation_service.generate_measurements(test_db, seed=42, save=True)
        measurements = measurement_repository.get_by_sensor(test_db, 1)
        assert len(measurements) > 0
        for m in measurements:
            assert m["sensor_id"] == 1

    def test_get_by_zone(self, test_db):
        """Le filtrage par zone doit fonctionner."""
        simulation_service.generate_measurements(test_db, seed=42, save=True)
        measurements = measurement_repository.get_by_zone(test_db, 1)
        assert len(measurements) > 0
        for m in measurements:
            assert m["zone_name"] == "Tunis Centre"

    def test_count_starts_at_zero(self, test_db):
        """Aucune mesure ne doit exister au départ."""
        assert measurement_repository.count_all(test_db) == 0

    def test_count_after_generation(self, test_db):
        """Le compteur doit augmenter après la génération."""
        simulation_service.generate_measurements(test_db, seed=42, save=True)
        assert measurement_repository.count_all(test_db) > 0

    def test_filtered_by_governorate(self, test_db):
        """Le filtrage par gouvernorat doit fonctionner."""
        simulation_service.generate_measurements(test_db, seed=42, save=True)
        measurements = measurement_repository.get_filtered(
            test_db, governorate_id=1
        )
        assert len(measurements) > 0
        for m in measurements:
            assert m["governorate_name"] == "Tunis"

    def test_filtered_by_zone(self, test_db):
        """Le filtrage par zone via get_filtered doit fonctionner."""
        simulation_service.generate_measurements(test_db, seed=42, save=True)
        measurements = measurement_repository.get_filtered(test_db, zone_id=1)
        assert len(measurements) > 0
        for m in measurements:
            assert m["zone_name"] == "Tunis Centre"

    def test_latest_by_sensor(self, test_db):
        """Doit retourner la dernière mesure d'un capteur."""
        simulation_service.generate_measurements(test_db, seed=42, save=True)
        latest = measurement_repository.get_latest_by_sensor(test_db, 1)
        assert latest is not None
        assert latest["sensor_id"] == 1

    def test_latest_by_sensor_empty(self, test_db):
        """Doit retourner None si aucune mesure n'existe."""
        latest = measurement_repository.get_latest_by_sensor(test_db, 1)
        assert latest is None
