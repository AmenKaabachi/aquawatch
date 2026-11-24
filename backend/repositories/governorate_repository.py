"""Repository des gouvernorats.

Fournit l'accès en lecture aux données des gouvernorats
stockées dans la base SQLite.
"""

import sqlite3
from typing import List, Optional


def get_all(conn: sqlite3.Connection) -> List[dict]:
    """Récupère tous les gouvernorats, triés par ID."""
    cursor = conn.execute("SELECT * FROM governorates ORDER BY id")
    return [dict(row) for row in cursor.fetchall()]


def get_by_id(conn: sqlite3.Connection, gov_id: int) -> Optional[dict]:
    """Récupère un gouvernorat par son identifiant.

    Returns:
        Dictionnaire du gouvernorat, ou ``None`` si introuvable.
    """
    cursor = conn.execute(
        "SELECT * FROM governorates WHERE id = ?", (gov_id,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def count(conn: sqlite3.Connection) -> int:
    """Retourne le nombre total de gouvernorats."""
    cursor = conn.execute("SELECT COUNT(*) FROM governorates")
    return cursor.fetchone()[0]
