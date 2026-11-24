"""Gestion des connexions SQLite pour AquaWatch.

Fournit une fonction de connexion et un context manager
pour gérer proprement l'ouverture/fermeture des connexions.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from backend.config import DATABASE_PATH


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Crée et retourne une connexion SQLite.

    La connexion a les clés étrangères activées et utilise
    ``sqlite3.Row`` comme row_factory pour accéder aux colonnes
    par nom.

    Args:
        db_path: Chemin vers la base de données.
                 Utilise le chemin par défaut si non spécifié.

    Returns:
        Connexion SQLite configurée.
    """
    path = str(db_path or DATABASE_PATH)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db(db_path: Optional[Path] = None):
    """Context manager pour une connexion SQLite.

    Usage::

        with get_db() as conn:
            cursor = conn.execute("SELECT ...")

    Args:
        db_path: Chemin optionnel vers la base de données.

    Yields:
        Connexion SQLite configurée.
    """
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()
