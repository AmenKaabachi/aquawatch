"""Fixtures partagées pour les tests AquaWatch.

Fournit une base de données temporaire initialisée
pour chaque test, garantissant l'isolation entre les tests.
"""

import pytest

from backend.database.connection import get_connection
from backend.database.init_db import init_database


@pytest.fixture
def test_db_path(tmp_path):
    """Fournit un chemin temporaire pour la base de données de test."""
    return tmp_path / "test_aquawatch.db"


@pytest.fixture
def test_db(test_db_path):
    """Crée et initialise une base de données de test temporaire.

    La base est créée dans un répertoire temporaire et supprimée
    automatiquement après le test.

    Yields:
        sqlite3.Connection: Connexion à la base de données de test.
    """
    init_database(test_db_path)
    conn = get_connection(test_db_path)
    yield conn
    conn.close()
