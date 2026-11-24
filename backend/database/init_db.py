"""Initialisation de la base de données AquaWatch Grand Tunis.

Ce script crée la base de données SQLite, applique le schéma
(schema.sql) et insère les données de référence (seed.sql).
Il est conçu pour être idempotent : l'exécuter plusieurs fois
ne duplique pas les données grâce à INSERT OR IGNORE.

Usage en ligne de commande::

    python -m backend.database.init_db
"""

import sys
from pathlib import Path
from typing import Optional

from backend.config import DATABASE_PATH, DATABASE_DIR, SCHEMA_PATH, SEED_PATH
from backend.database.connection import get_connection


def init_database(db_path: Optional[Path] = None) -> bool:
    """Initialise la base de données SQLite.

    Args:
        db_path: Chemin de la base de données.
                 Utilise le chemin par défaut si ``None``.

    Returns:
        ``True`` si l'initialisation a réussi, ``False`` sinon.
    """
    if db_path is None:
        db_path = DATABASE_PATH
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection(db_path)
    try:
        # Appliquer le schéma
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)

        # Insérer les données initiales
        seed_sql = SEED_PATH.read_text(encoding="utf-8")
        conn.executescript(seed_sql)

        conn.commit()

        # Vérification rapide
        gov_count = conn.execute("SELECT COUNT(*) FROM governorates").fetchone()[0]
        zone_count = conn.execute("SELECT COUNT(*) FROM monitoring_zones").fetchone()[0]
        sensor_count = conn.execute("SELECT COUNT(*) FROM sensors").fetchone()[0]

        print(f"✅ Base de données initialisée : {db_path}")
        print(f"   📍 {gov_count} gouvernorats")
        print(f"   🗺️  {zone_count} zones de surveillance")
        print(f"   📡 {sensor_count} capteurs virtuels")
        return True

    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation : {e}", file=sys.stderr)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
