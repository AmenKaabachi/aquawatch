"""Service de simulation de mesures pour AquaWatch Grand Tunis.

Génère des mesures simulées de pression et de débit pour les
capteurs virtuels du réseau de surveillance. Toutes les mesures
sont clairement identifiées comme SIMULÉES (data_origin = 'SIMULATED').

Le simulateur produit des valeurs réalistes avec :
- Un profil de consommation journalier (pics matin/soir).
- Des variations de pression inversement liées à la consommation.
- Du bruit gaussien pour simuler les fluctuations réelles.
- Reproductibilité via une graine aléatoire configurable.
"""

import math
import random
import sqlite3
from datetime import timedelta
from typing import List, Optional

from backend.config import (
    DATA_ORIGIN_SIMULATED,
    MEASUREMENTS_PER_SENSOR,
    SIMULATION_FLOW_MAX,
    SIMULATION_FLOW_MIN,
    SIMULATION_PRESSURE_MAX,
    SIMULATION_PRESSURE_MIN,
)
from backend.repositories import measurement_repository, sensor_repository
from backend.utils.time_utils import format_iso, utc_now


def generate_measurements(
    conn: sqlite3.Connection,
    seed: Optional[int] = None,
    count_per_sensor: int = MEASUREMENTS_PER_SENSOR,
    save: bool = True,
) -> List[dict]:
    """Génère un lot de mesures simulées pour tous les capteurs actifs.

    Args:
        conn: Connexion à la base de données.
        seed: Graine aléatoire pour la reproductibilité.
              ``None`` pour un comportement aléatoire.
        count_per_sensor: Nombre de mesures à générer par capteur.
        save: Si ``True``, enregistre les mesures dans la BDD.

    Returns:
        Liste de dictionnaires contenant les mesures générées.
    """
    rng = random.Random(seed)
    sensors = sensor_repository.get_active(conn)

    if not sensors:
        return []

    now = utc_now()
    base_time = now - timedelta(hours=count_per_sensor)
    all_measurements: List[dict] = []

    for sensor in sensors:
        sensor_measurements = _generate_sensor_measurements(
            sensor=sensor,
            base_time=base_time,
            count=count_per_sensor,
            rng=rng,
        )
        all_measurements.extend(sensor_measurements)

    if save and all_measurements:
        measurement_repository.insert_many(conn, all_measurements)

    return all_measurements


def _generate_sensor_measurements(
    sensor: dict,
    base_time,
    count: int,
    rng: random.Random,
) -> List[dict]:
    """Génère des mesures pour un capteur individuel.

    Les valeurs suivent un profil journalier réaliste :
    - Pression : varie autour de 3,5 bar avec des creux aux heures de pointe.
    - Débit : plus élevé aux heures de consommation (6h-9h, 17h-21h).
    """
    measurements: List[dict] = []

    sensor_type = sensor["sensor_type"]
    base_pressure = (
        3.5 + rng.uniform(-0.5, 0.5)
        if sensor_type in ("pressure", "combined")
        else None
    )
    base_flow = (
        200.0 + rng.uniform(-30.0, 30.0)
        if sensor_type in ("flow", "combined")
        else None
    )

    for i in range(count):
        timestamp = base_time + timedelta(hours=i)
        hour = timestamp.hour

        pressure = (
            round(_simulate_pressure(base_pressure, hour, rng), 2)
            if base_pressure is not None
            else None
        )
        flow = (
            round(_simulate_flow(base_flow, hour, rng), 2)
            if base_flow is not None
            else None
        )

        measurements.append(
            {
                "sensor_id": sensor["id"],
                "timestamp": format_iso(timestamp),
                "pressure_bar": pressure,
                "flow_m3_h": flow,
                "quality_status": "valid",
                "data_origin": DATA_ORIGIN_SIMULATED,
            }
        )

    return measurements


def _simulate_pressure(base: float, hour: int, rng: random.Random) -> float:
    """Simule une valeur de pression réaliste.

    La pression varie avec un cycle journalier :
    - Plus basse aux heures de forte consommation (matin, soir).
    - Plus haute pendant la nuit.
    """
    # Variation cyclique journalière
    daily_variation = 0.4 * math.sin(2 * math.pi * (hour - 6) / 24)

    # Baisse de pression aux heures de pointe
    peak_drop = 0.0
    if 6 <= hour <= 9:
        peak_drop = -0.3
    elif 17 <= hour <= 21:
        peak_drop = -0.4

    # Bruit gaussien
    noise = rng.gauss(0, 0.15)

    pressure = base + daily_variation + peak_drop + noise
    return max(SIMULATION_PRESSURE_MIN, min(SIMULATION_PRESSURE_MAX, pressure))


def _simulate_flow(base: float, hour: int, rng: random.Random) -> float:
    """Simule une valeur de débit réaliste.

    Le débit suit un profil de consommation urbaine typique :
    - Faible consommation la nuit (0h-5h).
    - Pics le matin (6h-9h) et le soir (17h-21h).
    - Consommation modérée en journée (10h-16h).
    """
    if 0 <= hour <= 5:
        hour_factor = 0.4
    elif 6 <= hour <= 9:
        hour_factor = 1.5
    elif 10 <= hour <= 16:
        hour_factor = 0.9
    elif 17 <= hour <= 21:
        hour_factor = 1.4
    else:
        hour_factor = 0.6

    noise = rng.gauss(0, 20)
    flow = base * hour_factor + noise
    return max(SIMULATION_FLOW_MIN, min(SIMULATION_FLOW_MAX, flow))
