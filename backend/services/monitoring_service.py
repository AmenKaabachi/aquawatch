"""Service de surveillance pour AquaWatch Grand Tunis (Sprint 2).

Fournit :
1. La détection au niveau zone (pression, débit, interruption possible).
2. La dérivation représentative avec politique de repli (capteur dédié prioritaire, repli combiné).
3. La validation des anomalies par lectures consécutives configurables.
4. Le traitement de la qualité des données (données manquantes, invalides, obsolètes/anciennes).
5. Le cycle de vie complet et persistant des alertes (création, maintien, résolution).
6. L'idempotence stricte des évaluations répétées.
"""

import sqlite3 
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from backend.config import (
    ALERT_STATUS_ACTIVE,
    ALERT_TYPE_LOW_FLOW,
    ALERT_TYPE_LOW_PRESSURE,
    ALERT_TYPE_POSSIBLE_INTERRUPTION,
    CONSECUTIVE_ABNORMAL_READINGS,
    FRESHNESS_RECENT,
    FRESHNESS_STALE,
    FRESHNESS_UNAVAILABLE,
    LOW_FLOW_THRESHOLD_M3_H,
    LOW_PRESSURE_THRESHOLD_BAR,
    MAX_MEASUREMENT_AGE_HOURS,
    SEVERITY_CRITICAL,
    SEVERITY_WARNING,
    STATUS_INACTIVE,
    STATUS_INSUFFICIENT_DATA,
    STATUS_LOW_FLOW,
    STATUS_LOW_PRESSURE,
    STATUS_NORMAL,
    STATUS_POSSIBLE_INTERRUPTION,
    STATUS_STALE_DATA,
)
from backend.models.alert import RepresentativeReading
from backend.repositories import (
    alert_repository,
    measurement_repository,
    monitoring_repository,
    sensor_repository,
    zone_repository,
)
from backend.utils.time_utils import format_iso, parse_iso, utc_now

# Seuil minimal de mesures pour considérer les données suffisantes (Sprint 1)
_MIN_MEASUREMENTS = 10


def is_measurement_stale(
    timestamp_str: str,
    reference_time: Optional[datetime] = None,
    max_age_hours: int = MAX_MEASUREMENT_AGE_HOURS,
) -> bool:
    """Vérifie si une mesure est obsolète par rapport à l'heure de référence."""
    ref = reference_time or utc_now()
    measurement_dt = parse_iso(timestamp_str)
    age_seconds = (ref - measurement_dt).total_seconds()
    return age_seconds > (max_age_hours * 3600)


