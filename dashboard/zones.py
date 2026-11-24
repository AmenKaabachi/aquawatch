"""Page Gouvernorats et Zones du tableau de bord AquaWatch.

Affiche les quatre gouvernorats du Grand Tunis avec leurs
zones de surveillance hypothétiques et capteurs associés.
"""

import sqlite3

import streamlit as st

from backend.repositories import governorate_repository, sensor_repository, zone_repository
from backend.services import monitoring_service

_SENSOR_TYPE_FR = {
    "pressure": "Pression",
    "flow": "Débit",
    "combined": "Combiné",
}

_STATUS_BADGES = {
    "Normal": "🟢 Normal",
    "Données insuffisantes": "🟡 Données insuffisantes",
    "Inactive": "🔴 Inactive",
}


def render(conn: sqlite3.Connection) -> None:
    """Affiche la page Gouvernorats et Zones."""

    st.title("🗺️ Gouvernorats et Zones de surveillance")
    st.markdown(
        """
        Les quatre gouvernorats du Grand Tunis et leurs zones de
        surveillance hypothétiques. Chaque zone est équipée de
        capteurs virtuels pour la démonstration.
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
            status = monitoring_service.get_zone_status(conn, zone["id"])
            sensors = sensor_repository.get_by_zone(conn, zone["id"])
            status_badge = _STATUS_BADGES.get(status, f"⚪ {status}")

            with st.expander(
                f"📍 {zone['code']} — {zone['name']}  |  {status_badge}",
                expanded=False,
            ):
                st.write(f"**Description :** {zone.get('description', 'N/D')}")
                st.write(
                    f"**Statut :** {'Active' if zone['is_active'] else 'Inactive'}"
                )
                st.write(f"**Nombre de capteurs :** {len(sensors)}")

                if sensors:
                    st.markdown("**Capteurs de la zone :**")
                    for sensor in sensors:
                        type_label = _SENSOR_TYPE_FR.get(
                            sensor["sensor_type"], sensor["sensor_type"]
                        )
                        active_icon = "✅" if sensor["is_active"] else "❌"
                        st.write(
                            f"  - {active_icon} **{sensor['name']}** — "
                            f"Type : {type_label}"
                        )
