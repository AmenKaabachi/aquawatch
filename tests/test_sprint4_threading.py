"""Tests for multithreaded sensor collection and three-mode benchmarks."""

import asyncio
import threading
from datetime import datetime, timezone

import pytest

from backend.repositories import measurement_repository, monitoring_repository
from backend.repositories import sensor_repository
from backend.services import async_sensor_service
from backend.services import benchmark_service, threaded_sensor_service


def test_threaded_collection_returns_one_measurement_per_sensor(test_db):
    sensors = sensor_repository.get_active(test_db)[:4]
    timestamp = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)

    result = threaded_sensor_service.collect_threaded(
        sensors,
        response_delay=0,
        max_workers=2,
        timestamp=timestamp,
        seed=42,
    )

    assert result["processed"] == 4
    assert result["successful"] == 4
    assert result["failed"] == 0
    assert result["worker_count"] == 2
    assert [row["sensor_id"] for row in result["measurements"]] == [
        sensor["id"] for sensor in sensors
    ]
    assert all(
        row["timestamp"] == "2026-01-02T03:04:00Z"
        for row in result["measurements"]
    )
    assert all(row["data_origin"] == "SIMULATED" for row in result["measurements"])
    assert len({row["sensor_id"] for row in result["measurements"]}) == 4
    assert len(result["activities"]) == 4


def test_all_strategies_generate_equivalent_measurements(test_db):
    sensors = sensor_repository.get_active(test_db)[:4]
    timestamp = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
    sequential = asyncio.run(
        async_sensor_service.collect_sequential(
            sensors,
            0,
            timestamp=timestamp,
            seed=42,
        )
    )
    asynchronous = asyncio.run(
        async_sensor_service.collect_async(
            sensors,
            0,
            timestamp=timestamp,
            seed=42,
        )
    )
    threaded = threaded_sensor_service.collect_threaded(
        sensors,
        0,
        max_workers=2,
        timestamp=timestamp,
        seed=42,
    )

    assert sequential["measurements"] == asynchronous["measurements"]
    assert sequential["measurements"] == threaded["measurements"]


def test_threaded_collection_handles_empty_sensor_list():
    result = threaded_sensor_service.collect_threaded([], 0.01, max_workers=3)

    assert result["processed"] == 0
    assert result["successful"] == 0
    assert result["failed"] == 0
    assert result["worker_count"] == 0
    assert result["measurements"] == []


@pytest.mark.parametrize("workers", [0, -1, 33, 1.5, True])
def test_threaded_collection_rejects_invalid_worker_counts(workers):
    with pytest.raises(ValueError):
        threaded_sensor_service.collect_threaded([], 0, max_workers=workers)


@pytest.mark.parametrize("delay", [-0.1, float("inf"), float("nan"), True])
def test_threaded_collection_rejects_invalid_delays(delay):
    with pytest.raises(ValueError):
        threaded_sensor_service.collect_threaded([], delay)


def test_threaded_collection_rejects_duplicate_sensor_ids(test_db):
    sensor = sensor_repository.get_active(test_db)[0]

    with pytest.raises(ValueError, match="identifiants en double"):
        threaded_sensor_service.collect_threaded([sensor, sensor], 0)


def test_threaded_collection_reports_individual_sensor_failure(test_db):
    sensors = sensor_repository.get_active(test_db)[:3]
    failed_id = sensors[1]["id"]

    result = threaded_sensor_service.collect_threaded(
        sensors,
        response_delay=0,
        max_workers=2,
        failure_sensor_ids={failed_id},
    )

    assert result["successful"] == 2
    assert result["failed"] == 1
    assert result["failures"] == [
        {
            "sensor_id": failed_id,
            "error": f"Échec simulé de la collecte du capteur {failed_id}",
        }
    ]
    failed_activity = next(
        activity
        for activity in result["activities"]
        if activity["sensor_id"] == failed_id
    )
    assert failed_activity["status"] == "failed"


def test_unexpected_worker_exception_is_reported(test_db, monkeypatch):
    sensors = sensor_repository.get_active(test_db)[:2]
    failed_id = sensors[0]["id"]
    original_collect = threaded_sensor_service._collect_sensor

    def raise_for_one(sensor, *args):
        if sensor["id"] == failed_id:
            raise RuntimeError("worker crashed")
        return original_collect(sensor, *args)

    monkeypatch.setattr(threaded_sensor_service, "_collect_sensor", raise_for_one)
    result = threaded_sensor_service.collect_threaded(sensors, 0, max_workers=2)

    assert result["successful"] == 1
    assert result["failed"] == 1
    assert result["failures"][0] == {
        "sensor_id": failed_id,
        "error": "worker crashed",
    }


def test_threaded_sensor_operations_overlap(test_db, monkeypatch):
    sensors = sensor_repository.get_active(test_db)[:2]
    barrier = threading.Barrier(2)

    def wait_for_other_worker(_delay):
        barrier.wait(timeout=3)

    monkeypatch.setattr(threaded_sensor_service.time, "sleep", wait_for_other_worker)
    result = threaded_sensor_service.collect_threaded(
        sensors,
        response_delay=0.01,
        max_workers=2,
    )

    assert result["successful"] == 2
    assert len(
        {activity["thread_id"] for activity in result["activities"]}
    ) == 2


