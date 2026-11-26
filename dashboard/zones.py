"""Page Gouvernorats et Zones du tableau de bord AquaWatch (Sprint 2).

Affiche les quatre gouvernorats du Grand Tunis avec leurs
zones de surveillance et l'état détaillé de chaque zone (pression, débit,
fraîcheur, alertes, repli).
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
    sensor_repository,
    zone_repository,
)
from backend.services import monitoring_service

_SENSOR_TYPE_FR = {
    "pressure": "Pression",
    "flow": "Débit",
    "combined": "Combiné",
}

_STATUS_BADGES = {
    STATUS_NORMAL: "🟢 Normal",
    STATUS_LOW_PRESSURE: "🟠 Pression faible",
    STATUS_LOW_FLOW: "🟠 Débit faible",
    STATUS_POSSIBLE_INTERRUPTION: "🔴 Interruption possible",
    STATUS_INSUFFICIENT_DATA: "🟡 Données insuffisantes",
    STATUS_STALE_DATA: "⏱️ Données anciennes",
    STATUS_INACTIVE: "⚪ Inactive",
}


def render(conn: sqlite3.Connection) -> None:
    """Affiche la page Gouvernorats et Zones avec surveillance détaillée (Section 9.2)."""

    st.title("🗺️ Gouvernorats et Zones de surveillance")
    st.markdown(
        """
        Détail de la surveillance pour chaque zone des quatre gouvernorats du Grand Tunis.
        Affiche les dernières mesures représentatives de pression et de débit,
        le statut individuel et les alertes actives associées.
        """
    )

    governorates = governorate_repository.get_all(conn)

    if not governorates:
        st.warning("Aucun gouvernorat trouvé dans la base de données.")
        return

    for gov in governorates:
        population_str = (
            f"{gov['population']:,}" if gov.get("population") else "N/D"
        )

        st.subheader(f"🏛️ {gov['name']}")
        st.caption(
            f"Population estimée : {population_str} habitants "
            f"(source : INS 2024, valeur approximative)"
        )

        zones = zone_repository.get_by_governorate(conn, gov["id"])

        if not zones:
            st.info(f"Aucune zone de surveillance pour {gov['name']}.")
            continue

        for zone in zones:
            eval_info = monitoring_service.evaluate_zone(
                conn,
                zone["id"],
                process_new=False,
            )
            sensors = sensor_repository.get_by_zone(conn, zone["id"])
            status_badge = _STATUS_BADGES.get(
                eval_info["status"], f"⚪ {eval_info['status']}"
            )

            with st.expander(
                f"📍 {zone['code']} — {zone['name']}  |  {status_badge}",
                expanded=False,
            ):
                col_left, col_right = st.columns([1, 1])

                with col_left:
                    st.markdown("#### 📡 Métriques représentatives de la zone")
                    p_val_str = (
                        f"{eval_info['latest_pressure']:.2f} bar"
                        if eval_info["latest_pressure"] is not None
                        else "Indisponible"
                    )
                    f_val_str = (
                        f"{eval_info['latest_flow']:.1f} m³/h"
                        if eval_info["latest_flow"] is not None
                        else "Indisponible"
                    )

                    p_fallback_note = (
                        " *(via repli combiné)*"
                        if eval_info["pressure_is_fallback"]
                        else ""
                    )
                    f_fallback_note = (
                        " *(via repli combiné)*"
                        if eval_info["flow_is_fallback"]
                        else ""
                    )

                    st.write(
                        f"**Pression représentative :** {p_val_str} "
                        f"(Statut : `{eval_info['pressure_status']}`){p_fallback_note}"
                    )
                    st.write(
                        f"**Débit représentatif :** {f_val_str} "
                        f"(Statut : `{eval_info['flow_status']}`){f_fallback_note}"
                    )
                    st.write(
                        f"**Fraîcheur des données :** {eval_info['data_freshness']}"
                    )
                    st.write(
                        f"**Dernière mesure :** "
                        f"{eval_info['last_timestamp'][:19].replace('T', ' ') if eval_info['last_timestamp'] else 'Aucune'}"
                    )

                with col_right:
                    st.markdown("#### 🚨 Alerte en cours")
                    active_alert = eval_info.get("active_alert")
                    if active_alert:
                        st.error(
                            f"**{active_alert['alert_type']}** ({active_alert['severity']})\n\n"
                            f"{active_alert['message']}\n\n"
                            f"⏱️ Début : {active_alert['started_at'][:19].replace('T', ' ')}"
                        )
                    else:
                        st.success("Aucune alerte active sur cette zone.")

                    st.write(
                        f"**Lectures consécutives anormales :** "
                        f"Pression={eval_info['consecutive_low_pressure_count']}/3, "
                        f"Débit={eval_info['consecutive_low_flow_count']}/3"
                    )

                st.markdown("---")
                st.write(f"**Description :** {zone.get('description', 'N/D')}")
                st.write(
                    f"**Statut administratif :** {'Active' if zone['is_active'] else 'Inactive'}"
                )

                if sensors:
                    st.markdown("**Capteurs rattachés :**")
                    for s in sensors:
                        type_label = _SENSOR_TYPE_FR.get(
                            s["sensor_type"], s["sensor_type"]
                        )
                        active_icon = "✅" if s["is_active"] else "❌"
                        st.write(
                            f"  - {active_icon} **{s['name']}** — "
                            f"Type : {type_label}"
                        )
