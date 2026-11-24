"""Tests du service de surveillance.

Vérifie la détermination des statuts de surveillance :
Normal, Données insuffisantes, Inactive.
"""

import pytest

from backend.config import STATUS_INACTIVE, STATUS_INSUFFICIENT_DATA, STATUS_NORMAL
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
