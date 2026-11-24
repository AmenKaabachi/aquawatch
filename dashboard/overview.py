"""Page Vue d'ensemble du tableau de bord AquaWatch.

Affiche les indicateurs clés du système de surveillance :
nombre de gouvernorats, zones, capteurs et mesures,
ainsi que le statut de chaque zone.
"""

import sqlite3

import streamlit as st

from backend.config import STATUS_INACTIVE, STATUS_INSUFFICIENT_DATA, STATUS_NORMAL
from backend.repositories import (
    governorate_repository,
    measurement_repository,
    sensor_repository,
    zone_repository,
)
from backend.services import monitoring_service


def render(conn: sqlite3.Connection) -> None:
    """Affiche la page Vue d'ensemble."""

    st.title("💧 AquaWatch Grand Tunis")
    st.markdown(
        """
        **Système de surveillance de l'approvisionnement en eau — Grand Tunis**

        Application de démonstration académique simulant la surveillance
        des réseaux d'eau potable à travers les quatre gouvernorats du Grand Tunis.
        """
    )

    st.warning(
        "⚠️ **Données simulées** — Les mesures de pression et de débit "
        "affichées sont générées par un simulateur Python. Elles ne "
        "proviennent pas de capteurs réels du réseau SONEDE."
    )

    # ── Indicateurs clés ─────────────────────────────────────
    st.subheader("📊 Indicateurs clés")

    gov_count = governorate_repository.count(conn)
    zone_count = zone_repository.count(conn)
    active_sensors = sensor_repository.count_active(conn)
    total_measurements = measurement_repository.count_all(conn)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gouvernorats", gov_count)
    col2.metric("Zones de surveillance", zone_count)
    col3.metric("Capteurs actifs", active_sensors)
    col4.metric("Mesures stockées", f"{total_measurements:,}")

    # ── Statut de surveillance ───────────────────────────────
    st.subheader("🔍 Statut de surveillance")

    zone_statuses = monitoring_service.get_all_zone_statuses(conn)

    if not zone_statuses:
        st.info("Aucune zone de surveillance configurée.")
        return

    normal_count = sum(1 for z in zone_statuses if z["status"] == STATUS_NORMAL)
    insufficient_count = sum(
        1 for z in zone_statuses if z["status"] == STATUS_INSUFFICIENT_DATA
    )
    inactive_count = sum(1 for z in zone_statuses if z["status"] == STATUS_INACTIVE)

    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Normal", normal_count)
    col2.metric("🟡 Données insuffisantes", insufficient_count)
    col3.metric("🔴 Inactive", inactive_count)

    # ── Tableau récapitulatif ────────────────────────────────
    st.subheader("📋 Résumé par zone")

    _STATUS_ICONS = {
        STATUS_NORMAL: "🟢",
        STATUS_INSUFFICIENT_DATA: "🟡",
        STATUS_INACTIVE: "🔴",
    }

    for zone_info in zone_statuses:
        status = zone_info["status"]
        icon = _STATUS_ICONS.get(status, "⚪")

        cols = st.columns([2, 2, 1, 1, 1])
        cols[0].write(f"**{zone_info['zone_code']}** — {zone_info['zone_name']}")
        cols[1].write(zone_info["governorate_name"])
        cols[2].write(f"📡 {zone_info['active_sensor_count']}")
        cols[3].write(f"📊 {zone_info['measurement_count']}")
        cols[4].write(f"{icon} {status}")
