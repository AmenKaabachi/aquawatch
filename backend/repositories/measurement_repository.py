"""Repository des mesures.

Fournit l'insertion et la lecture des mesures simulées
avec filtrage par gouvernorat, zone et capteur.
"""

import sqlite3
from typing import List, Optional

_BASE_QUERY = """
    SELECT m.*, s.name AS sensor_name, s.sensor_type,
           z.name AS zone_name, z.code AS zone_code,
           g.name AS governorate_name
    FROM measurements m
    JOIN sensors s ON m.sensor_id = s.id
    JOIN monitoring_zones z ON s.zone_id = z.id
    JOIN governorates g ON z.governorate_id = g.id
"""


def insert_many(conn: sqlite3.Connection, measurements: List[dict]) -> int:
    """Insère un lot de mesures dans la base de données.

    Args:
        conn: Connexion SQLite.
        measurements: Liste de dictionnaires contenant les champs
            ``sensor_id``, ``timestamp``, ``pressure_bar``,
            ``flow_m3_h``, ``quality_status``, ``data_origin``.

    Returns:
        Nombre de mesures insérées.
    """
    conn.executemany(
        """
        INSERT INTO measurements
            (sensor_id, timestamp, pressure_bar, flow_m3_h,
             quality_status, data_origin)
        VALUES
            (:sensor_id, :timestamp, :pressure_bar, :flow_m3_h,
             :quality_status, :data_origin)
        """,
        measurements,
    )
    conn.commit()
    return len(measurements)


def get_recent(conn: sqlite3.Connection, limit: int = 100) -> List[dict]:
    """Récupère les mesures les plus récentes."""
    cursor = conn.execute(
        f"{_BASE_QUERY} ORDER BY m.timestamp DESC LIMIT ?", (limit,)
    )
    return [dict(row) for row in cursor.fetchall()]


def get_by_sensor(
    conn: sqlite3.Connection, sensor_id: int, limit: int = 100
) -> List[dict]:
    """Récupère les mesures d'un capteur donné."""
    cursor = conn.execute(
        f"""
        SELECT m.*, s.name AS sensor_name, s.sensor_type
        FROM measurements m
        JOIN sensors s ON m.sensor_id = s.id
        WHERE m.sensor_id = ?
        ORDER BY m.timestamp DESC
        LIMIT ?
        """,
        (sensor_id, limit),
    )
    return [dict(row) for row in cursor.fetchall()]


def get_by_zone(
    conn: sqlite3.Connection, zone_id: int, limit: int = 200
) -> List[dict]:
    """Récupère les mesures des capteurs d'une zone."""
    cursor = conn.execute(
        f"""
        SELECT m.*, s.name AS sensor_name, s.sensor_type,
               z.name AS zone_name
        FROM measurements m
        JOIN sensors s ON m.sensor_id = s.id
        JOIN monitoring_zones z ON s.zone_id = z.id
        WHERE z.id = ?
        ORDER BY m.timestamp DESC
        LIMIT ?
        """,
        (zone_id, limit),
    )
    return [dict(row) for row in cursor.fetchall()]


def get_latest_by_sensor(
    conn: sqlite3.Connection, sensor_id: int
) -> Optional[dict]:
    """Récupère la mesure la plus récente d'un capteur."""
    cursor = conn.execute(
        """
        SELECT m.*, s.name AS sensor_name, s.sensor_type
        FROM measurements m
        JOIN sensors s ON m.sensor_id = s.id
        WHERE m.sensor_id = ?
        ORDER BY m.timestamp DESC
        LIMIT 1
        """,
        (sensor_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def count_all(conn: sqlite3.Connection) -> int:
    """Retourne le nombre total de mesures."""
    cursor = conn.execute("SELECT COUNT(*) FROM measurements")
    return cursor.fetchone()[0]


def count_by_zone(conn: sqlite3.Connection, zone_id: int) -> int:
    """Retourne le nombre de mesures pour une zone donnée."""
    cursor = conn.execute(
        """
        SELECT COUNT(*) FROM measurements m
        JOIN sensors s ON m.sensor_id = s.id
        WHERE s.zone_id = ?
        """,
        (zone_id,),
    )
    return cursor.fetchone()[0]


def get_filtered(
    conn: sqlite3.Connection,
    governorate_id: Optional[int] = None,
    zone_id: Optional[int] = None,
    sensor_id: Optional[int] = None,
    limit: int = 100,
) -> List[dict]:
    """Récupère les mesures avec des filtres optionnels.

    Tous les filtres sont combinés avec AND.

    Args:
        conn: Connexion SQLite.
        governorate_id: Filtre par gouvernorat (optionnel).
        zone_id: Filtre par zone (optionnel).
        sensor_id: Filtre par capteur (optionnel).
        limit: Nombre maximum de résultats.

    Returns:
        Liste de mesures correspondant aux filtres.
    """
    query = _BASE_QUERY
    conditions: List[str] = []
    params: List = []

    if governorate_id is not None:
        conditions.append("g.id = ?")
        params.append(governorate_id)
    if zone_id is not None:
        conditions.append("z.id = ?")
        params.append(zone_id)
    if sensor_id is not None:
        conditions.append("s.id = ?")
        params.append(sensor_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY m.timestamp DESC LIMIT ?"
    params.append(limit)

    cursor = conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]
