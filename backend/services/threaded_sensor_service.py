"""Blocking sensor collection using a bounded pool of worker threads."""

import math
import random
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Iterable, Optional, Set

from backend.services.simulation_service import generate_sensor_measurement
from backend.utils.time_utils import format_iso, utc_now

MAX_WORKERS = 32


def _collect_sensor(
    sensor: dict,
    response_delay: float,
    timestamp: datetime,
    seed: Optional[int],
    failure_sensor_ids: Optional[Set[int]],
) -> dict:
    started = time.perf_counter()
    started_at = utc_now()
    thread_id = threading.get_ident()
    thread_name = threading.current_thread().name

    try:
        time.sleep(response_delay)
        if failure_sensor_ids and sensor["id"] in failure_sensor_ids:
            raise RuntimeError(
                f"Échec simulé de la collecte du capteur {sensor['id']}"
            )

        sensor_seed = seed + sensor["id"] if seed is not None else None
        measurement = generate_sensor_measurement(
            sensor,
            timestamp,
            random.Random(sensor_seed),
        )
        return {
            "measurement": measurement,
            "error": None,
            "activity": {
                "sensor_id": sensor["id"],
                "thread_id": thread_id,
                "thread_name": thread_name,
                "started_at": format_iso(started_at),
                "completed_at": format_iso(utc_now()),
                "duration": time.perf_counter() - started,
                "status": "success",
            },
        }
    except Exception as exc:
        return {
            "measurement": None,
            "error": str(exc),
            "activity": {
                "sensor_id": sensor["id"],
                "thread_id": thread_id,
                "thread_name": thread_name,
                "started_at": format_iso(started_at),
                "completed_at": format_iso(utc_now()),
                "duration": time.perf_counter() - started,
                "status": "failed",
            },
        }


def collect_threaded(
    sensors: Iterable[dict],
    response_delay: float,
    max_workers: int = 4,
    timestamp: Optional[datetime] = None,
    seed: Optional[int] = None,
    failure_sensor_ids: Optional[Set[int]] = None,
) -> dict:
    """Collect sensors concurrently and return results without touching SQLite."""
    if isinstance(max_workers, bool) or not isinstance(max_workers, int):
        raise ValueError("max_workers doit être un entier.")
    if not 1 <= max_workers <= MAX_WORKERS:
        raise ValueError(f"max_workers doit être compris entre 1 et {MAX_WORKERS}.")
    if (
        isinstance(response_delay, bool)
        or not isinstance(response_delay, (int, float))
        or not math.isfinite(response_delay)
        or response_delay < 0
    ):
        raise ValueError("response_delay doit être un nombre fini positif ou nul.")

    sensor_list = list(sensors)
    sensor_ids = [sensor["id"] for sensor in sensor_list]
    if len(sensor_ids) != len(set(sensor_ids)):
        raise ValueError("La liste des capteurs contient des identifiants en double.")

    collection_timestamp = timestamp or utc_now()
    if not sensor_list:
        return {
            "measurements": [],
            "failures": [],
            "activities": [],
            "successful": 0,
            "failed": 0,
            "processed": 0,
            "worker_count": 0,
            "execution_time": 0.0,
        }

    started = time.perf_counter()
    results = {}
    with ThreadPoolExecutor(
        max_workers=min(max_workers, len(sensor_list)),
        thread_name_prefix="aquawatch-sensor",
    ) as executor:
        futures = {
            sensor["id"]: executor.submit(
                _collect_sensor,
                sensor,
                response_delay,
                collection_timestamp,
                seed,
                failure_sensor_ids,
            )
            for sensor in sensor_list
        }

        for sensor in sensor_list:
            sensor_id = sensor["id"]
            try:
                results[sensor_id] = futures[sensor_id].result()
            except Exception as exc:
                results[sensor_id] = {
                    "measurement": None,
                    "error": str(exc),
                    "activity": {
                        "sensor_id": sensor_id,
                        "thread_id": None,
                        "thread_name": None,
                        "started_at": None,
                        "completed_at": format_iso(utc_now()),
                        "duration": None,
                        "status": "failed",
                    },
                }

    measurements = []
    failures = []
    activities = []
    for sensor in sensor_list:
        result = results[sensor["id"]]
        activities.append(result["activity"])
        if result["measurement"] is not None:
            measurements.append(result["measurement"])
        else:
            failures.append(
                {"sensor_id": sensor["id"], "error": result["error"]}
            )

    return {
        "measurements": measurements,
        "failures": failures,
        "activities": activities,
        "successful": len(measurements),
        "failed": len(failures),
        "processed": len(sensor_list),
        "worker_count": min(max_workers, len(sensor_list)),
        "execution_time": time.perf_counter() - started,
    }


def collect_and_save(
    conn: sqlite3.Connection,
    sensors: Iterable[dict],
    response_delay: float,
    max_workers: int = 4,
    seed: Optional[int] = None,
    failure_sensor_ids: Optional[Set[int]] = None,
) -> dict:
    """Collect in worker threads, then persist the batch on the caller thread."""
    from backend.repositories import measurement_repository

    result = collect_threaded(
        sensors,
        response_delay,
        max_workers=max_workers,
        seed=seed,
        failure_sensor_ids=failure_sensor_ids,
    )
    result["persisted"] = measurement_repository.insert_many(
        conn,
        result["measurements"],
    ) if result["measurements"] else 0
    return result
