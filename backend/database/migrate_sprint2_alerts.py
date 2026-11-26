"""Migration sécurisée pour le Sprint 2 : Alertes et état de surveillance.

Ce script :
1. Crée une sauvegarde horodatée et vérifiée de la base de données.
2. Crée les tables ``alerts`` et ``monitoring_states`` si elles n'existent pas.
3. Crée les index associés.
4. Préserve l'intégralité des mesures et capteurs existants (1152 mesures, 24 capteurs).
5. Vérifie l'intégrité référentielle et structurelle.

Usage en ligne de commande::

    python -m backend.database.migrate_sprint2_alerts
"""

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from backend.config import DATABASE_PATH, SCHEMA_PATH
from backend.database.connection import get_connection


def _create_backup(db_path: Path) -> Path:
    """Crée une sauvegarde horodatée de la base et valide son intégrité."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = db_path.with_name(
        f"{db_path.stem}.backup-{timestamp}{db_path.suffix}"
    )
    if backup_path.exists():
        raise FileExistsError(f"Le fichier de sauvegarde existe déjà : {backup_path}")

    source = sqlite3.connect(str(db_path))
    target = sqlite3.connect(str(backup_path))
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()

    backup = sqlite3.connect(f"file:{backup_path.as_posix()}?mode=ro", uri=True)
    source = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        integrity = backup.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"Échec du contrôle d'intégrité de la sauvegarde : {integrity}")
        if backup.execute("SELECT COUNT(*) FROM measurements").fetchone()[0] != (
            source.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
        ):
            raise RuntimeError("Le nombre de mesures dans la sauvegarde ne correspond pas à la source")
    finally:
        backup.close()
        source.close()
    return backup_path


def migrate_sprint2_alerts(
    db_path: Optional[Path] = None,
) -> Dict[str, object]:
    """Applique les migrations du Sprint 2 en toute sécurité."""
    path = Path(db_path or DATABASE_PATH)
    if not path.is_file():
        raise FileNotFoundError(f"La base de données n'existe pas : {path}")

    backup_path = _create_backup(path)
    conn = get_connection(path)
    try:
        conn.execute("BEGIN IMMEDIATE")

        # Compte initial des mesures pour vérification de non-régression
        initial_measurements_count = conn.execute(
            "SELECT COUNT(*) FROM measurements"
        ).fetchone()[0]
        initial_sensors_count = conn.execute(
            "SELECT COUNT(*) FROM sensors"
        ).fetchone()[0]

        # Application du schéma complet (idempotent grâce à CREATE TABLE IF NOT EXISTS)
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        # Vérification post-migration
        post_measurements_count = conn.execute(
            "SELECT COUNT(*) FROM measurements"
        ).fetchone()[0]
        post_sensors_count = conn.execute(
            "SELECT COUNT(*) FROM sensors"
        ).fetchone()[0]

        if post_measurements_count != initial_measurements_count:
            raise RuntimeError(
                f"Nombre de mesures altéré : {initial_measurements_count} -> {post_measurements_count}"
            )

        if post_sensors_count != initial_sensors_count:
            raise RuntimeError(
                f"Nombre de capteurs altéré : {initial_sensors_count} -> {post_sensors_count}"
            )

        foreign_key_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise RuntimeError(f"Échec des clés étrangères : {foreign_key_errors}")

        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"Échec du contrôle d'intégrité SQLite : {integrity}")

        conn.commit()
        return {
            "backup_path": backup_path,
            "measurements_preserved": post_measurements_count,
            "sensors_preserved": post_sensors_count,
            "integrity": integrity,
        }
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    result = migrate_sprint2_alerts()
    print(f"✅ Migration Sprint 2 réussie !")
    print(f"   📦 Sauvegarde créée : {result['backup_path']}")
    print(f"   📊 Mesures préservées : {result['measurements_preserved']}")
    print(f"   📡 Capteurs préservés : {result['sensors_preserved']}")
    print(f"   🛡️ Intégrité : {result['integrity']}")
