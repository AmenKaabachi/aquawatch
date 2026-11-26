"""Collecte asynchrone simulée des mesures de capteurs."""

import asyncio
import random
import sqlite3
from datetime import datetime
from typing import Iterable, List, Optional, Set

from backend.repositories import measurement_repository
from backend.services.simulation_service import generate_sensor_measurement
from backend.utils.time_utils import utc_now


async def collect_sensor(
    sensor: dict,
    response_delay: float,
    timestamp: datetime,
    seed: Optional[int],
    failure_sensor_ids: Optional[Set[int]] = None,
) -> dict:
    """Attend la latence simulée puis génère une mesure pour un capteur."""
    await asyncio.sleep(response_delay)
    if failure_sensor_ids and sensor["id"] in failure_sensor_ids:
        raise RuntimeError(
            f"Échec simulé de la collecte du capteur {sensor['id']}"
        )

    sensor_seed = seed
    if sensor_seed is not None:
        sensor_seed = sensor_seed + sensor["id"]
    rng = random.Random(sensor_seed)
    return generate_sensor_measurement(sensor, timestamp, rng)


async def collect_sequential(
    sensors: Iterable[dict],
    response_delay: float,
    timestamp: Optional[datetime] = None,
    seed: Optional[int] = None,
    failure_sensor_ids: Optional[Set[int]] = None,
) -> dict:
    """Collecte les capteurs les uns après les autres."""
    sensor_list = list(sensors)
    collection_timestamp = timestamp or utc_now()
    measurements: List[dict] = []
    failures: List[dict] = []

    for sensor in sensor_list:
        try:
            measurement = await collect_sensor(
                sensor,
                response_delay,
                collection_timestamp,
                seed,
                failure_sensor_ids,
            )
            measurements.append(measurement)
        except Exception as exc:
            failures.append({"sensor_id": sensor["id"], "error": str(exc)})

    return {
        "measurements": measurements,
        "failures": failures,
        "successful": len(measurements),
        "failed": len(failures),
    }


async def collect_async(
    sensors: Iterable[dict],
    response_delay: float,
    timestamp: Optional[datetime] = None,
    seed: Optional[int] = None,
    failure_sensor_ids: Optional[Set[int]] = None,
) -> dict:
    """Collecte tous les capteurs concurrently via asyncio.gather."""
    sensor_list = list(sensors)
    collection_timestamp = timestamp or utc_now()
    tasks = [
        collect_sensor(
            sensor,
            response_delay,
            collection_timestamp,
            seed,
            failure_sensor_ids,
        )
        for sensor in sensor_list
    ]

    outcomes = await asyncio.gather(*tasks, return_exceptions=True)
    measurements: List[dict] = []
    failures: List[dict] = []

    for sensor, outcome in zip(sensor_list, outcomes):
        if isinstance(outcome, BaseException):
            failures.append({"sensor_id": sensor["id"], "error": str(outcome)})
        else:
            measurements.append(outcome)

    return {
        "measurements": measurements,
        "failures": failures,
        "successful": len(measurements),
        "failed": len(failures),
    }


def collect_and_save(
    conn: sqlite3.Connection,
    sensors: Iterable[dict],
    response_delay: float,
    seed: Optional[int] = None,
) -> dict:
    """Collecte asynchronement puis persiste par le repository existant."""
    result = asyncio.run(
        collect_async(
            sensors=sensors,
            response_delay=response_delay,
            timestamp=utc_now(),
            seed=seed,
        )
    )
    if result["measurements"]:
        result["persisted"] = measurement_repository.insert_many(
            conn,
            result["measurements"],
        )
    else:
        result["persisted"] = 0
    return result