def get_representative_reading(
    conn: sqlite3.Connection,
    zone_id: int,
    metric_type: str,
    reference_time: Optional[datetime] = None,
) -> RepresentativeReading:
    """Dérive une valeur représentative pour une métrique de zone selon la politique Sprint 2.

    Politique de sélection (Section 3.1) :
    - Pression :
      1. Préférer la dernière mesure valide du capteur dédié de pression.
      2. Si indisponible, invalide ou obsolète, utiliser la dernière mesure
         valide de pression du capteur combiné en repli.
    - Débit :
      1. Préférer la dernière mesure valide du capteur dédié de débit.
      2. Si indisponible, invalide ou obsolète, utiliser la dernière mesure
         valide de débit du capteur combiné en repli.

    Ne moyenne jamais les capteurs et ne double-compte jamais le capteur combiné.
    """
    ref_time = reference_time or utc_now()
    sensors = sensor_repository.get_by_zone(conn, zone_id)

    dedicated_sensor = next(
        (s for s in sensors if s["sensor_type"] == metric_type and s["is_active"]),
        None,
    )
    combined_sensor = next(
        (s for s in sensors if s["sensor_type"] == "combined" and s["is_active"]),
        None,
    )

    # Récupération des dernières mesures valides
    ded_valid = (
        measurement_repository.get_latest_valid_by_sensor(conn, dedicated_sensor["id"])
        if dedicated_sensor
        else None
    )
    comb_valid = (
        measurement_repository.get_latest_valid_by_sensor(conn, combined_sensor["id"])
        if combined_sensor
        else None
    )

    ded_is_stale = (
        is_measurement_stale(ded_valid["timestamp"], ref_time)
        if ded_valid
        else True
    )
    comb_is_stale = (
        is_measurement_stale(comb_valid["timestamp"], ref_time)
        if comb_valid
        else True
    )

    # Règle de sélection explicite :
    # 1. Capteur dédié valide et non obsolète
    if ded_valid and not ded_is_stale:
        val = (
            ded_valid["pressure_bar"]
            if metric_type == "pressure"
            else ded_valid["flow_m3_h"]
        )
        return RepresentativeReading(
            metric_type=metric_type,
            value=val,
            timestamp=ded_valid["timestamp"],
            measurement_id=ded_valid["id"],
            sensor_id=dedicated_sensor["id"],
            sensor_name=dedicated_sensor["name"],
            sensor_type=dedicated_sensor["sensor_type"],
            is_fallback=False,
            is_stale=False,
            is_valid=True,
            freshness=FRESHNESS_RECENT,
        )

    # 2. Repli vers capteur combiné valide et non obsolète
    if comb_valid and not comb_is_stale:
        val = (
            comb_valid["pressure_bar"]
            if metric_type == "pressure"
            else comb_valid["flow_m3_h"]
        )
        return RepresentativeReading(
            metric_type=metric_type,
            value=val,
            timestamp=comb_valid["timestamp"],
            measurement_id=comb_valid["id"],
            sensor_id=combined_sensor["id"],
            sensor_name=combined_sensor["name"],
            sensor_type=combined_sensor["sensor_type"],
            is_fallback=True,
            is_stale=False,
            is_valid=True,
            freshness=FRESHNESS_RECENT,
        )

    # 3. Données obsolètes (stale) : préférer dédié s'il existe, sinon combiné
    stale_chosen = ded_valid or comb_valid
    if stale_chosen:
        is_comb = (stale_chosen == comb_valid)
        s_obj = combined_sensor if is_comb else dedicated_sensor
        val = (
            stale_chosen["pressure_bar"]
            if metric_type == "pressure"
            else stale_chosen["flow_m3_h"]
        )
        return RepresentativeReading(
            metric_type=metric_type,
            value=val,
            timestamp=stale_chosen["timestamp"],
            measurement_id=stale_chosen["id"],
            sensor_id=s_obj["id"] if s_obj else None,
            sensor_name=s_obj["name"] if s_obj else None,
            sensor_type=s_obj["sensor_type"] if s_obj else None,
            is_fallback=is_comb,
            is_stale=True,
            is_valid=True,
            freshness=FRESHNESS_STALE,
        )

    # 4. Données indisponibles ou invalides
    # Vérifier si une mesure invalide récente existe pour traçabilité
    ded_raw = (
        measurement_repository.get_latest_by_sensor(conn, dedicated_sensor["id"])
        if dedicated_sensor
        else None
    )
    comb_raw = (
        measurement_repository.get_latest_by_sensor(conn, combined_sensor["id"])
        if combined_sensor
        else None
    )
    raw_chosen = ded_raw or comb_raw

    if raw_chosen:
        is_comb = (raw_chosen == comb_raw)
        s_obj = combined_sensor if is_comb else dedicated_sensor
        return RepresentativeReading(
            metric_type=metric_type,
            value=None,
            timestamp=raw_chosen["timestamp"],
            measurement_id=raw_chosen["id"],
            sensor_id=s_obj["id"] if s_obj else None,
            sensor_name=s_obj["name"] if s_obj else None,
            sensor_type=s_obj["sensor_type"] if s_obj else None,
            is_fallback=is_comb,
            is_stale=False,
            is_valid=False,
            freshness=FRESHNESS_UNAVAILABLE,
        )

    return RepresentativeReading(
        metric_type=metric_type,
        value=None,
        timestamp=None,
        measurement_id=None,
        sensor_id=None,
        sensor_name=None,
        sensor_type=None,
        is_fallback=False,
        is_stale=False,
        is_valid=False,
        freshness=FRESHNESS_UNAVAILABLE,
    )


