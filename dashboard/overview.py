"""Page Vue d'ensemble du tableau de bord AquaWatch (Sprint 2).

Affiche les indicateurs clés du système de surveillance :
nombre de gouvernorats, zones, capteurs et mesures,
ainsi que les cartes de synthèse d'état et le tableau récapitulatif par zone.
"""

import sqlite3

import streamlit as st

from backend.config import (
    STATUS_INACTIVE,
    STATUS_INSUFFICIENT_DATA,
    STATUS_LOW_FLOW,
    STATUS_LOW_PRESSURE,
    STATUS_NORMAL,
    STATUS_POSSIBLE_INTERRUPTION,
    STATUS_STALE_DATA,
)
from backend.repositories import (
    alert_repository,
    governorate_repository,
    measurement_repository,
    sensor_repository,
    zone_repository,
)
from backend.services import monitoring_service

_STATUS_ICONS = {
    STATUS_NORMAL: "🟢",
    STATUS_LOW_PRESSURE: "🟠",
    STATUS_LOW_FLOW: "🟠",
    STATUS_POSSIBLE_INTERRUPTION: "🔴",
    STATUS_INSUFFICIENT_DATA: "🟡",
    STATUS_STALE_DATA: "⏱️",
    STATUS_INACTIVE: "⚪",
}


def render(conn: sqlite3.Connection) -> None:
    """Affiche la page Vue d'ensemble."""

    st.title("💧 AquaWatch Grand Tunis")
    st.markdown(
        """
        **Système de surveillance de l'approvisionnement en eau — Grand Tunis**

        Surveillance du réseau de distribution d'eau potable à travers les quatre gouvernorats du Grand Tunis.
        """
    )

    st.warning(
        "⚠️ **Données simulées** — Les mesures de pression et de débit "
        "affichées sont générées par un simulateur Python. Elles ne "
        "proviennent pas de capteurs réels du réseau SONEDE."
    )

    st.caption(
        "La surveillance est déclenchée automatiquement après l'enregistrement "
        "de chaque nouvelle mesure."
    )

    # ── Indicateurs clés infrastructure ────────────────────────
    st.subheader("📊 Infrastructure surveillée")

    gov_count = governorate_repository.count(conn)
    zone_count = zone_repository.count(conn)
    active_sensors = sensor_repository.count_active(conn)
    total_measurements = measurement_repository.count_all(conn)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gouvernorats", gov_count)
    col2.metric("Zones de surveillance", zone_count)
    col3.metric("Capteurs actifs", active_sensors)
    col4.metric("Mesures stockées", f"{total_measurements:,}")

    # ── Statut de surveillance globale (Section 9.1) ───────────
    st.subheader("🔍 Synthèse de l'approvisionnement")

    zone_statuses = monitoring_service.get_all_zone_statuses(
        conn,
        process_new=False,
    )

    if not zone_statuses:
        st.info("Aucune zone de surveillance configurée.")
        return

    summary = monitoring_service.get_monitoring_summary(conn, zone_statuses)

    col_s1, col_s2, col_s3, col_s4, col_s5, col_s6 = st.columns(6)
    col_s1.metric("Total zones", summary["total_zones"])
    col_s2.metric("🟢 Normales", summary["normal_zones"])
    col_s3.metric("🟡 Données insuff.", summary["insufficient_data_zones"])
    col_s4.metric("🟠 Avertissements", summary["warning_zones"])
    col_s5.metric("🔴 Interruptions", summary["interruption_zones"])
    col_s6.metric("🚨 Alertes actives", summary["total_active_alerts"])

    # ── Tableau récapitulatif par zone (Section 9.1) ───────────
    st.subheader("📋 État détaillé par zone de surveillance")

    for zone_info in zone_statuses:
        status = zone_info["status"]
        icon = _STATUS_ICONS.get(status, "⚪")

        p_str = (
            f"{zone_info['latest_pressure']:.2f} bar"
            if zone_info.get("latest_pressure") is not None
            else "—"
        )
        f_str = (
            f"{zone_info['latest_flow']:.1f} m³/h"
            if zone_info.get("latest_flow") is not None
            else "—"
        )
        fallback_flag = ""
        if zone_info.get("pressure_is_fallback") or zone_info.get("flow_is_fallback"):
            fallback_flag = " 🔀 Repli"

        cols = st.columns([2, 1.5, 1.2, 1.2, 1.2, 1.5])
        cols[0].write(f"**{zone_info['zone_code']}** — {zone_info['zone_name']}")
        cols[1].write(f"🏛️ {zone_info['governorate_name']}")
        cols[2].write(f"**P :** {p_str}")
        cols[3].write(f"**Q :** {f_str}")
        cols[4].write(f"📊 {zone_info['measurement_count']} mes.{fallback_flag}")
        cols[5].write(f"{icon} **{status}**")
