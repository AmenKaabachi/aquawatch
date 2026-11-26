"""Tests of the Sprint 3 asyncio sensor collector and benchmark."""

import asyncio
import time

from backend.repositories import (
    measurement_repository,
    monitoring_repository,
    sensor_repository,
)
from backend.services import (
    async_sensor_service,
    benchmark_service,
    monitoring_service,
)


def test_single_sensor_async_collection(test_db):
    sensor = sensor_repository.get_active(test_db)[0]
    result = asyncio.run(
        async_sensor_service.collect_async([sensor], 0.001, seed=42)
    )
    assert result["successful"] == 1
    assert result["failed"] == 0
    assert len(result["measurements"]) == 1


def test_multiple_sensors_async_collection(test_db):
    sensors = sensor_repository.get_active(test_db)[:8]
    result = asyncio.run(
        async_sensor_service.collect_async(sensors, 0.001, seed=42)
    )
    assert result["successful"] == 8
    assert len(result["measurements"]) == 8


def test_async_collector_preserves_sensor_types(test_db):
    sensors = sensor_repository.get_active(test_db)[:3]
    result = asyncio.run(
        async_sensor_service.collect_async(sensors, 0.001, seed=42)
    )
    by_sensor = {
        row["sensor_id"]: row
        for row in result["measurements"]
    }
    assert by_sensor[1]["pressure_bar"] is not None
    assert by_sensor[1]["flow_m3_h"] is None
    assert by_sensor[2]["pressure_bar"] is None
    assert by_sensor[2]["flow_m3_h"] is not None
    assert by_sensor[3]["pressure_bar"] is not None
    assert by_sensor[3]["flow_m3_h"] is not None


def test_sequential_collection_count(test_db):
    sensors = sensor_repository.get_active(test_db)[:6]
    result = asyncio.run(
        async_sensor_service.collect_sequential(sensors, 0.001, seed=42)
    )
    assert result["successful"] == 6
    assert result["failed"] == 0


def test_async_collection_concurrency_is_faster(test_db):
    sensors = sensor_repository.get_active(test_db)[:6]

    sequential_start = time.perf_counter()
    sequential = asyncio.run(
        async_sensor_service.collect_sequential(sensors, 0.03, seed=42)
    )
    sequential_time = time.perf_counter() - sequential_start

    async_start = time.perf_counter()
    asynchronous = asyncio.run(
        async_sensor_service.collect_async(sensors, 0.03, seed=42)
    )
    async_time = time.perf_counter() - async_start

    assert sequential["successful"] == 6
    assert asynchronous["successful"] == 6
    assert async_time < sequential_time


def test_benchmark_speedup_calculation(test_db):
    sensors = sensor_repository.get_active(test_db)[:4]
    result = asyncio.run(
        benchmark_service.benchmark_once(sensors, 0.01, seed=42)
    )
    expected = result["sequential_time"] / result["async_time"]
    assert abs(result["speedup"] - expected) < 1e-12
    assert result["sensor_count"] == 4
    assert result["successful_measurements"] == 4


def test_benchmark_multiple_workloads(test_db):
    sensors = sensor_repository.get_active(test_db)
    workloads = [
        {"sensors": sensors[:4]},
        {"sensors": sensors[:8]},
    ]
    result = benchmark_service.run_benchmark(
        workloads,
        response_delay=0.005,
        repetitions=2,
        seed=42,
    )
    assert [row["sensor_count"] for row in result] == [4, 8]
    assert all(row["speedup"] > 1 for row in result)


def test_benchmark_does_not_modify_database(test_db):
    before = measurement_repository.count_all(test_db)
    sensors = sensor_repository.get_active(test_db)[:4]
    benchmark_service.run_benchmark(
        [{"sensors": sensors}],
        response_delay=0.001,
        repetitions=1,
        seed=42,
    )
    assert measurement_repository.count_all(test_db) == before


def test_application_async_collection_persists_through_repository(test_db):
    sensors = sensor_repository.get_active(test_db)[:3]
    before = measurement_repository.count_all(test_db)
    result = async_sensor_service.collect_and_save(
        test_db,
        sensors,
        response_delay=0.001,
        seed=42,
    )
    assert result["successful"] == 3
    assert result["persisted"] == 3
    assert measurement_repository.count_all(test_db) == before + 3


def test_async_save_triggers_automatic_monitoring(test_db):
    sensors = sensor_repository.get_active(test_db)[:3]
    async_sensor_service.collect_and_save(
        test_db,
        sensors,
        response_delay=0.001,
        seed=42,
    )
    state = monitoring_repository.get_state(test_db, 1)
    assert state is not None
    assert state["last_evaluated_at"]


def test_reprocessing_async_saved_measurement_is_idempotent(test_db):
    sensors = sensor_repository.get_active(test_db)[:3]
    result = async_sensor_service.collect_and_save(
        test_db,
        sensors,
        response_delay=0.001,
        seed=42,
    )
    measurement_id = measurement_repository.get_latest_by_sensor(
        test_db,
        sensors[0]["id"],
    )["id"]
    state_before = monitoring_repository.get_state(test_db, 1)

    monitoring_service.process_measurement(
        test_db,
        measurement_id,
    )
    state_after = monitoring_repository.get_state(test_db, 1)
    assert state_after["consecutive_low_pressure_count"] == (
        state_before["consecutive_low_pressure_count"]
    )
    assert result["successful"] == 3


def test_individual_sensor_failure_is_reported(test_db):
    sensors = sensor_repository.get_active(test_db)[:4]
    result = asyncio.run(
        async_sensor_service.collect_async(
            sensors,
            0.001,
            seed=42,
            failure_sensor_ids={sensors[1]["id"]},
        )
    )
    assert result["successful"] == 3
    assert result["failed"] == 1
    assert result["failures"][0]["sensor_id"] == sensors[1]["id"]


def test_async_collection_failure_does_not_change_database(test_db):
    before = measurement_repository.count_all(test_db)
    sensors = sensor_repository.get_active(test_db)[:2]
    result = asyncio.run(
        async_sensor_service.collect_async(
            sensors,
            0.001,
            failure_sensor_ids={sensors[0]["id"]},
        )
    )
    assert result["successful"] == 1
    assert measurement_repository.count_all(test_db) == before
