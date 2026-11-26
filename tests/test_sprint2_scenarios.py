"""Validation des 12 scénarios requis pour le Sprint 2 (Section 8).

Couvre exhaustivement :
- Scénario 1 : Approvisionnement normal
- Scénario 2 : Pression faible (3 lectures consécutives, alerte WARNING)
- Scénario 3 : Débit faible (3 lectures consécutives, alerte WARNING)
- Scénario 4 : Interruption possible (pression + débit faibles, alerte CRITICAL)
- Scénario 5 : Lecture anormale temporaire (< 3 lectures, aucune fausse alerte)
- Scénario 6 : Rétablissement de l'approvisionnement (résolution d'alerte et conservation historique)
- Scénario 7 : Données manquantes (pas de fausse alerte, statut données insuffisantes)
- Scénario 8 : Données invalides (ignorées lors de la détection)
- Scénario 9 : Données anciennes / obsolètes (statut données anciennes, pas de fausse alerte)
- Scénario 10 : Évaluations répétées idempotentes (compteurs et alertes stables)
- Scénario 11 : Repli capteur combiné (capteur dédié absent ou invalide, pas de double-comptage)
- Scénario 12 : Évaluation indépendante multi-zones
"""

from datetime import datetime, timedelta, timezone
import pytest

from backend.config import (
    ALERT_STATUS_ACTIVE,
    ALERT_STATUS_RESOLVED,
    ALERT_TYPE_LOW_FLOW,
    ALERT_TYPE_LOW_PRESSURE,
    ALERT_TYPE_POSSIBLE_INTERRUPTION,
    CONSECUTIVE_ABNORMAL_READINGS,
    FRESHNESS_RECENT,
    FRESHNESS_STALE,
    FRESHNESS_UNAVAILABLE,
    LOW_FLOW_THRESHOLD_M3_H,
    LOW_PRESSURE_THRESHOLD_BAR,
    SEVERITY_CRITICAL,
    SEVERITY_WARNING,
    STATUS_INSUFFICIENT_DATA,
    STATUS_LOW_FLOW,
    STATUS_LOW_PRESSURE,
    STATUS_NORMAL,
    STATUS_POSSIBLE_INTERRUPTION,
    STATUS_STALE_DATA,
)
from backend.repositories import alert_repository, measurement_repository, sensor_repository
from backend.services import monitoring_service, simulation_service
from backend.utils.time_utils import format_iso, parse_iso

FIXED_NOW = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)


def _seed_normal_background_data(conn, zone_id: int, count: int = 12, ref_time: datetime = FIXED_NOW):
    """Insère un historique normal pour dépasser le seuil minimal de 10 mesures."""
    sensors = sensor_repository.get_by_zone(conn, zone_id)
    measurements = []
    base_time = ref_time - timedelta(hours=2)

    for i in range(count):
        ts = format_iso(base_time + timedelta(minutes=5 * i))
        for s in sensors:
            stype = s["sensor_type"]
            p = 3.5 if stype in ("pressure", "combined") else None
            f = 200.0 if stype in ("flow", "combined") else None
            measurements.append(
                {
                    "sensor_id": s["id"],
                    "timestamp": ts,
                    "pressure_bar": p,
                    "flow_m3_h": f,
                    "quality_status": "valid",
                    "data_origin": "SIMULATED",
                }
            )
    measurement_repository.insert_many(conn, measurements)


