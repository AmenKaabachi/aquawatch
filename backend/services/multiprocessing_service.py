"""CPU-bound water-distribution analysis using worker processes."""

import math
from concurrent.futures import ProcessPoolExecutor
from itertools import repeat
from typing import Iterable, List

MAX_PROCESSES = 32


def _validate_iterations(iterations: int) -> None:
    if isinstance(iterations, bool) or not isinstance(iterations, int):
        raise ValueError("iterations doit être un entier positif.")
    if iterations < 1:
        raise ValueError("iterations doit être un entier positif.")


def analyze_zone(zone: dict, iterations: int) -> dict:
    """Estimate deterministic water loss for one zone over repeated samples."""
    _validate_iterations(iterations)

    try:
        zone_id = zone["id"]
        inflow = float(zone["inflow_m3_h"])
        delivered = float(zone["delivered_m3_h"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Données de zone invalides pour l'analyse.") from exc

    if (
        isinstance(zone_id, bool)
        or not isinstance(zone_id, int)
        or not math.isfinite(inflow)
        or not math.isfinite(delivered)
        or inflow < 0
        or delivered < 0
    ):
        raise ValueError("Données de zone invalides pour l'analyse.")

    estimated_loss_total = 0.0
    for sample in range(iterations):
        variation = ((sample * 37 + zone_id * 17) % 101 - 50) / 10000
        estimated_inflow = inflow * (1 + variation)
        estimated_delivery = delivered * (1 - variation)
        estimated_loss_total += max(0.0, estimated_inflow - estimated_delivery)

    water_loss = max(0.0, inflow - delivered)
    return {
        "zone_id": zone_id,
        "zone_name": zone.get("name", f"Zone {zone_id}"),
        "water_loss_m3_h": round(water_loss, 2),
        "water_loss_percent": round(water_loss / inflow * 100, 2) if inflow else 0,
        "estimated_loss_m3_h": round(estimated_loss_total / iterations, 2),
    }


def analyze_zones_sequential(
    zones: Iterable[dict],
    iterations: int = 100_000,
) -> List[dict]:
    """Analyze the same zone workloads sequentially for benchmark comparison."""
    _validate_iterations(iterations)
    return [analyze_zone(zone, iterations) for zone in zones]


def analyze_zones(
    zones: Iterable[dict],
    iterations: int = 100_000,
    max_workers: int = 4,
) -> List[dict]:
    """Analyze zones in separate processes and return results in input order."""
    if isinstance(max_workers, bool) or not isinstance(max_workers, int):
        raise ValueError("max_workers doit être un entier.")
    if not 1 <= max_workers <= MAX_PROCESSES:
        raise ValueError(
            f"max_workers doit être compris entre 1 et {MAX_PROCESSES}."
        )
    _validate_iterations(iterations)

    zone_list = list(zones)
    if not zone_list:
        return []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(analyze_zone, zone_list, repeat(iterations)))
