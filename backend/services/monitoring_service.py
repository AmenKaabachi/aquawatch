"""Service de surveillance pour AquaWatch Grand Tunis.

Fournit les statuts de surveillance pour chaque zone.
Pour Sprint 1, les statuts sont limités à :
- Normal : zone active avec suffisamment de données.
- Données insuffisantes : zone active mais < 10 mesures.
- Inactive : zone désactivée.

L'algorithme de détection des coupures d'eau sera ajouté
dans un sprint ultérieur.
"""

import sqlite3
from typing import List

from backend.config import STATUS_INACTIVE, STATUS_INSUFFICIENT_DATA, STATUS_NORMAL
from backend.repositories import measurement_repository, sensor_repository, zone_repository

# Seuil minimal de mesures pour considérer les données suffisantes
_MIN_MEASUREMENTS = 10


def get_zone_status(conn: sqlite3.Connection, zone_id: int) -> str:
    """Détermine le statut de surveillance d'une zone.

    Args:
        conn: Connexion à la base de données.
        zone_id: Identifiant de la zone.

    Returns:
        Chaîne représentant le statut de la zone.
    """
    zone = zone_repository.get_by_id(conn, zone_id)

    if zone is None:
        return STATUS_INSUFFICIENT_DATA

    if not zone["is_active"]:
        return STATUS_INACTIVE

    measurement_count = measurement_repository.count_by_zone(conn, zone_id)

    if measurement_count < _MIN_MEASUREMENTS:
        return STATUS_INSUFFICIENT_DATA

    return STATUS_NORMAL


def get_all_zone_statuses(conn: sqlite3.Connection) -> List[dict]:
    """Récupère le statut de surveillance de toutes les zones.

    Returns:
        Liste de dictionnaires contenant les informations
        de chaque zone et son statut de surveillance.
    """
    zones = zone_repository.get_all(conn)
    result: List[dict] = []

    for zone in zones:
        status = get_zone_status(conn, zone["id"])
        sensors = sensor_repository.get_by_zone(conn, zone["id"])
        active_sensors = [s for s in sensors if s["is_active"]]
        measurement_count = measurement_repository.count_by_zone(conn, zone["id"])

        result.append(
            {
                "zone_id": zone["id"],
                "zone_code": zone["code"],
                "zone_name": zone["name"],
                "governorate_name": zone["governorate_name"],
                "is_active": bool(zone["is_active"]),
                "sensor_count": len(sensors),
                "active_sensor_count": len(active_sensors),
                "measurement_count": measurement_count,
                "status": status,
            }
        )

    return result
