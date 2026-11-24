"""Repository des zones de surveillance.

Fournit l'accès en lecture aux zones de surveillance
avec jointure sur le gouvernorat associé.
"""

import sqlite3
from typing import List, Optional

_BASE_QUERY = """
    SELECT z.*, g.name AS governorate_name
    FROM monitoring_zones z
    JOIN governorates g ON z.governorate_id = g.id
"""


def get_all(conn: sqlite3.Connection) -> List[dict]:
    """Récupère toutes les zones de surveillance."""
    cursor = conn.execute(f"{_BASE_QUERY} ORDER BY z.id")
    return [dict(row) for row in cursor.fetchall()]


def get_by_governorate(conn: sqlite3.Connection, gov_id: int) -> List[dict]:
    """Récupère les zones associées à un gouvernorat."""
    cursor = conn.execute(
        f"{_BASE_QUERY} WHERE z.governorate_id = ? ORDER BY z.id",
        (gov_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def get_by_id(conn: sqlite3.Connection, zone_id: int) -> Optional[dict]:
    """Récupère une zone par son identifiant.

    Returns:
        Dictionnaire de la zone, ou ``None`` si introuvable.
    """
    cursor = conn.execute(
        f"{_BASE_QUERY} WHERE z.id = ?", (zone_id,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def count(conn: sqlite3.Connection) -> int:
    """Retourne le nombre total de zones."""
    cursor = conn.execute("SELECT COUNT(*) FROM monitoring_zones")
    return cursor.fetchone()[0]


def count_active(conn: sqlite3.Connection) -> int:
    """Retourne le nombre de zones actives."""
    cursor = conn.execute(
        "SELECT COUNT(*) FROM monitoring_zones WHERE is_active = 1"
    )
    return cursor.fetchone()[0]
