"""Pages Surveillance des capteurs et Données du tableau de bord.

Ce module fournit deux rendus :
- ``render_sensors`` : graphiques Plotly de pression et débit par capteur.
- ``render_data`` : tableau filtrable et bouton de génération de mesures.
"""

import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

from backend.repositories import (
    governorate_repository,
    measurement_repository,
    sensor_repository,
    zone_repository,
)
from backend.services import simulation_service

_SENSOR_TYPE_FR = {
    "pressure": "Pression",
    "flow": "Débit",
    "combined": "Combiné",
}


def _format_measurement(value, unit: str = "") -> str:
    """Affiche une valeur numérique ou signale explicitement son absence."""
    if pd.isna(value):
        return "—"
    unit_suffix = f" {unit}" if unit else ""
    return f"{value:.2f}{unit_suffix}"


# ── Page : Surveillance des capteurs ─────────────────────────


def render_sensors(conn: sqlite3.Connection) -> None:
    """Affiche la page Surveillance des capteurs avec graphiques Plotly."""

    st.title("📊 Surveillance des capteurs")
    st.markdown("Visualisation des mesures de pression et de débit par capteur.")

    # Sélection du capteur
    sensors = sensor_repository.get_active(conn)

    if not sensors:
        st.warning("Aucun capteur actif trouvé.")
        return

    sensor_options = {
        f"{s['name']} ({s['zone_name']})": s["id"] for s in sensors
    }

    selected_label = st.selectbox(
        "Sélectionner un capteur", options=list(sensor_options.keys())
    )

    if not selected_label:
        return

    selected_sensor_id = sensor_options[selected_label]
    sensor_info = sensor_repository.get_by_id(conn, selected_sensor_id)

    if sensor_info:
        type_label = _SENSOR_TYPE_FR.get(
            sensor_info["sensor_type"], sensor_info["sensor_type"]
        )
        col1, col2, col3 = st.columns(3)
        col1.write(f"**Capteur :** {sensor_info['name']}")
        col2.write(f"**Type :** {type_label}")
        col3.write(f"**Zone :** {sensor_info['zone_name']}")

    # Récupérer les mesures
    measurements = measurement_repository.get_by_sensor(
        conn, selected_sensor_id, limit=200
    )

    if not measurements:
        st.info(
            "Aucune mesure disponible pour ce capteur. "
            "Générez des mesures depuis la page **📋 Données**."
        )
        return

    # Dernière mesure
    latest = measurements[0]
    st.subheader("📡 Dernière mesure")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Pression",
        _format_measurement(latest["pressure_bar"], "bar"),
    )
    col2.metric(
        "Débit",
        _format_measurement(latest["flow_m3_h"], "m³/h"),
    )
    col3.metric("Horodatage", latest["timestamp"][:16].replace("T", " "))
    col4.metric("Origine", latest["data_origin"])

    # Préparer le DataFrame
    df = pd.DataFrame(measurements)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    # Graphique de pression
    st.subheader("📈 Historique de pression")
    if df["pressure_bar"].notna().any():
        fig_pressure = px.line(
            df,
            x="timestamp",
            y="pressure_bar",
            title="Pression (bar)",
            labels={"timestamp": "Horodatage", "pressure_bar": "Pression (bar)"},
        )
        # Seuil d'anomalie de basse pression (1.5 bar)
        fig_pressure.add_hline(
            y=1.5,
            line_dash="dash",
            line_color="red",
            annotation_text="Seuil pression basse (1.5 bar)",
            annotation_position="bottom right",
        )
        fig_pressure.update_layout(
            xaxis_title="Horodatage",
            yaxis_title="Pression (bar)",
            height=400,
        )
        st.plotly_chart(fig_pressure, use_container_width=True)
    else:
        st.info("Pas de données de pression disponibles.")

    # Graphique de débit
    st.subheader("📈 Historique de débit")
    if df["flow_m3_h"].notna().any():
        fig_flow = px.line(
            df,
            x="timestamp",
            y="flow_m3_h",
            title="Débit (m³/h)",
            labels={"timestamp": "Horodatage", "flow_m3_h": "Débit (m³/h)"},
        )
        # Seuil d'anomalie de faible débit (50 m³/h)
        fig_flow.add_hline(
            y=50.0,
            line_dash="dash",
            line_color="orange",
            annotation_text="Seuil débit bas (50 m³/h)",
            annotation_position="bottom right",
        )
        fig_flow.update_layout(
            xaxis_title="Horodatage",
            yaxis_title="Débit (m³/h)",
            height=400,
        )
        st.plotly_chart(fig_flow, use_container_width=True)
    else:
        st.info("Pas de données de débit disponibles.")