def _process_metric_sequence(
    conn: sqlite3.Connection,
    zone_id: int,
    metric_type: str,
    threshold: float,
    last_processed_id: Optional[int],
    current_consecutive_count: int,
    ref_time: datetime,
) -> Tuple[int, Optional[int]]:
    """Traite les nouvelles mesures chronologiques pour une métrique donnée.

    Garantit :
    - L'incrément uniquement sur mesures distinctes non traitées.
    - La remise à zéro lors d'une mesure normale.
    - Aucune modification sur données manquantes, invalides ou obsolètes.
    - L'idempotence parfaite lors d'exécutions répétées.
    """
    sensors = sensor_repository.get_by_zone(conn, zone_id)
    dedicated_sensor = next(
        (s for s in sensors if s["sensor_type"] == metric_type and s["is_active"]),
        None,
    )
    combined_sensor = next(
        (s for s in sensors if s["sensor_type"] == "combined" and s["is_active"]),
        None,
    )

    sensor_ids = []
    if dedicated_sensor:
        sensor_ids.append(dedicated_sensor["id"])
    if combined_sensor:
        sensor_ids.append(combined_sensor["id"])

    if not sensor_ids:
        return current_consecutive_count, last_processed_id

    placeholders = ",".join("?" for _ in sensor_ids)
    query = f"""
        SELECT m.*, s.sensor_type
        FROM measurements m
        JOIN sensors s ON m.sensor_id = s.id
        WHERE m.sensor_id IN ({placeholders})
    """
    params: List = list(sensor_ids)

    if last_processed_id is not None:
        query += " AND m.id > ?"
        params.append(last_processed_id)

    query += " ORDER BY m.timestamp ASC, m.id ASC"
    cursor = conn.execute(query, params)
    new_rows = [dict(r) for r in cursor.fetchall()]

    if not new_rows:
        return current_consecutive_count, last_processed_id

    # Grouper par timestamp pour appliquer la politique de sélection au même instant
    grouped_by_time: Dict[str, Dict[str, dict]] = {}
    for row in new_rows:
        ts = row["timestamp"]
        if ts not in grouped_by_time:
            grouped_by_time[ts] = {}
        grouped_by_time[ts][row["sensor_type"]] = row

    consecutive_count = current_consecutive_count
    new_last_id = last_processed_id

    for ts, sensor_map in grouped_by_time.items():
        ded_row = sensor_map.get(metric_type)
        comb_row = sensor_map.get("combined")

        # Mise à jour de l'ID max traité
        for r in (ded_row, comb_row):
            if r:
                new_last_id = max(new_last_id or 0, r["id"])

        # Sélection représentative à cet instant
        chosen = None
        if ded_row and ded_row["quality_status"] == "valid":
            chosen = ded_row
        elif comb_row and comb_row["quality_status"] == "valid":
            chosen = comb_row

        if not chosen:
            # Donnée invalide ou manquante à cet instant : n'incrémente pas le compteur
            continue

        # Vérifier l'ancienneté à cet instant
        if is_measurement_stale(ts, ref_time):
            # Donnée obsolète : n'incrémente pas le compteur
            continue

        val = (
            chosen["pressure_bar"]
            if metric_type == "pressure"
            else chosen["flow_m3_h"]
        )
        if val is None:
            continue

        if val <= threshold:
            consecutive_count += 1
        else:
            consecutive_count = 0  # Retour à la normale réinitialise le compteur

    return consecutive_count, new_last_id


