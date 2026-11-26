"""Repository des alertes (Sprint 2).

Fournit les opérations de création, mise à jour, résolution et filtrage
des alertes en base SQLite.
"""

import sqlite3
from typing import Dict, List, Optional

_BASE_ALERT_QUERY = """
    SELECT a.*, z.name AS zone_name, z.code AS zone_code,
           g.id AS governorate_id, g.name AS governorate_name
    FROM alerts a
    JOIN monitoring_zones z ON a.zone_id = z.id
    JOIN governorates g ON z.governorate_id = g.id
"""


def create_alert(
    conn: sqlite3.Connection,
    zone_id: int,
    alert_type: str,
    severity: str,
    message: str,
    started_at: str,
    last_detected_at: str,
    status: str = "ACTIVE",
) -> int:
    """Crée une nouvelle alerte et retourne son identifiant."""
    cursor = conn.execute(
        """
        INSERT INTO alerts (
            zone_id, alert_type, severity, status, message,
            started_at, last_detected_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (zone_id, alert_type, severity, status, message, started_at, last_detected_at),
    )
    return cursor.lastrowid


def update_last_detected(
    conn: sqlite3.Connection, alert_id: int, last_detected_at: str
) -> None:
    """Met à jour l'horodatage de dernière détection d'une alerte active."""
    conn.execute(
        """
        UPDATE alerts
        SET last_detected_at = ?
        WHERE id = ?
        """,
        (last_detected_at, alert_id),
    )
def resolve_alert(
    conn: sqlite3.Connection, alert_id: int, resolved_at: str
) -> None:
    """Marque une alerte comme résolue."""
    conn.execute(
        """
        UPDATE alerts
        SET status = 'RESOLVED', resolved_at = ?
        WHERE id = ? AND status = 'ACTIVE'
        """,
        (resolved_at, alert_id),
    )
def resolve_active_by_zone_and_type(
    conn: sqlite3.Connection, zone_id: int, alert_type: str, resolved_at: str
) -> int:
    """Résout toutes les alertes actives d'un type donné pour une zone."""
    cursor = conn.execute(
        """
        UPDATE alerts
        SET status = 'RESOLVED', resolved_at = ?
        WHERE zone_id = ? AND alert_type = ? AND status = 'ACTIVE'
        """,
        (resolved_at, zone_id, alert_type),
    )
    return cursor.rowcount


def resolve_all_active_by_zone(
    conn: sqlite3.Connection, zone_id: int, resolved_at: str
) -> int:
    """Résout toutes les alertes actives d'une zone."""
    cursor = conn.execute(
        """
        UPDATE alerts
        SET status = 'RESOLVED', resolved_at = ?
        WHERE zone_id = ? AND status = 'ACTIVE'
        """,
        (resolved_at, zone_id),
    )
    return cursor.rowcount


def get_active_by_zone(conn: sqlite3.Connection, zone_id: int) -> List[dict]:
    """Récupère les alertes actives pour une zone."""
    cursor = conn.execute(
        f"{_BASE_ALERT_QUERY} WHERE a.zone_id = ? AND a.status = 'ACTIVE' ORDER BY a.started_at DESC",
        (zone_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def get_active_by_zone_and_type(
    conn: sqlite3.Connection, zone_id: int, alert_type: str
) -> Optional[dict]:
    """Récupère l'alerte active correspondante pour une zone et un type."""
    cursor = conn.execute(
        f"""
        {_BASE_ALERT_QUERY}
        WHERE a.zone_id = ? AND a.alert_type = ? AND a.status = 'ACTIVE'
        LIMIT 1
        """,
        (zone_id, alert_type),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def get_all_active(conn: sqlite3.Connection) -> List[dict]:
    """Récupère toutes les alertes actuellement actives."""
    cursor = conn.execute(
        f"{_BASE_ALERT_QUERY} WHERE a.status = 'ACTIVE' ORDER BY a.started_at DESC"
    )
    return [dict(row) for row in cursor.fetchall()]


def get_resolved(conn: sqlite3.Connection, limit: int = 100) -> List[dict]:
    """Récupère l'historique des alertes résolues."""
    cursor = conn.execute(
        f"{_BASE_ALERT_QUERY} WHERE a.status = 'RESOLVED' ORDER BY a.resolved_at DESC LIMIT ?",
        (limit,),
    )
    return [dict(row) for row in cursor.fetchall()]


def get_all(conn: sqlite3.Connection, limit: int = 200) -> List[dict]:
    """Récupère toutes les alertes (actives et résolues)."""
    cursor = conn.execute(
        f"{_BASE_ALERT_QUERY} ORDER BY a.started_at DESC LIMIT ?", (limit,)
    )
    return [dict(row) for row in cursor.fetchall()]


def get_filtered(
    conn: sqlite3.Connection,
    governorate_id: Optional[int] = None,
    zone_id: Optional[int] = None,
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 200,
) -> List[dict]:
    """Filtre les alertes selon plusieurs critères combinés avec AND."""
    query = _BASE_ALERT_QUERY
    conditions: List[str] = []
    params: List = []

    if governorate_id is not None:
        conditions.append("g.id = ?")
        params.append(governorate_id)
    if zone_id is not None:
        conditions.append("z.id = ?")
        params.append(zone_id)
    if severity is not None:
        conditions.append("a.severity = ?")
        params.append(severity)
    if alert_type is not None:
        conditions.append("a.alert_type = ?")
        params.append(alert_type)
    if status is not None:
        conditions.append("a.status = ?")
        params.append(status)
    if start_date is not None:
        conditions.append("a.started_at >= ?")
        params.append(start_date)
    if end_date is not None:
        conditions.append("a.started_at <= ?")
        params.append(end_date)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY a.started_at DESC LIMIT ?"
    params.append(limit)

    cursor = conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


def count_active(conn: sqlite3.Connection) -> int:
    """Retourne le nombre total d'alertes actives."""
    cursor = conn.execute("SELECT COUNT(*) FROM alerts WHERE status = 'ACTIVE'")
    return cursor.fetchone()[0]


def count_by_status(conn: sqlite3.Connection) -> Dict[str, int]:
    """Retourne le nombre d'alertes par statut."""
    cursor = conn.execute(
        "SELECT status, COUNT(*) FROM alerts GROUP BY status"
    )
    result = {"ACTIVE": 0, "RESOLVED": 0}
    for row in cursor.fetchall():
        result[row[0]] = row[1]
    return result
