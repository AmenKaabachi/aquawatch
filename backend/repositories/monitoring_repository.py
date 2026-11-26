"""Repository de l'état de surveillance (Sprint 2).

Gère la persistance de l'état séquentiel de chaque zone (dernières mesures
traitées, compteurs consécutifs anormaux).
"""

import sqlite3
from typing import Optional


def get_state(conn: sqlite3.Connection, zone_id: int) -> Optional[dict]:
    """Récupère l'état de surveillance enregistré pour une zone."""
    cursor = conn.execute(
        """
        SELECT zone_id, last_processed_pressure_measurement_id,
               last_processed_flow_measurement_id,
               consecutive_low_pressure_count,
               consecutive_low_flow_count,
               last_evaluated_at
        FROM monitoring_states
        WHERE zone_id = ?
        """,
        (zone_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def upsert_state(
    conn: sqlite3.Connection,
    zone_id: int,
    last_pressure_id: Optional[int],
    last_flow_id: Optional[int],
    consecutive_pressure: int,
    consecutive_flow: int,
    last_evaluated_at: str,
) -> None:
    """Enregistre ou met à jour l'état de surveillance d'une zone."""
    conn.execute(
        """
        INSERT INTO monitoring_states (
            zone_id, last_processed_pressure_measurement_id,
            last_processed_flow_measurement_id,
            consecutive_low_pressure_count,
            consecutive_low_flow_count,
            last_evaluated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(zone_id) DO UPDATE SET
            last_processed_pressure_measurement_id = excluded.last_processed_pressure_measurement_id,
            last_processed_flow_measurement_id = excluded.last_processed_flow_measurement_id,
            consecutive_low_pressure_count = excluded.consecutive_low_pressure_count,
            consecutive_low_flow_count = excluded.consecutive_low_flow_count,
            last_evaluated_at = excluded.last_evaluated_at
        """,
        (
            zone_id,
            last_pressure_id,
            last_flow_id,
            consecutive_pressure,
            consecutive_flow,
            last_evaluated_at,
        ),
    )
def reset_state_for_zone(conn: sqlite3.Connection, zone_id: int) -> None:
    """Réinitialise l'état de surveillance d'une zone."""
    conn.execute(
        """
        DELETE FROM monitoring_states WHERE zone_id = ?
        """,
        (zone_id,),
    )
