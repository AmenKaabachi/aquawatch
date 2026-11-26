"""Tests for local Dask execution of the water-loss analysis."""

import pytest

from backend.services import (
    benchmark_service,
    dask_analysis_service,
    multiprocessing_service,
)


ZONES = [
    {
        "id": zone_id,
        "name": f"Zone {zone_id}",
        "inflow_m3_h": 1000 + zone_id * 50,
        "delivered_m3_h": 920 + zone_id * 45,
    }
    for zone_id in range(1, 5)
]


@pytest.fixture
def tracked_dask_resources(monkeypatch):
    clusters = []
    clients = []
    submitted_tasks = []
    original_cluster = dask_analysis_service.LocalCluster
    original_client = dask_analysis_service.Client

    def create_cluster(*args, **kwargs):
        cluster = original_cluster(*args, **kwargs)
        clusters.append(cluster)
        return cluster

    class ClientTracker:
        def __init__(self, cluster):
            self.client = original_client(cluster)
            self.closed = False
            clients.append(self)

        def submit(self, function, *args, **kwargs):
            submitted_tasks.append((function, args))
            return self.client.submit(function, *args, **kwargs)

        def gather(self, futures):
            return self.client.gather(futures)

        def close(self):
            self.closed = True
            self.client.close()

    monkeypatch.setattr(dask_analysis_service, "LocalCluster", create_cluster)
    monkeypatch.setattr(dask_analysis_service, "Client", ClientTracker)
    return clusters, clients, submitted_tasks


def _assert_resources_closed(clusters, clients):
    assert clients[0].closed
    assert str(clusters[0].status).lower().endswith("closed")
    assert str(clients[0].client.status).lower().endswith("closed")


def test_dask_submits_one_task_per_zone_and_matches_sequential(
    tracked_dask_resources,
):
    clusters, clients, submitted_tasks = tracked_dask_resources

    results = dask_analysis_service.analyze_zones_dask(
        ZONES,
        iterations=50,
        n_workers=2,
    )

    assert results == multiprocessing_service.analyze_zones_sequential(
        ZONES,
        iterations=50,
    )
    assert [args[0]["id"] for _, args in submitted_tasks] == [1, 2, 3, 4]
    assert all(
        function is multiprocessing_service.analyze_zone
        for function, _ in submitted_tasks
    )
    _assert_resources_closed(clusters, clients)


@pytest.mark.parametrize("worker_count", [0, -1, 33, 1.5, True])
def test_dask_rejects_invalid_worker_counts(worker_count):
    with pytest.raises(ValueError, match="n_workers"):
        dask_analysis_service.analyze_zones_dask(
            ZONES,
            iterations=5,
            n_workers=worker_count,
        )


def test_dask_worker_error_propagates_and_resources_close(
    tracked_dask_resources,
):
    clusters, clients, _ = tracked_dask_resources
    invalid_zone = {"id": 1, "inflow_m3_h": 1000}

    with pytest.raises(ValueError, match="Données de zone invalides"):
        dask_analysis_service.analyze_zones_dask(
            [invalid_zone],
            iterations=10,
            n_workers=1,
        )

    _assert_resources_closed(clusters, clients)


def test_cpu_benchmark_compares_all_strategies_and_worker_counts():
    benchmark = benchmark_service.benchmark_cpu_analysis(
        ZONES,
        iterations=50,
        process_counts=[1],
        dask_worker_counts=[1, 2],
    )

    assert benchmark["sequential_results"] == (
        multiprocessing_service.analyze_zones_sequential(ZONES, iterations=50)
    )
    assert [row["strategy"] for row in benchmark["comparisons"]] == [
        "Multiprocessing",
        "Dask Distributed",
        "Dask Distributed",
    ]
    assert [row["worker_count"] for row in benchmark["comparisons"]] == [1, 1, 2]
    for comparison in benchmark["comparisons"]:
        assert comparison["results"] == benchmark["sequential_results"]
        assert comparison["execution_time"] >= 0
        assert comparison["speedup"] == pytest.approx(
            benchmark["sequential_time"] / comparison["execution_time"]
        )


@pytest.mark.parametrize(
    ("sequential_time", "strategy_time"),
    [
        (0, 1),
        (-1, 1),
        (float("inf"), 1),
        (1, float("nan")),
        (1, -1),
        (None, 1),
        (1, True),
    ],
)
def test_comparison_metrics_handle_invalid_times_safely(
    sequential_time,
    strategy_time,
):
    metrics = benchmark_service._comparison_metrics(
        sequential_time,
        strategy_time,
    )

    assert metrics == {
        "speedup": None,
        "time_saved": None,
        "improvement_percent": None,
    }


def test_zero_strategy_time_has_no_infinite_speedup():
    metrics = benchmark_service._comparison_metrics(2, 0)

    assert metrics["speedup"] is None
    assert metrics["time_saved"] == 2
    assert metrics["improvement_percent"] == 100
