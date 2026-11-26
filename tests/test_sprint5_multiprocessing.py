"""Tests for deterministic water-loss analysis using multiprocessing."""

import pytest

from backend.services import benchmark_service, multiprocessing_service


ZONES = [
    {
        "id": zone_id,
        "name": f"Zone {zone_id}",
        "inflow_m3_h": 1000 + zone_id * 50,
        "delivered_m3_h": 920 + zone_id * 45,
    }
    for zone_id in range(1, 5)
]


def test_real_process_pool_matches_sequential_results():
    sequential = multiprocessing_service.analyze_zones_sequential(
        ZONES,
        iterations=250,
    )

    parallel = multiprocessing_service.analyze_zones(
        ZONES,
        iterations=250,
        max_workers=2,
    )

    assert parallel == sequential
    assert [result["zone_id"] for result in parallel] == [1, 2, 3, 4]
    assert [
        result["water_loss_m3_h"] for result in parallel
    ] == [85.0, 90.0, 95.0, 100.0]


@pytest.mark.parametrize("process_count", [1, 2, 4])
def test_results_are_consistent_across_process_counts(process_count):
    results = multiprocessing_service.analyze_zones(
        ZONES,
        iterations=25,
        max_workers=process_count,
    )

    assert results == multiprocessing_service.analyze_zones_sequential(
        ZONES,
        iterations=25,
    )


@pytest.mark.parametrize("process_count", [0, -1, 33, 1.5, True])
def test_invalid_process_counts_are_rejected(process_count):
    with pytest.raises(ValueError, match="max_workers"):
        multiprocessing_service.analyze_zones(
            ZONES,
            iterations=1,
            max_workers=process_count,
        )


@pytest.mark.parametrize("iterations", [0, -1, 1.5, True])
def test_invalid_iteration_counts_are_rejected(iterations):
    with pytest.raises(ValueError, match="iterations"):
        multiprocessing_service.analyze_zones(
            ZONES,
            iterations=iterations,
            max_workers=1,
        )


def test_worker_exception_is_reported_and_pool_is_closed():
    invalid_zone = {"id": 1, "inflow_m3_h": 1000}

    with pytest.raises(ValueError, match="Données de zone invalides"):
        multiprocessing_service.analyze_zones(
            [invalid_zone],
            iterations=10,
            max_workers=1,
        )


def test_process_pool_is_cleaned_up(monkeypatch):
    original_executor = multiprocessing_service.ProcessPoolExecutor
    state = {"closed": False}

    class RecordingExecutor:
        def __init__(self, *args, **kwargs):
            self.executor = original_executor(*args, **kwargs)

        def __enter__(self):
            self.executor.__enter__()
            return self

        def map(self, *args, **kwargs):
            return self.executor.map(*args, **kwargs)

        def __exit__(self, *args):
            state["closed"] = True
            return self.executor.__exit__(*args)

    monkeypatch.setattr(
        multiprocessing_service,
        "ProcessPoolExecutor",
        RecordingExecutor,
    )

    multiprocessing_service.analyze_zones(
        ZONES[:2],
        iterations=10,
        max_workers=2,
    )

    assert state["closed"]


def test_multiprocessing_benchmark_uses_matching_work_and_metrics():
    benchmark = benchmark_service.benchmark_multiprocessing(
        ZONES,
        iterations=250,
        process_counts=[1, 2],
    )

    assert benchmark["zone_count"] == len(ZONES)
    assert benchmark["sequential_results"] == (
        multiprocessing_service.analyze_zones_sequential(ZONES, 250)
    )
    assert [row["process_count"] for row in benchmark["comparisons"]] == [1, 2]
    for comparison in benchmark["comparisons"]:
        assert comparison["results"] == benchmark["sequential_results"]
        assert comparison["execution_time"] >= 0
        assert comparison["speedup"] == pytest.approx(
            benchmark["sequential_time"] / comparison["execution_time"]
        )
