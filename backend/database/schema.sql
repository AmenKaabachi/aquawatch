-- ============================================================
-- AquaWatch Grand Tunis — Schéma de la base de données
-- Sprint 1
-- ============================================================

PRAGMA foreign_keys = ON;

-- Table des gouvernorats du Grand Tunis
CREATE TABLE IF NOT EXISTS governorates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    population  INTEGER,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Table des zones de surveillance hypothétiques
CREATE TABLE IF NOT EXISTS monitoring_zones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT    NOT NULL UNIQUE,
    governorate_id  INTEGER NOT NULL,
    name            TEXT    NOT NULL,
    description     TEXT    DEFAULT '',
    is_active       INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    FOREIGN KEY (governorate_id) REFERENCES governorates (id)
);

-- Table des capteurs virtuels
CREATE TABLE IF NOT EXISTS sensors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id     INTEGER NOT NULL,
    name        TEXT    NOT NULL UNIQUE,
    sensor_type TEXT    NOT NULL CHECK (sensor_type IN ('pressure', 'flow', 'combined')),
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    FOREIGN KEY (zone_id) REFERENCES monitoring_zones (id)
);

-- Table des mesures (simulées)
CREATE TABLE IF NOT EXISTS measurements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id       INTEGER NOT NULL,
    timestamp       TEXT    NOT NULL,
    pressure_bar    REAL,
    flow_m3_h       REAL,
    quality_status  TEXT    NOT NULL DEFAULT 'valid'
                           CHECK (quality_status IN ('valid', 'suspect', 'invalid')),
    data_origin     TEXT    NOT NULL DEFAULT 'SIMULATED'
                           CHECK (data_origin IN ('SIMULATED', 'REAL')),
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    FOREIGN KEY (sensor_id) REFERENCES sensors (id)
);

-- A measurement must contain exactly the metrics supported by its sensor.
CREATE TRIGGER IF NOT EXISTS trg_measurements_sensor_type_insert
BEFORE INSERT ON measurements
WHEN
    (SELECT sensor_type FROM sensors WHERE id = NEW.sensor_id) = 'pressure'
        AND (NEW.pressure_bar IS NULL OR NEW.flow_m3_h IS NOT NULL)
    OR (SELECT sensor_type FROM sensors WHERE id = NEW.sensor_id) = 'flow'
        AND (NEW.pressure_bar IS NOT NULL OR NEW.flow_m3_h IS NULL)
    OR (SELECT sensor_type FROM sensors WHERE id = NEW.sensor_id) = 'combined'
        AND (NEW.pressure_bar IS NULL OR NEW.flow_m3_h IS NULL)
BEGIN
    SELECT RAISE(ABORT, 'measurement values do not match sensor type');
END;

CREATE TRIGGER IF NOT EXISTS trg_measurements_sensor_type_update
BEFORE UPDATE OF sensor_id, pressure_bar, flow_m3_h ON measurements
WHEN
    (SELECT sensor_type FROM sensors WHERE id = NEW.sensor_id) = 'pressure'
        AND (NEW.pressure_bar IS NULL OR NEW.flow_m3_h IS NOT NULL)
    OR (SELECT sensor_type FROM sensors WHERE id = NEW.sensor_id) = 'flow'
        AND (NEW.pressure_bar IS NOT NULL OR NEW.flow_m3_h IS NULL)
    OR (SELECT sensor_type FROM sensors WHERE id = NEW.sensor_id) = 'combined'
        AND (NEW.pressure_bar IS NULL OR NEW.flow_m3_h IS NULL)
BEGIN
    SELECT RAISE(ABORT, 'measurement values do not match sensor type');
END;

CREATE TRIGGER IF NOT EXISTS trg_sensors_type_update
BEFORE UPDATE OF sensor_type ON sensors
WHEN EXISTS (
    SELECT 1
    FROM measurements m
    WHERE m.sensor_id = OLD.id
      AND (
          (NEW.sensor_type = 'pressure'
              AND (m.pressure_bar IS NULL OR m.flow_m3_h IS NOT NULL))
          OR (NEW.sensor_type = 'flow'
              AND (m.pressure_bar IS NOT NULL OR m.flow_m3_h IS NULL))
          OR (NEW.sensor_type = 'combined'
              AND (m.pressure_bar IS NULL OR m.flow_m3_h IS NULL))
      )
)
BEGIN
    SELECT RAISE(ABORT, 'sensor type conflicts with existing measurements');
END;

-- ── Index pour les requêtes fréquentes ──────────────────────────
CREATE INDEX IF NOT EXISTS idx_measurements_sensor_id
    ON measurements (sensor_id);

CREATE INDEX IF NOT EXISTS idx_measurements_timestamp
    ON measurements (timestamp);

CREATE INDEX IF NOT EXISTS idx_measurements_sensor_timestamp
    ON measurements (sensor_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_sensors_zone_id
    ON sensors (zone_id);

CREATE INDEX IF NOT EXISTS idx_zones_governorate_id
    ON monitoring_zones (governorate_id);

-- ============================================================
-- Sprint 2 : Alertes et état de surveillance
-- ============================================================

-- Table des alertes de surveillance
CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id         INTEGER NOT NULL,
    alert_type      TEXT    NOT NULL CHECK (alert_type IN ('LOW_PRESSURE', 'LOW_FLOW', 'POSSIBLE_INTERRUPTION')),
    severity        TEXT    NOT NULL CHECK (severity IN ('WARNING', 'CRITICAL')),
    status          TEXT    NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'RESOLVED')),
    message         TEXT    NOT NULL,
    started_at      TEXT    NOT NULL,
    last_detected_at TEXT   NOT NULL,
    resolved_at     TEXT,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    FOREIGN KEY (zone_id) REFERENCES monitoring_zones (id)
);

-- Table de suivi de l'état de surveillance par zone (validation des lectures consécutives)
CREATE TABLE IF NOT EXISTS monitoring_states (
    zone_id                                 INTEGER PRIMARY KEY,
    last_processed_pressure_measurement_id  INTEGER,
    last_processed_flow_measurement_id      INTEGER,
    consecutive_low_pressure_count          INTEGER NOT NULL DEFAULT 0,
    consecutive_low_flow_count              INTEGER NOT NULL DEFAULT 0,
    last_evaluated_at                       TEXT NOT NULL,
    FOREIGN KEY (zone_id) REFERENCES monitoring_zones (id)
);

CREATE INDEX IF NOT EXISTS idx_alerts_zone_id
    ON alerts (zone_id);

CREATE INDEX IF NOT EXISTS idx_alerts_status
    ON alerts (status);

CREATE INDEX IF NOT EXISTS idx_alerts_alert_type
    ON alerts (alert_type);

CREATE INDEX IF NOT EXISTS idx_alerts_started_at
    ON alerts (started_at);

