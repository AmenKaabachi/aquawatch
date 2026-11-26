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
from datetime import datetime, timedelta
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

    now = utc_now().replace(minute=0, second=0, microsecond=0)
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


def generate_sensor_measurement(
    sensor: dict,
    timestamp,
    rng: random.Random,
) -> dict:
    """Génère une unique mesure selon le type du capteur.

    Cette fonction réutilise les fonctions de simulation de pression et de débit
    existantes afin que la collection séquentielle et asyncio produisent les
    mêmes types de valeurs.
    """
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

    return {
        "sensor_id": sensor["id"],
        "timestamp": format_iso(timestamp),
        "pressure_bar": pressure,
        "flow_m3_h": flow,
        "quality_status": "valid",
        "data_origin": DATA_ORIGIN_SIMULATED,
    }


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


def generate_abnormal_measurements(
    conn: sqlite3.Connection,
    zone_id: int,
    condition: str = "interruption",
    count: int = 3,
    base_time: Optional[datetime] = None,
    save: bool = True,
) -> List[dict]:
    """Génère des mesures anormales contrôlées pour une zone (Sprint 2).

    Permet de tester et de démontrer la détection des coupures et alertes.
    Toutes les mesures sont marquées explicitement data_origin = 'SIMULATED'.

    Args:
        conn: Connexion SQLite.
        zone_id: Identifiant de la zone cible.
        condition: 'interruption', 'low_pressure', 'low_flow' ou 'normal'.
        count: Nombre de mesures consécutives à générer.
        base_time: Horodatage de début (utc_now() par défaut).
        save: Si True, enregistre en base.

    Returns:
        Liste des mesures générées.
    """
    sensors = sensor_repository.get_by_zone(conn, zone_id)
    if not sensors:
        return []

    now = base_time or utc_now()
    # On espace les mesures de 10 minutes pour former une séquence temporelle
    all_measurements: List[dict] = []

    for i in range(count):
        ts = now + timedelta(minutes=10 * i)
        ts_iso = format_iso(ts)

        for sensor in sensors:
            stype = sensor["sensor_type"]
            p_val = None
            f_val = None

            if stype in ("pressure", "combined"):
                if condition in ("low_pressure", "interruption"):
                    p_val = round(1.0 + (i * 0.1), 2)  # 1.0, 1.1, 1.2 <= 1.5 bar
                else:
                    p_val = round(3.2 + (i * 0.1), 2)  # normal > 1.5 bar

            if stype in ("flow", "combined"):
                if condition in ("low_flow", "interruption"):
                    f_val = round(25.0 + (i * 5.0), 2)  # 25, 30, 35 <= 50.0 m³/h
                else:
                    f_val = round(180.0 + (i * 5.0), 2)  # normal > 50.0 m³/h

            all_measurements.append(
                {
                    "sensor_id": sensor["id"],
                    "timestamp": ts_iso,
                    "pressure_bar": p_val,
                    "flow_m3_h": f_val,
                    "quality_status": "valid",
                    "data_origin": DATA_ORIGIN_SIMULATED,
                }
            )

    if save and all_measurements:
        measurement_repository.insert_many(conn, all_measurements)

    return all_measurements

