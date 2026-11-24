"""Repository des capteurs virtuels.

Fournit l'accès en lecture aux capteurs avec jointures
vers la zone et le gouvernorat associés.
"""

import sqlite3
from typing import List, Optional

_BASE_QUERY = """
    SELECT s.*, z.name AS zone_name, z.code AS zone_code,
           g.name AS governorate_name
    FROM sensors s
    JOIN monitoring_zones z ON s.zone_id = z.id
    JOIN governorates g ON z.governorate_id = g.id
"""

_ZONE_QUERY = """
    SELECT s.*, z.name AS zone_name, z.code AS zone_code
    FROM sensors s
    JOIN monitoring_zones z ON s.zone_id = z.id
"""


def get_all(conn: sqlite3.Connection) -> List[dict]:
    """Récupère tous les capteurs."""
    cursor = conn.execute(f"{_BASE_QUERY} ORDER BY s.id")
    return [dict(row) for row in cursor.fetchall()]


def get_by_zone(conn: sqlite3.Connection, zone_id: int) -> List[dict]:
    """Récupère les capteurs d'une zone donnée."""
    cursor = conn.execute(
        f"{_ZONE_QUERY} WHERE s.zone_id = ? ORDER BY s.id",
        (zone_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def get_by_id(conn: sqlite3.Connection, sensor_id: int) -> Optional[dict]:
    """Récupère un capteur par son identifiant."""
    cursor = conn.execute(
        f"{_ZONE_QUERY} WHERE s.id = ?", (sensor_id,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def get_active(conn: sqlite3.Connection) -> List[dict]:
    """Récupère tous les capteurs actifs."""
    cursor = conn.execute(
        f"{_BASE_QUERY} WHERE s.is_active = 1 ORDER BY s.id"
    )
    return [dict(row) for row in cursor.fetchall()]


def count(conn: sqlite3.Connection) -> int:
    """Retourne le nombre total de capteurs."""
    cursor = conn.execute("SELECT COUNT(*) FROM sensors")
    return cursor.fetchone()[0]


def count_active(conn: sqlite3.Connection) -> int:
    """Retourne le nombre de capteurs actifs."""
    cursor = conn.execute(
        "SELECT COUNT(*) FROM sensors WHERE is_active = 1"
    )
    return cursor.fetchone()[0]
