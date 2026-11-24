"""Structures de données pour AquaWatch Grand Tunis.

Dataclasses représentant les entités principales du système.
Ces structures servent à la documentation et à la lisibilité du code.
Les repositories retournent des dictionnaires (sqlite3.Row) pour la simplicité.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Governorate:
    """Représente un gouvernorat du Grand Tunis."""

    id: int
    name: str
    population: Optional[int] = None


@dataclass
class MonitoringZone:
    """Représente une zone de surveillance hypothétique."""

    id: int
    code: str
    governorate_id: int
    name: str
    description: str = ""
    is_active: bool = True


@dataclass
class Sensor:
    """Représente un capteur virtuel.

    Les capteurs ne sont pas connectés à du matériel physique.
    """

    id: int
    zone_id: int
    name: str
    sensor_type: str  # 'pressure', 'flow', 'combined'
    is_active: bool = True


@dataclass
class Measurement:
    """Représente une mesure simulée d'un capteur.

    Attributes:
        sensor_id: Identifiant du capteur source.
        timestamp: Horodatage ISO 8601.
        pressure_bar: Pression en bar (peut être None).
        flow_m3_h: Débit en m³/h (peut être None).
                    ``None`` signifie que le type du capteur ne mesure pas
                    cette variable, et non une valeur nulle.
        quality_status: Statut de qualité ('valid', 'suspect', 'invalid').
        data_origin: Origine des données ('SIMULATED').
        id: Identifiant auto-généré par la BDD.
    """

    sensor_id: int
    timestamp: str
    pressure_bar: Optional[float] = None
    flow_m3_h: Optional[float] = None
    quality_status: str = "valid"
    data_origin: str = "SIMULATED"
    id: Optional[int] = None
