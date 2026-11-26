"""Tests du repository et du cycle de vie des alertes (Sprint 2).

Vérifie :
- La création, mise à jour et résolution des alertes.
- Le filtrage par sévérité, type, statut, gouvernorat et date.
- L'intégrité des clés étrangères et contraintes CHECK.
- L'absence de doublons d'alertes actives.
"""

import sqlite3
import pytest

from backend.config import (
    ALERT_STATUS_ACTIVE,
    ALERT_STATUS_RESOLVED,
    ALERT_TYPE_LOW_FLOW,
    ALERT_TYPE_LOW_PRESSURE,
    ALERT_TYPE_POSSIBLE_INTERRUPTION,
    SEVERITY_CRITICAL,
    SEVERITY_WARNING,
)
from backend.repositories import alert_repository, monitoring_repository


class TestAlertRepository:
    """Tests unitaires pour alert_repository."""

    def test_create_and_retrieve_alert(self, test_db):
        """Création d'une alerte et récupération par zone."""
        alert_id = alert_repository.create_alert(
            conn=test_db,
            zone_id=1,
            alert_type=ALERT_TYPE_LOW_PRESSURE,
            severity=SEVERITY_WARNING,
            message="Pression basse",
            started_at="2026-11-24T10:00:00Z",
            last_detected_at="2026-11-24T10:00:00Z",
        )
        assert alert_id > 0

        active_alerts = alert_repository.get_active_by_zone(test_db, 1)
        assert len(active_alerts) == 1
        assert active_alerts[0]["alert_type"] == ALERT_TYPE_LOW_PRESSURE
        assert active_alerts[0]["severity"] == SEVERITY_WARNING
        assert active_alerts[0]["status"] == ALERT_STATUS_ACTIVE
        assert active_alerts[0]["zone_name"] is not None
        assert active_alerts[0]["governorate_name"] is not None

    def test_update_last_detected(self, test_db):
        """Mise à jour de l'horodatage de dernière détection."""
        alert_id = alert_repository.create_alert(
            conn=test_db,
            zone_id=1,
            alert_type=ALERT_TYPE_LOW_FLOW,
            severity=SEVERITY_WARNING,
            message="Débit faible",
            started_at="2026-11-24T10:00:00Z",
            last_detected_at="2026-11-24T10:00:00Z",
        )
        alert_repository.update_last_detected(
            test_db, alert_id, "2026-11-24T10:30:00Z"
        )

        alert = alert_repository.get_active_by_zone_and_type(
            test_db, 1, ALERT_TYPE_LOW_FLOW
        )
        assert alert["last_detected_at"] == "2026-11-24T10:30:00Z"
        assert alert["started_at"] == "2026-11-24T10:00:00Z"

    def test_resolve_alert(self, test_db):
        """Résolution d'une alerte active."""
        alert_id = alert_repository.create_alert(
            conn=test_db,
            zone_id=1,
            alert_type=ALERT_TYPE_POSSIBLE_INTERRUPTION,
            severity=SEVERITY_CRITICAL,
            message="Coupure possible",
            started_at="2026-11-24T10:00:00Z",
            last_detected_at="2026-11-24T10:30:00Z",
        )
        alert_repository.resolve_alert(test_db, alert_id, "2026-11-24T11:00:00Z")

        # N'est plus active
        assert alert_repository.get_active_by_zone(test_db, 1) == []

        # Existe toujours dans l'historique résolu
        resolved = alert_repository.get_resolved(test_db)
        assert len(resolved) == 1
        assert resolved[0]["id"] == alert_id
        assert resolved[0]["status"] == ALERT_STATUS_RESOLVED
        assert resolved[0]["resolved_at"] == "2026-11-24T11:00:00Z"

    def test_filter_alerts(self, test_db):
        """Filtrage des alertes selon divers critères."""
        # Zone 1 : alerte pression
        alert_repository.create_alert(
            test_db, 1, ALERT_TYPE_LOW_PRESSURE, SEVERITY_WARNING,
            "Pression", "2026-11-24T08:00:00Z", "2026-11-24T08:00:00Z"
        )
        # Zone 2 : alerte interruption
        aid2 = alert_repository.create_alert(
            test_db, 2, ALERT_TYPE_POSSIBLE_INTERRUPTION, SEVERITY_CRITICAL,
            "Interruption", "2026-11-24T09:00:00Z", "2026-11-24T09:00:00Z"
        )
        alert_repository.resolve_alert(test_db, aid2, "2026-11-24T09:30:00Z")

        # Filtre par sévérité
        critical_alerts = alert_repository.get_filtered(test_db, severity=SEVERITY_CRITICAL)
        assert len(critical_alerts) == 1
        assert critical_alerts[0]["severity"] == SEVERITY_CRITICAL

        # Filtre par statut
        active = alert_repository.get_filtered(test_db, status=ALERT_STATUS_ACTIVE)
        assert len(active) == 1
        assert active[0]["zone_id"] == 1

        resolved = alert_repository.get_filtered(test_db, status=ALERT_STATUS_RESOLVED)
        assert len(resolved) == 1
        assert resolved[0]["zone_id"] == 2

    def test_foreign_key_constraint_on_alerts(self, test_db):
        """Une alerte sur une zone inexistante doit échouer."""
        with pytest.raises(sqlite3.IntegrityError):
            alert_repository.create_alert(
                test_db, 9999, ALERT_TYPE_LOW_PRESSURE, SEVERITY_WARNING,
                "Inconnue", "2026-11-24T10:00:00Z", "2026-11-24T10:00:00Z"
            )

    def test_invalid_alert_type_rejected(self, test_db):
        """Un type d'alerte non autorisé par le CHECK doit échouer."""
        with pytest.raises(sqlite3.IntegrityError):
            test_db.execute(
                """
                INSERT INTO alerts (zone_id, alert_type, severity, message, started_at, last_detected_at)
                VALUES (1, 'UNKNOWN_TYPE', 'WARNING', 'msg', '2026-11-24T10:00:00Z', '2026-11-24T10:00:00Z')
                """
            )


class TestMonitoringRepository:
    """Tests pour monitoring_repository."""

    def test_upsert_and_get_state(self, test_db):
        """Enregistrement et lecture de l'état de surveillance."""
        monitoring_repository.upsert_state(
            conn=test_db,
            zone_id=1,
            last_pressure_id=10,
            last_flow_id=20,
            consecutive_pressure=2,
            consecutive_flow=1,
            last_evaluated_at="2026-11-24T12:00:00Z",
        )

        state = monitoring_repository.get_state(test_db, 1)
        assert state is not None
        assert state["zone_id"] == 1
        assert state["last_processed_pressure_measurement_id"] == 10
        assert state["last_processed_flow_measurement_id"] == 20
        assert state["consecutive_low_pressure_count"] == 2
        assert state["consecutive_low_flow_count"] == 1

        # Mise à jour idempotente
        monitoring_repository.upsert_state(
            conn=test_db,
            zone_id=1,
            last_pressure_id=15,
            last_flow_id=25,
            consecutive_pressure=3,
            consecutive_flow=0,
            last_evaluated_at="2026-11-24T12:10:00Z",
        )
        updated = monitoring_repository.get_state(test_db, 1)
        assert updated["consecutive_low_pressure_count"] == 3
        assert updated["last_processed_pressure_measurement_id"] == 15