def evaluate_zone(
    conn: sqlite3.Connection,
    zone_id: int,
    reference_time: Optional[datetime] = None,
    commit: bool = True,
    process_new: bool = True,
) -> dict:
    """Évalue l'état de surveillance d'une zone et gère le cycle de vie des alertes.

    Opération transactionnelle et idempotente.
    """
    ref_time = reference_time or utc_now()
    ref_time_iso = format_iso(ref_time)

    zone = zone_repository.get_by_id(conn, zone_id)
    if zone is None:
        return {
            "zone_id": zone_id,
            "zone_code": "",
            "zone_name": "Inconnue",
            "governorate_name": "Inconnu",
            "governorate_id": 0,
            "is_active": False,
            "sensor_count": 0,
            "active_sensor_count": 0,
            "measurement_count": 0,
            "status": STATUS_INSUFFICIENT_DATA,
            "latest_pressure": None,
            "latest_flow": None,
            "pressure_timestamp": None,
            "flow_timestamp": None,
            "last_timestamp": None,
            "pressure_status": "Indisponible",
            "flow_status": "Indisponible",
            "pressure_is_fallback": False,
            "flow_is_fallback": False,
            "pressure_freshness": FRESHNESS_UNAVAILABLE,
            "flow_freshness": FRESHNESS_UNAVAILABLE,
            "data_freshness": FRESHNESS_UNAVAILABLE,
            "consecutive_low_pressure_count": 0,
            "consecutive_low_flow_count": 0,
            "active_alert": None,
        }

    sensors = sensor_repository.get_by_zone(conn, zone_id)
    active_sensors = [s for s in sensors if s["is_active"]]
    measurement_count = measurement_repository.count_by_zone(conn, zone_id)

    if not zone["is_active"]:
        return {
            "zone_id": zone["id"],
            "zone_code": zone["code"],
            "zone_name": zone["name"],
            "governorate_name": zone["governorate_name"],
            "governorate_id": zone["governorate_id"],
            "is_active": False,
            "sensor_count": len(sensors),
            "active_sensor_count": len(active_sensors),
            "measurement_count": measurement_count,
            "status": STATUS_INACTIVE,
            "latest_pressure": None,
            "latest_flow": None,
            "pressure_timestamp": None,
            "flow_timestamp": None,
            "last_timestamp": None,
            "pressure_status": "Inactive",
            "flow_status": "Inactive",
            "pressure_is_fallback": False,
            "flow_is_fallback": False,
            "pressure_freshness": FRESHNESS_UNAVAILABLE,
            "flow_freshness": FRESHNESS_UNAVAILABLE,
            "data_freshness": FRESHNESS_UNAVAILABLE,
            "consecutive_low_pressure_count": 0,
            "consecutive_low_flow_count": 0,
            "active_alert": None,
        }

    # Récupération de l'état persistant
    state = monitoring_repository.get_state(conn, zone_id)
    last_pressure_id = (
        state["last_processed_pressure_measurement_id"] if state else None
    )
    last_flow_id = state["last_processed_flow_measurement_id"] if state else None
    consec_pressure = state["consecutive_low_pressure_count"] if state else 0
    consec_flow = state["consecutive_low_flow_count"] if state else 0

    # Traitement des nouvelles lectures chronologiques
    if process_new:
        consec_pressure, last_pressure_id = _process_metric_sequence(
            conn=conn,
            zone_id=zone_id,
            metric_type="pressure",
            threshold=LOW_PRESSURE_THRESHOLD_BAR,
            last_processed_id=last_pressure_id,
            current_consecutive_count=consec_pressure,
            ref_time=ref_time,
        )

        consec_flow, last_flow_id = _process_metric_sequence(
            conn=conn,
            zone_id=zone_id,
            metric_type="flow",
            threshold=LOW_FLOW_THRESHOLD_M3_H,
            last_processed_id=last_flow_id,
            current_consecutive_count=consec_flow,
            ref_time=ref_time,
        )

    # Récupérer les lectures représentatives actuelles pour l'affichage
    rep_pressure = get_representative_reading(
        conn, zone_id, "pressure", reference_time=ref_time
    )
    rep_flow = get_representative_reading(
        conn, zone_id, "flow", reference_time=ref_time
    )

    # Détection des conditions
    is_low_pressure = consec_pressure >= CONSECUTIVE_ABNORMAL_READINGS
    is_low_flow = consec_flow >= CONSECUTIVE_ABNORMAL_READINGS
    is_interruption = is_low_pressure and is_low_flow

    # Gestion transactionnelle du cycle de vie des alertes (Section 5)
    active_interruption = alert_repository.get_active_by_zone_and_type(
        conn, zone_id, ALERT_TYPE_POSSIBLE_INTERRUPTION
    )
    active_pressure = alert_repository.get_active_by_zone_and_type(
        conn, zone_id, ALERT_TYPE_LOW_PRESSURE
    )
    active_flow = alert_repository.get_active_by_zone_and_type(
        conn, zone_id, ALERT_TYPE_LOW_FLOW
    )

    if is_interruption:
        # Alerte combinée prioritaire (CRITICAL)
        # Résoudre les alertes individuelles pour éviter les doublons contradictoires
        if active_pressure:
            alert_repository.resolve_alert(conn, active_pressure["id"], ref_time_iso)
        if active_flow:
            alert_repository.resolve_alert(conn, active_flow["id"], ref_time_iso)

        if active_interruption:
            alert_repository.update_last_detected(
                conn, active_interruption["id"], ref_time_iso
            )
        else:
            alert_repository.create_alert(
                conn,
                zone_id=zone_id,
                alert_type=ALERT_TYPE_POSSIBLE_INTERRUPTION,
                severity=SEVERITY_CRITICAL,
                message="Interruption possible : Pression et débit anormalement faibles",
                started_at=ref_time_iso,
                last_detected_at=ref_time_iso,
            )

    elif is_low_pressure and not is_low_flow:
        # Pression faible seulement
        if active_interruption:
            alert_repository.resolve_alert(conn, active_interruption["id"], ref_time_iso)
        if active_flow:
            alert_repository.resolve_alert(conn, active_flow["id"], ref_time_iso)

        if active_pressure:
            alert_repository.update_last_detected(
                conn, active_pressure["id"], ref_time_iso
            )
        else:
            alert_repository.create_alert(
                conn,
                zone_id=zone_id,
                alert_type=ALERT_TYPE_LOW_PRESSURE,
                severity=SEVERITY_WARNING,
                message="Pression anormalement basse détectée",
                started_at=ref_time_iso,
                last_detected_at=ref_time_iso,
            )

    elif is_low_flow and not is_low_pressure:
        # Débit faible seulement
        if active_interruption:
            alert_repository.resolve_alert(conn, active_interruption["id"], ref_time_iso)
        if active_pressure:
            alert_repository.resolve_alert(conn, active_pressure["id"], ref_time_iso)

        if active_flow:
            alert_repository.update_last_detected(
                conn, active_flow["id"], ref_time_iso
            )
        else:
            alert_repository.create_alert(
                conn,
                zone_id=zone_id,
                alert_type=ALERT_TYPE_LOW_FLOW,
                severity=SEVERITY_WARNING,
                message="Débit anormalement bas détecté",
                started_at=ref_time_iso,
                last_detected_at=ref_time_iso,
            )

    else:
        # Retour à la normale : résolution selon la règle de récupération (Section 5)
        if consec_pressure == 0 and consec_flow == 0:
            alert_repository.resolve_all_active_by_zone(conn, zone_id, ref_time_iso)
        else:
            if consec_pressure == 0 and active_pressure:
                alert_repository.resolve_alert(conn, active_pressure["id"], ref_time_iso)
            if consec_flow == 0 and active_flow:
                alert_repository.resolve_alert(conn, active_flow["id"], ref_time_iso)
            if active_interruption:
                alert_repository.resolve_alert(conn, active_interruption["id"], ref_time_iso)

    # Persistance de l'état de surveillance
    monitoring_repository.upsert_state(
        conn=conn,
        zone_id=zone_id,
        last_pressure_id=last_pressure_id,
        last_flow_id=last_flow_id,
        consecutive_pressure=consec_pressure,
        consecutive_flow=consec_flow,
        last_evaluated_at=ref_time_iso,
    )

    if commit:
        conn.commit()

    # Récupérer l'alerte active courante
    current_active_alerts = alert_repository.get_active_by_zone(conn, zone_id)
    top_alert = current_active_alerts[0] if current_active_alerts else None

    # Statuts individuels des métriques
    p_status = "Normal"
    if rep_pressure.value is None:
        p_status = "Indisponible"
    elif rep_pressure.is_stale:
        p_status = "Ancien"
    elif rep_pressure.value <= LOW_PRESSURE_THRESHOLD_BAR:
        p_status = "Faible"

    f_status = "Normal"
    if rep_flow.value is None:
        f_status = "Indisponible"
    elif rep_flow.is_stale:
        f_status = "Ancien"
    elif rep_flow.value <= LOW_FLOW_THRESHOLD_M3_H:
        f_status = "Faible"

    # Statut global de fraîcheur des données
    overall_freshness = FRESHNESS_RECENT
    if rep_pressure.freshness == FRESHNESS_UNAVAILABLE and rep_flow.freshness == FRESHNESS_UNAVAILABLE:
        overall_freshness = FRESHNESS_UNAVAILABLE
    elif rep_pressure.is_stale or rep_flow.is_stale:
        overall_freshness = FRESHNESS_STALE

    # Détermination du statut global de surveillance de la zone
    if measurement_count < _MIN_MEASUREMENTS or (rep_pressure.value is None and rep_flow.value is None):
        overall_status = STATUS_INSUFFICIENT_DATA
    elif rep_pressure.is_stale or rep_flow.is_stale:
        overall_status = STATUS_STALE_DATA
    elif top_alert and top_alert["alert_type"] == ALERT_TYPE_POSSIBLE_INTERRUPTION:
        overall_status = STATUS_POSSIBLE_INTERRUPTION
    elif top_alert and top_alert["alert_type"] == ALERT_TYPE_LOW_PRESSURE:
        overall_status = STATUS_LOW_PRESSURE
    elif top_alert and top_alert["alert_type"] == ALERT_TYPE_LOW_FLOW:
        overall_status = STATUS_LOW_FLOW
    else:
        overall_status = STATUS_NORMAL

    # Dernier horodatage connu
    timestamps = [ts for ts in (rep_pressure.timestamp, rep_flow.timestamp) if ts]
    latest_ts = max(timestamps) if timestamps else None

    return {
        "zone_id": zone["id"],
        "zone_code": zone["code"],
        "zone_name": zone["name"],
        "governorate_name": zone["governorate_name"],
        "governorate_id": zone["governorate_id"],
        "is_active": bool(zone["is_active"]),
        "sensor_count": len(sensors),
        "active_sensor_count": len(active_sensors),
        "measurement_count": measurement_count,
        "status": overall_status,
        "latest_pressure": rep_pressure.value,
        "latest_flow": rep_flow.value,
        "pressure_timestamp": rep_pressure.timestamp,
        "flow_timestamp": rep_flow.timestamp,
        "last_timestamp": latest_ts,
        "pressure_status": p_status,
        "flow_status": f_status,
        "pressure_is_fallback": rep_pressure.is_fallback,
        "flow_is_fallback": rep_flow.is_fallback,
        "pressure_freshness": rep_pressure.freshness,
        "flow_freshness": rep_flow.freshness,
        "data_freshness": overall_freshness,
        "consecutive_low_pressure_count": consec_pressure,
        "consecutive_low_flow_count": consec_flow,
        "active_alert": top_alert,
    }