# ── Page : Données ───────────────────────────────────────────


def render_data(conn: sqlite3.Connection) -> None:
    """Affiche la page Données avec filtres et génération de mesures."""

    st.title("📋 Données")
    st.markdown("Consultation et génération de mesures simulées.")

    st.warning(
        "⚠️ Toutes les mesures affichées ci-dessous sont **simulées** "
        "et ne proviennent pas de capteurs réels."
    )

    # ── Génération ───────────────────────────────────────────
    st.subheader("🔄 Générer de nouvelles mesures")

    col_desc, col_btn = st.columns([3, 1])
    with col_desc:
        st.caption(
            "Génère un lot de mesures simulées pour tous les capteurs "
            "actifs et les enregistre dans la base de données SQLite."
        )
    with col_btn:
        if st.button("🔄 Générer", use_container_width=True):
            with st.spinner("Génération en cours..."):
                new_measurements = simulation_service.generate_measurements(
                    conn, save=True
                )
            st.success(
                f"✅ {len(new_measurements)} mesures générées avec succès !"
            )
            st.rerun()

    # ── Filtres ──────────────────────────────────────────────
    st.subheader("🔍 Filtres")

    governorates = governorate_repository.get_all(conn)
    gov_options = {"Tous": None}
    gov_options.update({g["name"]: g["id"] for g in governorates})

    col1, col2, col3 = st.columns(3)

    with col1:
        selected_gov_name = st.selectbox("Gouvernorat", list(gov_options.keys()))
        selected_gov_id = gov_options[selected_gov_name]

    # Zones filtrées par gouvernorat
    if selected_gov_id is not None:
        zones_list = zone_repository.get_by_governorate(conn, selected_gov_id)
    else:
        zones_list = zone_repository.get_all(conn)

    zone_options = {"Toutes": None}
    zone_options.update(
        {f"{z['code']} — {z['name']}": z["id"] for z in zones_list}
    )

    with col2:
        selected_zone_name = st.selectbox("Zone", list(zone_options.keys()))
        selected_zone_id = zone_options[selected_zone_name]

    # Capteurs filtrés par zone
    if selected_zone_id is not None:
        sensors_list = sensor_repository.get_by_zone(conn, selected_zone_id)
    elif selected_gov_id is not None:
        sensors_list = []
        for z in zones_list:
            sensors_list.extend(sensor_repository.get_by_zone(conn, z["id"]))
    else:
        sensors_list = sensor_repository.get_all(conn)

    sensor_options = {"Tous": None}
    sensor_options.update({s["name"]: s["id"] for s in sensors_list})

    with col3:
        selected_sensor_name = st.selectbox("Capteur", list(sensor_options.keys()))
        selected_sensor_id = sensor_options[selected_sensor_name]

    # ── Tableau des mesures ──────────────────────────────────
    st.subheader("📊 Mesures récentes")

    measurements = measurement_repository.get_filtered(
        conn,
        governorate_id=selected_gov_id,
        zone_id=selected_zone_id,
        sensor_id=selected_sensor_id,
        limit=200,
    )

    if not measurements:
        st.info(
            "Aucune mesure trouvée. Utilisez le bouton ci-dessus pour "
            "générer de nouvelles mesures simulées."
        )
        return

    st.caption(f"Affichage de {len(measurements)} mesures les plus récentes")

    df = pd.DataFrame(measurements)

    display_columns = {
        "timestamp": "Horodatage",
        "sensor_name": "Capteur",
        "zone_name": "Zone",
        "governorate_name": "Gouvernorat",
        "pressure_bar": "Pression (bar)",
        "flow_m3_h": "Débit (m³/h)",
        "quality_status": "Qualité",
        "data_origin": "Origine",
    }

    available = [c for c in display_columns if c in df.columns]
    df_display = df[available].rename(
        columns={c: display_columns[c] for c in available}
    )
    for column in ("Pression (bar)", "Débit (m³/h)"):
        if column in df_display:
            df_display[column] = df_display[column].map(_format_measurement)

    st.dataframe(df_display, use_container_width=True, hide_index=True)
