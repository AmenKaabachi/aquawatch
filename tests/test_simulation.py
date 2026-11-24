"""Tests du service de simulation.

Vérifie la génération de mesures simulées : champs requis,
plages de valeurs, reproductibilité et persistance.
"""

import pytest

from backend.repositories import measurement_repository, sensor_repository
from backend.services import simulation_service
from backend.utils.time_utils import parse_iso


class TestSimulationService:
    """Tests de génération de mesures simulées."""

    def test_generates_measurements(self, test_db):
        """Le simulateur doit générer des mesures."""
        measurements = simulation_service.generate_measurements(
            test_db, seed=42, save=False
        )
        assert len(measurements) > 0

    def test_measurement_required_fields(self, test_db):
        """Chaque mesure doit contenir tous les champs requis."""
        measurements = simulation_service.generate_measurements(
            test_db, seed=42, save=False
        )
        required_fields = {
            "sensor_id",
            "timestamp",
            "pressure_bar",
            "flow_m3_h",
            "quality_status",
            "data_origin",
        }
        for m in measurements:
            missing = required_fields - set(m.keys())
            assert not missing, f"Champs manquants : {missing}"

    def test_pressure_in_range(self, test_db):
        """La pression doit être dans [1.5, 6.0] bar."""
        measurements = simulation_service.generate_measurements(
            test_db, seed=42, save=False
        )
        for m in measurements:
            if m["pressure_bar"] is not None:
                assert 1.5 <= m["pressure_bar"] <= 6.0, (
                    f"Pression hors limites : {m['pressure_bar']}"
                )

    def test_flow_in_range(self, test_db):
        """Le débit doit être dans [50.0, 500.0] m³/h."""
        measurements = simulation_service.generate_measurements(
            test_db, seed=42, save=False
        )
        for m in measurements:
            if m["flow_m3_h"] is not None:
                assert 50.0 <= m["flow_m3_h"] <= 500.0, (
                    f"Débit hors limites : {m['flow_m3_h']}"
                )

    def test_measurements_match_sensor_type(self, test_db):
        """Only metrics supported by each sensor type are generated."""
        measurements = simulation_service.generate_measurements(
            test_db, seed=42, save=False
        )
        sensor_types = {
            sensor["id"]: sensor["sensor_type"]
            for sensor in sensor_repository.get_all(test_db)
        }

        for measurement in measurements:
            sensor_type = sensor_types[measurement["sensor_id"]]
            if sensor_type == "pressure":
                assert measurement["pressure_bar"] is not None
                assert measurement["flow_m3_h"] is None
            elif sensor_type == "flow":
                assert measurement["pressure_bar"] is None
                assert measurement["flow_m3_h"] is not None
            else:
                assert measurement["pressure_bar"] is not None
                assert measurement["flow_m3_h"] is not None

    def test_valid_iso_timestamps(self, test_db):
        """Les horodatages doivent être au format ISO 8601 valide."""
        measurements = simulation_service.generate_measurements(
            test_db, seed=42, save=False
        )
        for m in measurements:
            dt = parse_iso(m["timestamp"])
            assert dt is not None

    def test_all_marked_simulated(self, test_db):
        """Toutes les mesures doivent avoir data_origin = 'SIMULATED'."""
        measurements = simulation_service.generate_measurements(
            test_db, seed=42, save=False
        )
        for m in measurements:
            assert m["data_origin"] == "SIMULATED"

    def test_reproducible_with_same_seed(self, test_db):
        """La même graine doit produire des résultats identiques."""
        m1 = simulation_service.generate_measurements(
            test_db, seed=123, save=False
        )
        m2 = simulation_service.generate_measurements(
            test_db, seed=123, save=False
        )
        assert len(m1) == len(m2)
        for a, b in zip(m1, m2):
            assert a["pressure_bar"] == b["pressure_bar"]
            assert a["flow_m3_h"] == b["flow_m3_h"]
            assert a["timestamp"] == b["timestamp"]

    def test_different_seeds_differ(self, test_db):
        """Des graines différentes doivent donner des résultats différents."""
        m1 = simulation_service.generate_measurements(
            test_db, seed=1, save=False
        )
        m2 = simulation_service.generate_measurements(
            test_db, seed=2, save=False
        )
        differences = sum(
            1 for a, b in zip(m1, m2) if a["pressure_bar"] != b["pressure_bar"]
        )
        assert differences > 0

    def test_saves_to_database(self, test_db):
        """save=True doit persister les mesures en base."""
        initial_count = measurement_repository.count_all(test_db)
        measurements = simulation_service.generate_measurements(
            test_db, seed=42, save=True
        )
        final_count = measurement_repository.count_all(test_db)
        assert final_count == initial_count + len(measurements)

    def test_save_false_does_not_persist(self, test_db):
        """save=False ne doit pas modifier la base."""
        initial_count = measurement_repository.count_all(test_db)
        simulation_service.generate_measurements(test_db, seed=42, save=False)
        final_count = measurement_repository.count_all(test_db)
        assert final_count == initial_count

    def test_correct_count_per_sensor(self, test_db):
        """Le nombre de mesures par capteur doit correspondre au paramètre."""
        count_per = 10
        measurements = simulation_service.generate_measurements(
            test_db, seed=42, count_per_sensor=count_per, save=False
        )
        active_count = sensor_repository.count_active(test_db)
        assert len(measurements) == active_count * count_per