def evaluate_all_zones(
    conn: sqlite3.Connection,
    reference_time: Optional[datetime] = None,
    commit: bool = True,
    process_new: bool = True,
) -> List[dict]:
    """Évalue toutes les zones configurées dans le système."""
    zones = zone_repository.get_all(conn)
    results = [
        evaluate_zone(
            conn,
            z["id"],
            reference_time=reference_time,
            commit=False,
            process_new=process_new,
        )
        for z in zones
    ]
    if commit:
        conn.commit()
    return results


def process_measurement(
    conn: sqlite3.Connection,
    measurement_id: int,
    reference_time: Optional[datetime] = None,
    commit: bool = True,
) -> Optional[dict]:
    """Process a newly saved measurement exactly once in its zone."""
    row = conn.execute(
        """
        SELECT m.id, s.zone_id
        FROM measurements m
        JOIN sensors s ON s.id = m.sensor_id
        WHERE m.id = ?
        """,
        (measurement_id,),
    ).fetchone()
    if row is None:
        return None

    return evaluate_zone(
        conn,
        row["zone_id"],
        reference_time=reference_time,
        commit=commit,
        process_new=True,
    )


def get_zone_status(
    conn: sqlite3.Connection,
    zone_id: int,
    reference_time: Optional[datetime] = None,
    process_new: bool = True,
) -> str:
    """Détermine le statut de surveillance d'une zone (compatible Sprint 1 & 2)."""
    eval_result = evaluate_zone(
        conn,
        zone_id,
        reference_time=reference_time,
        process_new=process_new,
    )
    return eval_result["status"]


