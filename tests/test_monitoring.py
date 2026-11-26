"""Tests du service de surveillance.

Vérifie la détermination des statuts de surveillance :
Normal, Données insuffisantes, Inactive.
"""

from datetime import datetime, timedelta
import pytest

from backend.config import STATUS_INACTIVE, STATUS_INSUFFICIENT_DATA, STATUS_NORMAL
from backend.repositories import alert_repository, measurement_repository, sensor_repository
from backend.services import monitoring_service, simulation_service


class TestMonitoringService:
    """Tests de détermination du statut de surveillance."""

    def test_zone_without_data_is_insufficient(self, test_db):
        """Une zone sans mesures → Données insuffisantes."""
        status = monitoring_service.get_zone_status(test_db, 1)
        assert status == STATUS_INSUFFICIENT_DATA

    def test_zone_with_data_is_normal(self, test_db):
        """Une zone active avec suffisamment de données → Normal."""
        simulation_service.generate_measurements(test_db, seed=42, save=True)
        status = monitoring_service.get_zone_status(test_db, 1)
        assert status == STATUS_NORMAL

    def test_inactive_zone(self, test_db):
        """Une zone désactivée → Inactive (même avec des données)."""
        simulation_service.generate_measurements(test_db, seed=42, save=True)
        test_db.execute(
            "UPDATE monitoring_zones SET is_active = 0 WHERE id = 1"
        )
        test_db.commit()
        status = monitoring_service.get_zone_status(test_db, 1)
        assert status == STATUS_INACTIVE

    def test_nonexistent_zone(self, test_db):
        """Une zone inexistante → Données insuffisantes."""
        status = monitoring_service.get_zone_status(test_db, 999)
        assert status == STATUS_INSUFFICIENT_DATA

    def test_get_all_zone_statuses_count(self, test_db):
        """Doit retourner un statut pour chacune des 8 zones."""
        statuses = monitoring_service.get_all_zone_statuses(test_db)
        assert len(statuses) == 8

    def test_all_statuses_are_valid(self, test_db):
        """Chaque statut doit être une valeur reconnue."""
        valid_statuses = {STATUS_NORMAL, STATUS_INSUFFICIENT_DATA, STATUS_INACTIVE}
        statuses = monitoring_service.get_all_zone_statuses(test_db)
        for zone_status in statuses:
            assert zone_status["status"] in valid_statuses

    def test_zone_statuses_have_required_fields(self, test_db):
        """Chaque statut de zone doit contenir les champs requis."""
        required_fields = {
            "zone_id",
            "zone_code",
            "zone_name",
            "governorate_name",
            "is_active",
            "sensor_count",
            "active_sensor_count",
            "measurement_count",
            "status",
        }
        statuses = monitoring_service.get_all_zone_statuses(test_db)
        for zone_status in statuses:
            missing = required_fields - set(zone_status.keys())
            assert not missing, f"Champs manquants : {missing}"

    def test_status_transitions(self, test_db):
        """Le statut doit changer quand les conditions changent."""
        # Sans données → Données insuffisantes
        assert monitoring_service.get_zone_status(test_db, 1) == STATUS_INSUFFICIENT_DATA

        # Avec données → Normal
        simulation_service.generate_measurements(test_db, seed=42, save=True)
        assert monitoring_service.get_zone_status(test_db, 1) == STATUS_NORMAL

        # Désactivation → Inactive
        test_db.execute(
            "UPDATE monitoring_zones SET is_active = 0 WHERE id = 1"
        )
        test_db.commit()
        assert monitoring_service.get_zone_status(test_db, 1) == STATUS_INACTIVE

    def test_threshold_boundary_comparisons(self, test_db):
        """Les seuils doivent être comparés avec <= (Section 3.2).

        1.5 bar est anormal, 1.51 bar est normal.
        50.0 m³/h est anormal, 50.1 m³/h est normal.
        """
        sensors = sensor_repository.get_by_zone(test_db, 1)
        p_sensor = next(s for s in sensors if s["sensor_type"] == "pressure")
        f_sensor = next(s for s in sensors if s["sensor_type"] == "flow")

        now = monitoring_service.utc_now()

        # Insérer 12 mesures antérieures pour suffire au seuil
        simulation_service.generate_measurements(test_db, seed=42, save=True)

        # Insérer 3 mesures exactement au seuil : 1.5 bar et 50.0 m³/h
        boundary_measurements = []
        for i in range(3):
            ts = monitoring_service.format_iso(now + timedelta(minutes=5 * i))
            boundary_measurements.append(
                {
                    "sensor_id": p_sensor["id"],
                    "timestamp": ts,
                    "pressure_bar": 1.5,
                    "flow_m3_h": None,
                    "quality_status": "valid",
                    "data_origin": "SIMULATED",
                }
            )
            boundary_measurements.append(
                {
                    "sensor_id": f_sensor["id"],
                    "timestamp": ts,
                    "pressure_bar": None,
                    "flow_m3_h": 50.0,
                    "quality_status": "valid",
                    "data_origin": "SIMULATED",
                }
            )
        measurement_repository.insert_many(test_db, boundary_measurements)

        # Doit déclencher l'alerte d'interruption car <= seuils
        res = monitoring_service.evaluate_zone(test_db, 1, reference_time=now + timedelta(minutes=20))
        assert res["consecutive_low_pressure_count"] >= 3
        assert res["consecutive_low_flow_count"] >= 3
        assert res["status"] == "Interruption possible"

    def test_alert_transition_from_warning_to_interruption(self, test_db):
        """Transition d'alerte : LOW_PRESSURE -> POSSIBLE_INTERRUPTION sans doublon actif."""
        simulation_service.generate_measurements(test_db, seed=42, save=True)

        # 1. Pression faible seule (3 lectures)
        simulation_service.generate_abnormal_measurements(test_db, 1, "low_pressure", 3, save=True)
        res1 = monitoring_service.evaluate_zone(test_db, 1)
        assert res1["status"] == "Pression faible"
        active_alerts1 = alert_repository.get_active_by_zone(test_db, 1)
        assert len(active_alerts1) == 1
        assert active_alerts1[0]["alert_type"] == "LOW_PRESSURE"

        # 2. Le débit devient également faible tout en maintenant la pression basse (interruption)
        simulation_service.generate_abnormal_measurements(test_db, 1, "interruption", 3, save=True)
        res2 = monitoring_service.evaluate_zone(test_db, 1)
        assert res2["status"] == "Interruption possible"

        # L'alerte LOW_PRESSURE doit être résolue et remplacée par POSSIBLE_INTERRUPTION
        active_alerts2 = alert_repository.get_active_by_zone(test_db, 1)
        assert len(active_alerts2) == 1
        assert active_alerts2[0]["alert_type"] == "POSSIBLE_INTERRUPTION"
        assert active_alerts2[0]["severity"] == "CRITICAL"

