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

# ── Statuts de surveillance (Sprint 1) ────────────────────────────
STATUS_NORMAL = "Normal"
STATUS_INSUFFICIENT_DATA = "Données insuffisantes"
STATUS_INACTIVE = "Inactive"

# ── Origine des données ──────────────────────────────────────────
DATA_ORIGIN_SIMULATED = "SIMULATED"
