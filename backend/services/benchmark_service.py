"""Benchmark sequential, asyncio, and threaded sensor collection."""

import asyncio
import math
import statistics
import time
from typing import Iterable, List, Optional, Set

from backend.services.async_sensor_service import collect_async, collect_sequential
from backend.services.threaded_sensor_service import MAX_WORKERS, collect_threaded
from backend.utils.time_utils import utc_now


def _validate_benchmark(response_delay: float, repetitions: int) -> None:
    if (
        isinstance(response_delay, bool)
        or not isinstance(response_delay, (int, float))
        or not math.isfinite(response_delay)
        or response_delay < 0
    ):
        raise ValueError("response_delay doit être un nombre fini positif ou nul.")
    if isinstance(repetitions, bool) or not isinstance(repetitions, int):
        raise ValueError("repetitions doit être un entier positif.")
    if repetitions < 1:
        raise ValueError("repetitions doit être un entier positif.")


def _comparison_metrics(sequential_time: float, parallel_time: float) -> dict:
    if sequential_time <= 0 or parallel_time < 0:
        return {
            "speedup": None,
            "time_saved": sequential_time - parallel_time,
            "improvement_percent": None,
        }
    return {
        "speedup": sequential_time / parallel_time if parallel_time > 0 else None,
        "time_saved": sequential_time - parallel_time,
        "improvement_percent": (
            (sequential_time - parallel_time) / sequential_time * 100
        ),
    }


async def benchmark_once(
    sensors: Iterable[dict],
    response_delay: float,
    seed: Optional[int] = None,
    max_workers: int = 4,
    failure_sensor_ids: Optional[Set[int]] = None,
) -> dict:
    """Run all three strategies over the same sensors and simulation inputs."""
    sensor_list = list(sensors)
    if not sensor_list:
        raise ValueError("Le benchmark nécessite au moins un capteur.")
    timestamp = utc_now()

    start = time.perf_counter()
    sequential_result = await collect_sequential(
        sensor_list,
        response_delay,
        timestamp=timestamp,
        seed=seed,
        failure_sensor_ids=failure_sensor_ids,
    )
    sequential_time = time.perf_counter() - start

    start = time.perf_counter()
    async_result = await collect_async(
        sensor_list,
        response_delay,
        timestamp=timestamp,
        seed=seed,
        failure_sensor_ids=failure_sensor_ids,
    )
    async_time = time.perf_counter() - start

    start = time.perf_counter()
    threaded_result = collect_threaded(
        sensor_list,
        response_delay,
        max_workers=max_workers,
        timestamp=timestamp,
        seed=seed,
        failure_sensor_ids=failure_sensor_ids,
    )
    threaded_time = time.perf_counter() - start

    async_metrics = _comparison_metrics(sequential_time, async_time)
    threaded_metrics = _comparison_metrics(sequential_time, threaded_time)
    return {
        "sensor_count": len(sensor_list),
        "processed": len(sensor_list),
        "response_delay": response_delay,
        "worker_count": threaded_result["worker_count"],
        "sequential_time": sequential_time,
        "async_time": async_time,
        "threaded_time": threaded_time,
        "async_speedup": async_metrics["speedup"],
        "speedup": async_metrics["speedup"],
        "threaded_speedup": threaded_metrics["speedup"],
        "async_time_saved": async_metrics["time_saved"],
        "threaded_time_saved": threaded_metrics["time_saved"],
        "async_improvement_percent": async_metrics["improvement_percent"],
        "threaded_improvement_percent": threaded_metrics[
            "improvement_percent"
        ],
        "sequential_successful": sequential_result["successful"],
        "sequential_failed": sequential_result["failed"],
        "async_successful": async_result["successful"],
        "async_failed": async_result["failed"],
        "threaded_successful": threaded_result["successful"],
        "threaded_failed": threaded_result["failed"],
        "successful_measurements": async_result["successful"],
        "failed_sensors": async_result["failed"],
    }


async def benchmark_workloads(
    workloads: List[dict],
    response_delay: float,
    repetitions: int = 3,
    seed: Optional[int] = None,
    worker_counts: Optional[List[int]] = None,
    failure_sensor_ids: Optional[Set[int]] = None,
) -> List[dict]:
    """Benchmark each workload, optionally comparing multiple pool sizes."""
    _validate_benchmark(response_delay, repetitions)
    if not workloads:
        raise ValueError("Au moins une charge de capteurs est requise.")
    selected_worker_counts = worker_counts if worker_counts is not None else [4]
    if not selected_worker_counts:
        raise ValueError("Au moins une configuration de workers est requise.")
    for worker_count in selected_worker_counts:
        if (
            isinstance(worker_count, bool)
            or not isinstance(worker_count, int)
            or not 1 <= worker_count <= MAX_WORKERS
        ):
            raise ValueError(
                f"Chaque configuration de workers doit être entre 1 et {MAX_WORKERS}."
            )

    results: List[dict] = []
    for workload in workloads:
        sensors = list(workload["sensors"])
        for max_workers in selected_worker_counts:
            runs = [
                await benchmark_once(
                    sensors,
                    response_delay,
                    seed=seed,
                    max_workers=max_workers,
                    failure_sensor_ids=failure_sensor_ids,
                )
                for _ in range(repetitions)
            ]
            sequential_time = statistics.mean(
                run["sequential_time"] for run in runs
            )
            async_time = statistics.mean(run["async_time"] for run in runs)
            threaded_time = statistics.mean(
                run["threaded_time"] for run in runs
            )
            async_metrics = _comparison_metrics(sequential_time, async_time)
            threaded_metrics = _comparison_metrics(
                sequential_time,
                threaded_time,
            )
            last_run = runs[-1]
            results.append(
                {
                    "sensor_count": len(sensors),
                    "processed": len(sensors),
                    "response_delay": response_delay,
                    "repetitions": repetitions,
                    "worker_count": last_run["worker_count"],
                    "sequential_time": sequential_time,
                    "async_time": async_time,
                    "threaded_time": threaded_time,
                    "async_speedup": async_metrics["speedup"],
                    "speedup": async_metrics["speedup"],
                    "threaded_speedup": threaded_metrics["speedup"],
                    "async_time_saved": async_metrics["time_saved"],
                    "threaded_time_saved": threaded_metrics["time_saved"],
                    "async_improvement_percent": async_metrics[
                        "improvement_percent"
                    ],
                    "threaded_improvement_percent": threaded_metrics[
                        "improvement_percent"
                    ],
                    "sequential_successful": last_run[
                        "sequential_successful"
                    ],
                    "sequential_failed": last_run["sequential_failed"],
                    "async_successful": last_run["async_successful"],
                    "async_failed": last_run["async_failed"],
                    "threaded_successful": last_run["threaded_successful"],
                    "threaded_failed": last_run["threaded_failed"],
                    "successful_measurements": last_run[
                        "successful_measurements"
                    ],
                    "failed_sensors": last_run["failed_sensors"],
                }
            )
    return results


def run_benchmark(
    workloads: List[dict],
    response_delay: float,
    repetitions: int = 3,
    seed: Optional[int] = None,
    worker_counts: Optional[List[int]] = None,
    failure_sensor_ids: Optional[Set[int]] = None,
) -> List[dict]:
    """Synchronous entry point used by the dashboard and demo commands."""
    return asyncio.run(
        benchmark_workloads(
            workloads,
            response_delay,
            repetitions,
            seed,
            worker_counts,
            failure_sensor_ids,
        )
    )
