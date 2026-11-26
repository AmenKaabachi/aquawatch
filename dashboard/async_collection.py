"""Page Streamlit Sprint 3 : collecte asynchrone des capteurs."""

import sqlite3

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from backend.repositories import sensor_repository
from backend.services import async_sensor_service, benchmark_service


def render(conn: sqlite3.Connection) -> None:
    st.title("⚡ Collecte asynchrone des capteurs")
    st.markdown(
        """
        Sprint 3 — démonstration de concurrence asynchrone avec `asyncio`.
        Les capteurs sont virtuels et la latence est simulée.
        """
    )
    st.warning(
        "Aucune communication réelle avec la SONEDE n'est effectuée. "
        "Le benchmark ne sauvegarde aucune mesure."
    )

    sensors = sensor_repository.get_active(conn)
    if not sensors:
        st.info("Aucun capteur actif disponible.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        sensor_count = st.slider(
            "Nombre de capteurs",
            min_value=1,
            max_value=len(sensors),
            value=min(24, len(sensors)),
        )
    with col2:
        response_delay = st.slider(
            "Latence simulée par capteur (secondes)",
            min_value=0.01,
            max_value=1.0,
            value=0.10,
            step=0.01,
        )
    with col3:
        repetitions = st.slider(
            "Répétitions du benchmark",
            min_value=1,
            max_value=5,
            value=3,
        )

    selected_sensors = sensors[:sensor_count]
    col_seq, col_async, col_bench = st.columns(3)

    with col_seq:
        if st.button("Collecte séquentielle", use_container_width=True):
            import asyncio

            result = asyncio.run(
                async_sensor_service.collect_sequential(
                    selected_sensors,
                    response_delay,
                    seed=42,
                )
            )
            st.success(
                f"{result['successful']} mesure(s) réussie(s), "
                f"{result['failed']} échec(s)"
            )

    with col_async:
        if st.button("Collecte asyncio", use_container_width=True):
            result = async_sensor_service.collect_and_save(
                conn,
                selected_sensors,
                response_delay,
                seed=42,
            )
            st.success(
                f"{result['successful']} collectée(s), "
                f"{result['persisted']} sauvegardée(s), "
                f"{result['failed']} échec(s)"
            )

    with col_bench:
        if st.button("Comparer les méthodes", use_container_width=True):
            workloads = []
            for count in (4, 8, 16, 24):
                if count <= len(sensors):
                    workloads.append({"sensors": sensors[:count]})

            if not workloads:
                workloads = [{"sensors": selected_sensors}]

            results = benchmark_service.run_benchmark(
                workloads,
                response_delay,
                repetitions=repetitions,
                seed=42,
            )
            st.session_state["sprint3_benchmark"] = results

    results = st.session_state.get("sprint3_benchmark")
    if results:
        df = pd.DataFrame(
            [
                {
                    "Capteurs": row["sensor_count"],
                    "Séquentiel (s)": row["sequential_time"],
                    "Async (s)": row["async_time"],
                    "Speedup": row["speedup"],
                    "Mesures réussies": row["successful_measurements"],
                    "Échecs": row["failed_sensors"],
                }
                for row in results
            ]
        )
        st.subheader("Résultats du benchmark")
        st.dataframe(df, use_container_width=True, hide_index=True)

        fig = go.Figure()
        fig.add_bar(
            x=df["Capteurs"].astype(str),
            y=df["Séquentiel (s)"],
            name="Séquentiel",
        )
        fig.add_bar(
            x=df["Capteurs"].astype(str),
            y=df["Async (s)"],
            name="Async",
        )
        fig.update_layout(
            barmode="group",
            xaxis_title="Nombre de capteurs",
            yaxis_title="Temps (secondes)",
        )
        st.plotly_chart(fig, use_container_width=True)