def get_all_zone_statuses(
    conn: sqlite3.Connection,
    reference_time: Optional[datetime] = None,
    process_new: bool = True,
) -> List[dict]:
    """Récupère le statut de surveillance de toutes les zones (compatible Sprint 1 & 2)."""
    return evaluate_all_zones(
        conn,
        reference_time=reference_time,
        process_new=process_new,
    )


def get_monitoring_summary(
    conn: sqlite3.Connection,
    zone_statuses: Optional[List[dict]] = None,
) -> dict:
    """Calcule les indicateurs agrégés de surveillance (Section 9.1).

    Garantit qu'aucune zone n'est comptée deux fois.
    """
    statuses = zone_statuses or get_all_zone_statuses(conn)

    total_zones = len(statuses)
    normal_count = sum(1 for z in statuses if z["status"] == STATUS_NORMAL)
    insufficient_count = sum(
        1 for z in statuses if z["status"] == STATUS_INSUFFICIENT_DATA
    )
    stale_count = sum(1 for z in statuses if z["status"] == STATUS_STALE_DATA)
    warning_count = sum(
        1 for z in statuses if z["status"] in (STATUS_LOW_PRESSURE, STATUS_LOW_FLOW)
    )
    interruption_count = sum(
        1 for z in statuses if z["status"] == STATUS_POSSIBLE_INTERRUPTION
    )
    inactive_count = sum(1 for z in statuses if z["status"] == STATUS_INACTIVE)
    active_alerts_count = alert_repository.count_active(conn)

    return {
        "total_zones": total_zones,
        "normal_zones": normal_count,
        "insufficient_data_zones": insufficient_count,
        "stale_data_zones": stale_count,
        "warning_zones": warning_count,
        "interruption_zones": interruption_count,
        "inactive_zones": inactive_count,
        "total_active_alerts": active_alerts_count,
    }
