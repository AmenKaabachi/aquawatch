"""Configuration de l'application AquaWatch Grand Tunis.

Centralise les chemins, constantes et paramètres de l'application.
"""

from pathlib import Path

# ── Chemins du projet ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DATABASE_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATABASE_DIR / "aquawatch.db"
SQL_DIR = Path(__file__).parent / "database"
SCHEMA_PATH = SQL_DIR / "schema.sql"
SEED_PATH = SQL_DIR / "seed.sql"

# ── Paramètres de simulation ──────────────────────────────────────
SIMULATION_PRESSURE_MIN: float = 1.5   # bar
SIMULATION_PRESSURE_MAX: float = 6.0   # bar
SIMULATION_FLOW_MIN: float = 50.0      # m³/h
SIMULATION_FLOW_MAX: float = 500.0     # m³/h
SIMULATION_DEFAULT_SEED: int = 42
MEASUREMENTS_PER_SENSOR: int = 24      # mesures par capteur par lot

# ── Statuts de surveillance (Sprint 1 & Sprint 2) ────────────────
STATUS_NORMAL = "Normal"
STATUS_LOW_PRESSURE = "Pression faible"
STATUS_LOW_FLOW = "Débit faible"
STATUS_POSSIBLE_INTERRUPTION = "Interruption possible"
STATUS_INSUFFICIENT_DATA = "Données insuffisantes"
STATUS_STALE_DATA = "Données anciennes"
STATUS_INACTIVE = "Inactive"

# ── Fraîcheur des données ────────────────────────────────────────
FRESHNESS_RECENT = "Données récentes"
FRESHNESS_STALE = "Données anciennes"
FRESHNESS_UNAVAILABLE = "Données indisponibles"

# ── Seuils de détection de surveillance (Sprint 2) ───────────────
LOW_PRESSURE_THRESHOLD_BAR: float = 1.5      # Condition A : pression <= 1.5 bar
LOW_FLOW_THRESHOLD_M3_H: float = 50.0        # Condition B : débit <= 50.0 m³/h
CONSECUTIVE_ABNORMAL_READINGS: int = 3       # Lectures consécutives pour déclencher une alerte
MAX_MEASUREMENT_AGE_HOURS: int = 24          # Seuil d'obsolescence (en heures)

# ── Alertes (Sprint 2) ───────────────────────────────────────────
ALERT_TYPE_LOW_PRESSURE = "LOW_PRESSURE"
ALERT_TYPE_LOW_FLOW = "LOW_FLOW"
ALERT_TYPE_POSSIBLE_INTERRUPTION = "POSSIBLE_INTERRUPTION"

SEVERITY_WARNING = "WARNING"
SEVERITY_CRITICAL = "CRITICAL"

ALERT_STATUS_ACTIVE = "ACTIVE"
ALERT_STATUS_RESOLVED = "RESOLVED"

# ── Origine des données ──────────────────────────────────────────
DATA_ORIGIN_SIMULATED = "SIMULATED"
