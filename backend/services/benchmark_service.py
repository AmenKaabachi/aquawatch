"""Benchmark séquentiel/asynchrone pour la collecte virtuelle des capteurs."""

import asyncio
import statistics
import time
from typing import Iterable, List, Optional

from backend.services.async_sensor_service import collect_async, collect_sequential


async def benchmark_once(
    sensors: Iterable[dict],
    response_delay: float,
    seed: Optional[int] = None,
) -> dict:
    """Exécute une répétition des deux modes sur le même nombre de capteurs."""
    sensor_list = list(sensors)

    sequential_start = time.perf_counter()
    sequential_result = await collect_sequential(
        sensor_list,
        response_delay,
        seed=seed,
    )
    sequential_time = time.perf_counter() - sequential_start

    async_start = time.perf_counter()
    async_result = await collect_async(
        sensor_list,
        response_delay,
        seed=seed,
    )
    async_time = time.perf_counter() - async_start

    return {
        "sensor_count": len(sensor_list),
        "response_delay": response_delay,
        "sequential_time": sequential_time,
        "async_time": async_time,
        "speedup": (
            sequential_time / async_time
            if async_time > 0
            else float("inf")
        ),
        "successful_measurements": async_result["successful"],
        "failed_sensors": async_result["failed"],
    }


async def benchmark_workloads(
    workloads: List[dict],
    response_delay: float,
    repetitions: int = 3,
    seed: Optional[int] = None,
) -> List[dict]:
    """Compare plusieurs charges; chaque répétition utilise le même workload."""
    results: List[dict] = []
    for workload in workloads:
        sensors = list(workload["sensors"])
        runs = [
            await benchmark_once(sensors, response_delay, seed=seed)
            for _ in range(repetitions)
        ]
        sequential_median = statistics.median(
            run["sequential_time"] for run in runs
        )
        async_median = statistics.median(run["async_time"] for run in runs)
        results.append(
            {
                "sensor_count": len(sensors),
                "response_delay": response_delay,
                "repetitions": repetitions,
                "sequential_time": sequential_median,
                "async_time": async_median,
                "speedup": sequential_median / async_median,
                "successful_measurements": runs[-1]["successful_measurements"],
                "failed_sensors": runs[-1]["failed_sensors"],
            }
        )
    return results


def run_benchmark(
    workloads: List[dict],
    response_delay: float,
    repetitions: int = 3,
    seed: Optional[int] = None,
) -> List[dict]:
    """Point d'entrée synchrone pour Streamlit."""
    return asyncio.run(
        benchmark_workloads(
            workloads,
            response_delay,
            repetitions,
            seed,
        )
    )
