"""Utilitaires pour la gestion du temps.

Fournit des fonctions cohérentes pour créer, formater et parser
des horodatages ISO 8601 en UTC.
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Retourne l'heure actuelle en UTC."""
    return datetime.now(timezone.utc)


def format_iso(dt: datetime) -> str:
    """Formate un datetime en chaîne ISO 8601 (suffixe Z pour UTC).

    Args:
        dt: Objet datetime à formater.

    Returns:
        Chaîne au format ``YYYY-MM-DDTHH:MM:SSZ``.
    """
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str) -> datetime:
    """Parse une chaîne ISO 8601 en datetime UTC.

    Accepte le suffixe ``Z`` ou ``+00:00``.

    Args:
        s: Chaîne ISO 8601.

    Returns:
        Objet datetime conscient du fuseau horaire (UTC).
    """
    s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s)
