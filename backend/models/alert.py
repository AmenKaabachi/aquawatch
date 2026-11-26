"""Modèles de données pour les alertes et la surveillance (Sprint 2).

Fournit les dataclasses pour les alertes persistantes, l'état de surveillance,
et les résultats d'évaluation de zone.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Alert:
    """Représente une alerte de surveillance persistée."""

    zone_id: int
    alert_type: str  # 'LOW_PRESSURE', 'LOW_FLOW', 'POSSIBLE_INTERRUPTION'
    severity: str    # 'WARNING', 'CRITICAL'
    message: str
    started_at: str
    last_detected_at: str
    status: str = "ACTIVE"  # 'ACTIVE', 'RESOLVED'
    resolved_at: Optional[str] = None
    created_at: Optional[str] = None
    id: Optional[int] = None


@dataclass
class MonitoringState:
    """Représente l'état persistant de surveillance pour une zone."""

    zone_id: int
    consecutive_low_pressure_count: int
    consecutive_low_flow_count: int
    last_evaluated_at: str
    last_processed_pressure_measurement_id: Optional[int] = None
    last_processed_flow_measurement_id: Optional[int] = None


@dataclass
class RepresentativeReading:
    """Représente une valeur représentative dérivée pour une métrique de zone."""

    metric_type: str  # 'pressure' ou 'flow'
    value: Optional[float]
    timestamp: Optional[str]
    measurement_id: Optional[int]
    sensor_id: Optional[int]
    sensor_name: Optional[str]
    sensor_type: Optional[str]
    is_fallback: bool
    is_stale: bool
    is_valid: bool
    freshness: str  # 'Données récentes', 'Données anciennes', 'Données indisponibles'
