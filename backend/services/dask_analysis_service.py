"""Dask Distributed execution for CPU-bound water-loss analysis."""

from typing import Iterable, List

from dask.distributed import Client, LocalCluster

from backend.services.multiprocessing_service import (
    MAX_PROCESSES,
    analyze_zone,
)


def analyze_zones_dask(
    zones: Iterable[dict],
    iterations: int = 100_000,
    n_workers: int = 4,
) -> List[dict]:
    """Analyze independent zones on a temporary local Dask cluster."""
    if isinstance(n_workers, bool) or not isinstance(n_workers, int):
        raise ValueError("n_workers doit être un entier.")
    if not 1 <= n_workers <= MAX_PROCESSES:
        raise ValueError(
            f"n_workers doit être compris entre 1 et {MAX_PROCESSES}."
        )

    zone_list = list(zones)
    if not zone_list:
        return []

    cluster = LocalCluster(
        n_workers=n_workers,
        threads_per_worker=1,
        processes=True,
        dashboard_address=None,
    )
    client = None
    try:
        client = Client(cluster)
        tasks = [
            client.submit(analyze_zone, zone, iterations, pure=False)
            for zone in zone_list
        ]
        return client.gather(tasks)
    finally:
        try:
            if client is not None:
                client.close()
        finally:
            cluster.close()