class TestSprint2Scenarios:
    """Suite de vérification des scénarios Sprint 2."""

    def test_scenario_1_normal_supply(self, test_db):
        """Scénario 1 : Approvisionnement normal.

        - Pression normale (> 1.5 bar).
        - Débit normal (> 50 m³/h).
        - Aucune alerte active.
        - Statut Normal.
        """
        _seed_normal_background_data(test_db, zone_id=1, count=12, ref_time=FIXED_NOW)

        res = monitoring_service.evaluate_zone(test_db, zone_id=1, reference_time=FIXED_NOW)
        assert res["status"] == STATUS_NORMAL
        assert res["pressure_status"] == "Normal"
        assert res["flow_status"] == "Normal"
        assert res["consecutive_low_pressure_count"] == 0
        assert res["consecutive_low_flow_count"] == 0
        assert res["active_alert"] is None
        assert alert_repository.count_active(test_db) == 0

    def test_scenario_2_low_pressure_warning(self, test_db):
        """Scénario 2 : Pression faible.

        - 3 mesures consécutives de basse pression (<= 1.5 bar).
        - Débit normal (> 50 m³/h).
        - Alerte WARNING de type LOW_PRESSURE créée.
        - Statut Pression faible.
        """
        _seed_normal_background_data(test_db, zone_id=1, count=10, ref_time=FIXED_NOW - timedelta(minutes=40))

        simulation_service.generate_abnormal_measurements(
            conn=test_db,
            zone_id=1,
            condition="low_pressure",
            count=3,
            base_time=FIXED_NOW - timedelta(minutes=20),
            save=True,
        )

        res = monitoring_service.evaluate_zone(test_db, zone_id=1, reference_time=FIXED_NOW)
        assert res["status"] == STATUS_LOW_PRESSURE
        assert res["consecutive_low_pressure_count"] >= 3
        assert res["consecutive_low_flow_count"] == 0

        active_alerts = alert_repository.get_active_by_zone(test_db, 1)
        assert len(active_alerts) == 1
        assert active_alerts[0]["alert_type"] == ALERT_TYPE_LOW_PRESSURE
        assert active_alerts[0]["severity"] == SEVERITY_WARNING

    def test_scenario_3_low_flow_warning(self, test_db):
        """Scénario 3 : Débit faible.

        - 3 mesures consécutives de faible débit (<= 50 m³/h).
        - Pression normale (> 1.5 bar).
        - Alerte WARNING de type LOW_FLOW créée.
        - Statut Débit faible.
        """
        _seed_normal_background_data(test_db, zone_id=1, count=10, ref_time=FIXED_NOW - timedelta(minutes=40))

        simulation_service.generate_abnormal_measurements(
            conn=test_db,
            zone_id=1,
            condition="low_flow",
            count=3,
            base_time=FIXED_NOW - timedelta(minutes=20),
            save=True,
        )

        res = monitoring_service.evaluate_zone(test_db, zone_id=1, reference_time=FIXED_NOW)
        assert res["status"] == STATUS_LOW_FLOW
        assert res["consecutive_low_flow_count"] >= 3
        assert res["consecutive_low_pressure_count"] == 0

        active_alerts = alert_repository.get_active_by_zone(test_db, 1)
        assert len(active_alerts) == 1
        assert active_alerts[0]["alert_type"] == ALERT_TYPE_LOW_FLOW
        assert active_alerts[0]["severity"] == SEVERITY_WARNING

    def test_scenario_4_possible_interruption_critical(self, test_db):
        """Scénario 4 : Interruption possible.

        - 3 mesures consécutives de basse pression.
        - 3 mesures consécutives de faible débit.
        - Alerte CRITICAL de type POSSIBLE_INTERRUPTION créée.
        - Statut Interruption possible.
        """
        _seed_normal_background_data(test_db, zone_id=1, count=10, ref_time=FIXED_NOW - timedelta(minutes=40))

        simulation_service.generate_abnormal_measurements(
            conn=test_db,
            zone_id=1,
            condition="interruption",
            count=3,
            base_time=FIXED_NOW - timedelta(minutes=20),
            save=True,
        )

        res = monitoring_service.evaluate_zone(test_db, zone_id=1, reference_time=FIXED_NOW)
        assert res["status"] == STATUS_POSSIBLE_INTERRUPTION
        assert res["consecutive_low_pressure_count"] >= 3
        assert res["consecutive_low_flow_count"] >= 3

        active_alerts = alert_repository.get_active_by_zone(test_db, 1)
        assert len(active_alerts) == 1
        assert active_alerts[0]["alert_type"] == ALERT_TYPE_POSSIBLE_INTERRUPTION
        assert active_alerts[0]["severity"] == SEVERITY_CRITICAL

    def test_scenario_5_temporary_abnormal_reading_no_alert(self, test_db):
        """Scénario 5 : Lecture anormale temporaire.

        - 1 mesure anormale (< 3).
        - Suivie d'une mesure normale.
        - Aucune alerte déclenchée.
        """
        _seed_normal_background_data(test_db, zone_id=1, count=10, ref_time=FIXED_NOW - timedelta(minutes=40))

        # 1 seule lecture anormale
        simulation_service.generate_abnormal_measurements(
            conn=test_db,
            zone_id=1,
            condition="interruption",
            count=1,
            base_time=FIXED_NOW - timedelta(minutes=20),
            save=True,
        )

        res = monitoring_service.evaluate_zone(test_db, zone_id=1, reference_time=FIXED_NOW)
        assert res["consecutive_low_pressure_count"] == 1
        assert res["consecutive_low_flow_count"] == 1
        assert alert_repository.count_active(test_db) == 0

        # Mesure normale suivante : réinitialise le compteur
        simulation_service.generate_abnormal_measurements(
            conn=test_db,
            zone_id=1,
            condition="normal",
            count=1,
            base_time=FIXED_NOW - timedelta(minutes=10),
            save=True,
        )

        res2 = monitoring_service.evaluate_zone(test_db, zone_id=1, reference_time=FIXED_NOW)
        assert res2["consecutive_low_pressure_count"] == 0
        assert res2["consecutive_low_flow_count"] == 0
        assert res2["status"] == STATUS_NORMAL
        assert alert_repository.count_active(test_db) == 0

    def test_scenario_6_recovery_resolves_alert_and_preserves_history(self, test_db):
        """Scénario 6 : Rétablissement.

        - Une alerte active existe.
        - Arrivée de mesures normales satisfaisant la règle de récupération.
        - L'alerte passe à RESOLVED.
        - L'alerte résolue reste consultable dans l'historique.
        """
        _seed_normal_background_data(test_db, zone_id=1, count=10, ref_time=FIXED_NOW - timedelta(minutes=50))

        # Générer interruption -> Alerte CRITICAL
        simulation_service.generate_abnormal_measurements(
            test_db, zone_id=1, condition="interruption", count=3,
            base_time=FIXED_NOW - timedelta(minutes=30), save=True
        )
        res_alert = monitoring_service.evaluate_zone(test_db, zone_id=1, reference_time=FIXED_NOW - timedelta(minutes=15))
        assert res_alert["status"] == STATUS_POSSIBLE_INTERRUPTION
        assert alert_repository.count_active(test_db) == 1

        # Génération d'une mesure normale (rétablissement)
        simulation_service.generate_abnormal_measurements(
            test_db, zone_id=1, condition="normal", count=1,
            base_time=FIXED_NOW - timedelta(minutes=5), save=True
        )

        res_recovered = monitoring_service.evaluate_zone(test_db, zone_id=1, reference_time=FIXED_NOW)
        assert res_recovered["status"] == STATUS_NORMAL
        assert res_recovered["consecutive_low_pressure_count"] == 0
        assert res_recovered["consecutive_low_flow_count"] == 0

        # L'alerte active n'existe plus
        assert alert_repository.get_active_by_zone(test_db, 1) == []

        # Mais l'historique contient l'alerte résolue
        resolved_history = alert_repository.get_resolved(test_db)
        assert len(resolved_history) == 1
        assert resolved_history[0]["alert_type"] == ALERT_TYPE_POSSIBLE_INTERRUPTION
        assert resolved_history[0]["status"] == ALERT_STATUS_RESOLVED
        assert resolved_history[0]["resolved_at"] is not None

    def test_scenario_7_missing_data_no_false_alert(self, test_db):
        """Scénario 7 : Données manquantes.

        - Métrique indisponible.
        - Ne doit jamais être interprétée comme zéro.
        - Ne doit pas générer d'alerte d'interruption.
        - Statut : Données insuffisantes.
        """
        # Aucune mesure insérée pour la zone 1
        res = monitoring_service.evaluate_zone(test_db, zone_id=1, reference_time=FIXED_NOW)
        assert res["status"] == STATUS_INSUFFICIENT_DATA
        assert res["latest_pressure"] is None
        assert res["latest_flow"] is None
        assert alert_repository.count_active(test_db) == 0

    def test_scenario_8_invalid_data_ignored_for_detection(self, test_db):
        """Scénario 8 : Données invalides.

        - Une mesure marquée 'invalid' ou 'suspect' ne doit pas incrémenter le compteur.
        - Ne doit pas générer de fausse alerte.
        """
        _seed_normal_background_data(test_db, zone_id=1, count=10, ref_time=FIXED_NOW - timedelta(minutes=40))

        sensors = sensor_repository.get_by_zone(test_db, 1)
        p_sensor = next(s for s in sensors if s["sensor_type"] == "pressure")

        # Insertion de 3 mesures à 0.5 bar mais avec quality_status = 'invalid'
        invalid_rows = []
        for i in range(3):
            invalid_rows.append(
                {
                    "sensor_id": p_sensor["id"],
                    "timestamp": format_iso(FIXED_NOW - timedelta(minutes=15 - i)),
                    "pressure_bar": 0.5,
                    "flow_m3_h": None,
                    "quality_status": "invalid",
                    "data_origin": "SIMULATED",
                }
            )
        measurement_repository.insert_many(test_db, invalid_rows)

        res = monitoring_service.evaluate_zone(test_db, zone_id=1, reference_time=FIXED_NOW)
        assert res["consecutive_low_pressure_count"] == 0
        assert alert_repository.count_active(test_db) == 0
        assert res["status"] != STATUS_LOW_PRESSURE

    def test_scenario_9_stale_data_marked_and_no_false_alert(self, test_db):
        """Scénario 9 : Données anciennes / obsolètes.

        - Mesures datant de plus de 24h.
        - Doit afficher Données anciennes.
        - Ne doit pas générer d'alerte d'interruption.
        """
        stale_time = FIXED_NOW - timedelta(hours=30)
        _seed_normal_background_data(test_db, zone_id=1, count=12, ref_time=stale_time)

        res = monitoring_service.evaluate_zone(test_db, zone_id=1, reference_time=FIXED_NOW)
        assert res["status"] == STATUS_STALE_DATA
        assert res["data_freshness"] == FRESHNESS_STALE
        assert alert_repository.count_active(test_db) == 0

    def test_scenario_10_repeated_evaluation_idempotent(self, test_db):
        """Scénario 10 : Évaluations répétées.

        - Évaluer la même zone 5 fois de suite sans nouvelles mesures.
        - Les compteurs ne doivent pas s'incrémenter plusieurs fois.
        - Aucun doublon d'alerte ne doit être créé.
        """
        _seed_normal_background_data(test_db, zone_id=1, count=10, ref_time=FIXED_NOW - timedelta(minutes=40))

        simulation_service.generate_abnormal_measurements(
            test_db, zone_id=1, condition="interruption", count=3,
            base_time=FIXED_NOW - timedelta(minutes=20), save=True
        )

        res1 = monitoring_service.evaluate_zone(test_db, zone_id=1, reference_time=FIXED_NOW)
        assert res1["consecutive_low_pressure_count"] == 3
        assert alert_repository.count_active(test_db) == 1

        # Répétitions multiples
        for _ in range(4):
            res_loop = monitoring_service.evaluate_zone(test_db, zone_id=1, reference_time=FIXED_NOW)
            assert res_loop["consecutive_low_pressure_count"] == 3
            assert res_loop["consecutive_low_flow_count"] == 3

        # Toujours une seule alerte active (pas de doublon)
        assert alert_repository.count_active(test_db) == 1
        all_alerts = alert_repository.get_all(test_db)
        assert len(all_alerts) == 1

    def test_scenario_11_sensor_fallback_without_double_counting(self, test_db):
        """Scénario 11 : Repli capteur combiné.

        - Le capteur dédié est indisponible ou ne contient aucune mesure.
        - Le capteur combiné fournit la mesure de pression ou de débit en repli.
        - Le repli fonctionne sans double-comptage.
        """
        sensors = sensor_repository.get_by_zone(test_db, 1)
        p_sensor = next(s for s in sensors if s["sensor_type"] == "pressure")
        comb_sensor = next(s for s in sensors if s["sensor_type"] == "combined")
        flow_sensor = next(s for s in sensors if s["sensor_type"] == "flow")

        # Insérer des mesures normales pour débit sur capteur dédié
        normal_flows = []
        for i in range(12):
            normal_flows.append(
                {
                    "sensor_id": flow_sensor["id"],
                    "timestamp": format_iso(FIXED_NOW - timedelta(minutes=15 - i)),
                    "pressure_bar": None,
                    "flow_m3_h": 200.0,
                    "quality_status": "valid",
                    "data_origin": "SIMULATED",
                }
            )
        measurement_repository.insert_many(test_db, normal_flows)

        # Capteur dédié pression n'a AUCUNE mesure.
        # Le capteur combiné a des mesures valides à basse pression (1.2 bar)
        comb_measurements = []
        for i in range(3):
            comb_measurements.append(
                {
                    "sensor_id": comb_sensor["id"],
                    "timestamp": format_iso(FIXED_NOW - timedelta(minutes=10 - (2 * i))),
                    "pressure_bar": 1.2,
                    "flow_m3_h": 210.0,
                    "quality_status": "valid",
                    "data_origin": "SIMULATED",
                }
            )
        measurement_repository.insert_many(test_db, comb_measurements)

        # Vérification du repli
        rep_p = monitoring_service.get_representative_reading(test_db, 1, "pressure", reference_time=FIXED_NOW)
        assert rep_p.is_fallback is True
        assert rep_p.value == 1.2
        assert rep_p.sensor_type == "combined"

        # Évaluation de la zone : doit utiliser le capteur combiné pour la pression
        res = monitoring_service.evaluate_zone(test_db, zone_id=1, reference_time=FIXED_NOW)
        assert res["consecutive_low_pressure_count"] == 3
        assert res["pressure_is_fallback"] is True
        assert res["status"] == STATUS_LOW_PRESSURE

    def test_scenario_12_multiple_zones_evaluated_independently(self, test_db):
        """Scénario 12 : Évaluation indépendante de plusieurs zones.

        - Zone 1 : normale.
        - Zone 2 : pression faible.
        - Zone 3 : interruption possible.
        - Les zones sont évaluées isolément sans collision d'état.
        """
        # Zone 1 : normale
        _seed_normal_background_data(test_db, zone_id=1, count=12, ref_time=FIXED_NOW)

        # Zone 2 : pression faible
        _seed_normal_background_data(test_db, zone_id=2, count=10, ref_time=FIXED_NOW - timedelta(minutes=30))
        simulation_service.generate_abnormal_measurements(
            test_db, zone_id=2, condition="low_pressure", count=3,
            base_time=FIXED_NOW - timedelta(minutes=15), save=True
        )

        # Zone 3 : interruption possible
        _seed_normal_background_data(test_db, zone_id=3, count=10, ref_time=FIXED_NOW - timedelta(minutes=30))
        simulation_service.generate_abnormal_measurements(
            test_db, zone_id=3, condition="interruption", count=3,
            base_time=FIXED_NOW - timedelta(minutes=15), save=True
        )

        all_res = monitoring_service.evaluate_all_zones(test_db, reference_time=FIXED_NOW)
        res_by_id = {z["zone_id"]: z for z in all_res}

        assert res_by_id[1]["status"] == STATUS_NORMAL
        assert res_by_id[2]["status"] == STATUS_LOW_PRESSURE
        assert res_by_id[3]["status"] == STATUS_POSSIBLE_INTERRUPTION

        # Vérification du résumé global
        summary = monitoring_service.get_monitoring_summary(test_db, all_res)
        assert summary["total_zones"] == 8
        assert summary["normal_zones"] == 1
        assert summary["warning_zones"] == 1
        assert summary["interruption_zones"] == 1
        assert summary["total_active_alerts"] == 2