def test_thread_pool_is_shut_down_after_collection(test_db):
    sensors = sensor_repository.get_active(test_db)[:3]

    threaded_sensor_service.collect_threaded(
        sensors,
        response_delay=0,
        max_workers=2,
    )

    assert not any(
        thread.name.startswith("aquawatch-sensor")
        for thread in threading.enumerate()
    )


def test_threaded_collection_persists_on_caller_thread_and_monitors(test_db):
    sensors = sensor_repository.get_active(test_db)[:3]
    before = measurement_repository.count_all(test_db)

    result = threaded_sensor_service.collect_and_save(
        test_db,
        sensors,
        response_delay=0,
        max_workers=2,
        seed=42,
    )

    assert result["successful"] == 3
    assert result["persisted"] == 3
    assert measurement_repository.count_all(test_db) == before + 3
    assert monitoring_repository.get_state(test_db, 1) is not None


def test_collect_and_save_persists_only_successful_threaded_results(test_db):
    sensors = sensor_repository.get_active(test_db)[:2]
    before = measurement_repository.count_all(test_db)

    result = threaded_sensor_service.collect_and_save(
        test_db,
        sensors,
        response_delay=0,
        failure_sensor_ids={sensors[0]["id"]},
    )

    assert result["successful"] == 1
    assert result["failed"] == 1
    assert result["persisted"] == 1
    assert measurement_repository.count_all(test_db) == before + 1


def test_benchmark_measures_all_strategies_and_calculates_metrics(test_db):
    sensors = sensor_repository.get_active(test_db)[:3]

    result = benchmark_service.run_benchmark(
        [{"sensors": sensors}],
        response_delay=0.001,
        repetitions=1,
        seed=42,
        worker_counts=[2],
    )[0]

    assert result["processed"] == 3
    assert result["worker_count"] == 2
    assert result["sequential_failed"] == 0
    assert result["async_failed"] == 0
    assert result["threaded_failed"] == 0
    assert result["sequential_time"] >= 0
    assert result["async_time"] >= 0
    assert result["threaded_time"] >= 0
    assert result["async_speedup"] == pytest.approx(
        result["sequential_time"] / result["async_time"]
    )
    assert result["async_time_saved"] == pytest.approx(
        result["sequential_time"] - result["async_time"]
    )
    assert result["async_improvement_percent"] == pytest.approx(
        result["async_time_saved"] / result["sequential_time"] * 100
    )
    assert result["threaded_speedup"] == pytest.approx(
        result["sequential_time"] / result["threaded_time"]
    )
    assert result["threaded_time_saved"] == pytest.approx(
        result["sequential_time"] - result["threaded_time"]
    )
    assert result["threaded_improvement_percent"] == pytest.approx(
        result["threaded_time_saved"] / result["sequential_time"] * 100
    )


def test_benchmark_reports_failures_in_each_strategy(test_db):
    sensors = sensor_repository.get_active(test_db)[:3]
    failed_id = sensors[1]["id"]

    result = benchmark_service.run_benchmark(
        [{"sensors": sensors}],
        response_delay=0,
        repetitions=1,
        seed=42,
        worker_counts=[1],
        failure_sensor_ids={failed_id},
    )[0]

    assert result["sequential_successful"] == 2
    assert result["async_successful"] == 2
    assert result["threaded_successful"] == 2
    assert result["sequential_failed"] == 1
    assert result["async_failed"] == 1
    assert result["threaded_failed"] == 1


@pytest.mark.parametrize(
    ("delay", "repetitions"),
    [(-1, 1), (float("inf"), 1), (0.01, 0), (0.01, True)],
)
def test_benchmark_rejects_invalid_inputs(delay, repetitions):
    with pytest.raises(ValueError):
        benchmark_service.run_benchmark(
            [{"sensors": []}],
            response_delay=delay,
            repetitions=repetitions,
        )


def test_benchmark_supports_multiple_worker_configurations(test_db):
    sensors = sensor_repository.get_active(test_db)[:3]

    results = benchmark_service.run_benchmark(
        [{"sensors": sensors}],
        response_delay=0,
        repetitions=1,
        seed=42,
        worker_counts=[1, 2],
    )

    assert [result["worker_count"] for result in results] == [1, 2]
    assert all(result["processed"] == 3 for result in results)


def test_benchmark_rejects_invalid_worker_configuration():
    with pytest.raises(ValueError):
        benchmark_service.run_benchmark(
            [{"sensors": []}],
            response_delay=0,
            worker_counts=[0],
        )


def test_benchmark_rejects_empty_sensor_set():
    with pytest.raises(ValueError, match="au moins un capteur"):
        benchmark_service.run_benchmark(
            [{"sensors": []}],
            response_delay=0,
        )


def test_benchmark_rejects_empty_workload_list():
    with pytest.raises(ValueError, match="Au moins une charge"):
        benchmark_service.run_benchmark([], response_delay=0)
