"""Tests for event-driven monitoring after measurement persistence."""

from datetime import datetime, timedelta, timezone

import pytest

from backend.repositories import (
    alert_repository,
    measurement_repository,
    monitoring_repository,
    sensor_repository,
)
from backend.services import monitoring_service, simulation_service
from backend.utils.time_utils import format_iso


FIXED_NOW = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)


def _insert_one(test_db, sensor_id, timestamp, pressure, flow):
    return measurement_repository.insert_one(
        test_db,
        {
            "sensor_id": sensor_id,
            "timestamp": format_iso(timestamp),
            "pressure_bar": pressure,
            "flow_m3_h": flow,
            "quality_status": "valid",
            "data_origin": "SIMULATED",
        },
    )


def test_new_measurement_is_saved_and_monitored_without_dashboard(test_db):
    pressure_sensor = sensor_repository.get_by_zone(test_db, 1)[0]

    measurement_id = _insert_one(
        test_db,
        pressure_sensor["id"],
        FIXED_NOW,
        1.2,
        None,
    )

    saved = measurement_repository.get_latest_by_sensor(
        test_db, pressure_sensor["id"]
    )
    state = monitoring_repository.get_state(test_db, 1)
    assert saved["id"] == measurement_id
    assert state is not None
    assert state["consecutive_low_pressure_count"] == 1


def test_reprocessing_same_measurement_is_idempotent(test_db):
    pressure_sensor = next(
        s for s in sensor_repository.get_by_zone(test_db, 1)
        if s["sensor_type"] == "pressure"
    )
    measurement_id = _insert_one(
        test_db, pressure_sensor["id"], FIXED_NOW, 1.2, None
    )

    monitoring_service.process_measurement(
        test_db,
        measurement_id,
        reference_time=FIXED_NOW,
    )
    state = monitoring_repository.get_state(test_db, 1)
    assert state["consecutive_low_pressure_count"] == 1


def test_three_abnormal_pressure_readings_create_warning(test_db):
    _seed_normal_history(test_db, FIXED_NOW - timedelta(hours=1))
    simulation_service.generate_abnormal_measurements(
        test_db,
        zone_id=1,
        condition="low_pressure",
        count=3,
        base_time=FIXED_NOW,
        save=True,
    )

    state = monitoring_repository.get_state(test_db, 1)
    active = alert_repository.get_active_by_zone(test_db, 1)
    assert state["consecutive_low_pressure_count"] >= 3
    assert any(alert["alert_type"] == "LOW_PRESSURE" for alert in active)


def test_three_abnormal_flow_readings_create_warning(test_db):
    _seed_normal_history(test_db, FIXED_NOW - timedelta(hours=1))
    simulation_service.generate_abnormal_measurements(
        test_db,
        zone_id=1,
        condition="low_flow",
        count=3,
        base_time=FIXED_NOW,
        save=True,
    )

    state = monitoring_repository.get_state(test_db, 1)
    active = alert_repository.get_active_by_zone(test_db, 1)
    assert state["consecutive_low_flow_count"] >= 3
    assert any(alert["alert_type"] == "LOW_FLOW" for alert in active)


def test_possible_interruption_is_created_automatically(test_db):
    _seed_normal_history(test_db, FIXED_NOW - timedelta(hours=1))
    simulation_service.generate_abnormal_measurements(
        test_db,
        zone_id=1,
        condition="interruption",
        count=3,
        base_time=FIXED_NOW,
        save=True,
    )

    state = monitoring_repository.get_state(test_db, 1)
    active = alert_repository.get_active_by_zone(test_db, 1)
    assert state["consecutive_low_pressure_count"] >= 3
    assert state["consecutive_low_flow_count"] >= 3
    assert any(
        alert["alert_type"] == "POSSIBLE_INTERRUPTION"
        for alert in active
    )


def test_normal_reading_resets_counters_and_resolves_alert(test_db):
    simulation_service.generate_abnormal_measurements(
        test_db,
        zone_id=1,
        condition="interruption",
        count=3,
        base_time=FIXED_NOW - timedelta(minutes=30),
        save=True,
    )
    assert alert_repository.count_active(test_db) == 1

    simulation_service.generate_abnormal_measurements(
        test_db,
        zone_id=1,
        condition="normal",
        count=1,
        base_time=FIXED_NOW,
        save=True,
    )

    state = monitoring_repository.get_state(test_db, 1)
    assert state["consecutive_low_pressure_count"] == 0
    assert state["consecutive_low_flow_count"] == 0
    assert alert_repository.count_active(test_db) == 0


def test_failed_persistence_does_not_trigger_monitoring(test_db):
    before = measurement_repository.count_all(test_db)
    before_state = monitoring_repository.get_state(test_db, 1)

    with pytest.raises(Exception):
        measurement_repository.insert_one(
            test_db,
            {
                "sensor_id": 999,
                "timestamp": format_iso(FIXED_NOW),
                "pressure_bar": 1.2,
                "flow_m3_h": None,
                "quality_status": "valid",
                "data_origin": "SIMULATED",
            },
        )

    assert measurement_repository.count_all(test_db) == before
    assert monitoring_repository.get_state(test_db, 1) == before_state


def test_application_initialization_does_not_process_existing_measurements(test_db):
    assert measurement_repository.count_all(test_db) == 0
    assert monitoring_repository.get_state(test_db, 1) is None


def _seed_normal_history(test_db, base_time):
    sensors = sensor_repository.get_by_zone(test_db, 1)
    rows = []
    for index in range(3):
        timestamp = base_time + timedelta(minutes=10 * index)
        for sensor in sensors:
            rows.append(
                {
                    "sensor_id": sensor["id"],
                    "timestamp": format_iso(timestamp),
                    "pressure_bar": (
                        3.5 if sensor["sensor_type"] in ("pressure", "combined")
                        else None
                    ),
                    "flow_m3_h": (
                        180.0 if sensor["sensor_type"] in ("flow", "combined")
                        else None
                    ),
                    "quality_status": "valid",
                    "data_origin": "SIMULATED",
                }
            )
    measurement_repository.insert_many(test_db, rows)
