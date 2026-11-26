"""Dashboard page for comparing sensor collection strategies."""

import asyncio
import sqlite3
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from backend.repositories import (
    measurement_repository,
    sensor_repository,
    zone_repository,
)
from backend.services import (
    async_sensor_service,
    benchmark_service,
    dask_analysis_service,
    multiprocessing_service,
    threaded_sensor_service,
)

_STRATEGIES = {
    "Séquentiel": "sequential",
    "Asyncio": "asyncio",
    "Multithreading": "threaded",
}


def _collect(strategy: str, sensors: list, response_delay: float, workers: int):
    if strategy == "sequential":
        return asyncio.run(
            async_sensor_service.collect_sequential(
                sensors,
                response_delay,
                seed=42,
            )
        )
    if strategy == "asyncio":
        return asyncio.run(
            async_sensor_service.collect_async(
                sensors,
                response_delay,
                seed=42,
            )
        )
    return threaded_sensor_service.collect_threaded(
        sensors,
        response_delay,
        max_workers=workers,
        seed=42,
    )


def _render_collection_result(result: dict) -> None:
    labels = {
        "sequential": "Séquentiel",
        "asyncio": "Asyncio",
        "threaded": "Multithreading",
    }
    st.subheader("Résultat de la collecte")
    st.caption(f"Stratégie : {labels[result['strategy']]}")

    metrics = st.columns(5)
    metrics[0].metric("Capteurs traités", result["processed"])
    metrics[1].metric("Mesures réussies", result["successful"])
    metrics[2].metric("Échecs", result["failed"])
    metrics[3].metric("Durée", f"{result['execution_time']:.4f} s")
    metrics[4].metric(
        "Workers",
        result.get("worker_count", "—"),
    )
    persistence_message = (
        f"{result['persisted']} mesure(s) persistée(s) et transmise(s) "
        "au suivi des zones."
    )
    if result["failed"] == 0:
        st.success(f"Collecte terminée : {persistence_message}")
    elif result["successful"] > 0:
        st.warning(
            f"Collecte partielle : {persistence_message} "
            f"{result['failed']} capteur(s) en échec."
        )
    else:
        st.error(
            f"Aucune mesure collectée : {result['failed']} capteur(s) en échec."
        )

    if result["failures"]:
        st.warning("Certains capteurs n'ont pas répondu.")
        st.caption("Capteurs concernés et raisons de l'échec.")
        st.dataframe(
            pd.DataFrame(result["failures"]),
            hide_index=True,
        )
    if result.get("activities"):
        activity_frame = pd.DataFrame(result["activities"])
        st.subheader("Activité des workers")
        st.caption("Threads utilisés, capteurs traités et durée de chaque collecte.")
        st.dataframe(
            activity_frame,
            hide_index=True,
        )


def _render_benchmark(results: list) -> None:
    if not results:
        return

    st.subheader("Comparaison mesurée")
    table = pd.DataFrame(
        [
            {
                "Workers": row["worker_count"],
                "Capteurs": row["processed"],
                "Séquentiel (s)": row["sequential_time"],
                "Asyncio (s)": row["async_time"],
                "Multithreading (s)": row["threaded_time"],
                "Speedup asyncio": row["async_speedup"],
                "Speedup multithreading": row["threaded_speedup"],
                "Temps économisé asyncio (s)": row["async_time_saved"],
                "Temps économisé multithreading (s)": row[
                    "threaded_time_saved"
                ],
                "Amélioration asyncio (%)": row["async_improvement_percent"],
                "Amélioration multithreading (%)": row[
                    "threaded_improvement_percent"
                ],
                "Réussies": row["threaded_successful"],
                "Échecs": row["threaded_failed"],
            }
            for row in results
        ]
    )
    st.caption("Temps et métriques réellement mesurés pour chaque stratégie et pool.")
    st.dataframe(table, hide_index=True)

    duration_figure = go.Figure()
    for column, name in (
        ("sequential_time", "Séquentiel"),
        ("async_time", "Asyncio"),
        ("threaded_time", "Multithreading"),
    ):
        duration_figure.add_bar(
            x=[str(row["worker_count"]) for row in results],
            y=[row[column] for row in results],
            name=name,
        )
    duration_figure.update_layout(
        title="Durée de collecte par stratégie",
        barmode="group",
        xaxis_title="Nombre de workers configuré",
        yaxis_title="Temps de collecte (secondes)",
    )
    st.plotly_chart(duration_figure)

    speedup_figure = go.Figure()
    speedup_figure.add_bar(
        x=[str(row["worker_count"]) for row in results],
        y=[row["async_speedup"] for row in results],
        name="Asyncio",
    )
    speedup_figure.add_bar(
        x=[str(row["worker_count"]) for row in results],
        y=[row["threaded_speedup"] for row in results],
        name="Multithreading",
    )
    speedup_figure.update_layout(
        title="Speedup relatif au séquentiel",
        barmode="group",
        xaxis_title="Nombre de workers configuré",
        yaxis_title="Speedup relatif au séquentiel",
    )
    st.plotly_chart(speedup_figure)
    st.caption(
        "Un speedup supérieur à 1 indique une exécution plus rapide que le "
        "séquentiel. Les résultats peuvent varier selon la machine et la charge."
    )


def render(conn: sqlite3.Connection) -> None:
    st.title("Collecte concurrente des capteurs")
    st.markdown(
        """
        Comparez trois façons d'effectuer la même collecte simulée : une par
        une, avec une boucle d'événements `asyncio`, ou avec plusieurs threads
        via `ThreadPoolExecutor`.
        """
    )
    st.warning(
        "Les capteurs et latences sont simulés. Les collectes exécutées "
        "individuellement enregistrent leurs mesures dans SQLite; un benchmark "
        "ne modifie pas la base de données."
    )

    sensors = sensor_repository.get_active(conn)
    if not sensors:
        st.info("Aucun capteur actif disponible.")
        return

    sensor_count = st.slider(
        "Nombre de capteurs",
        min_value=1,
        max_value=len(sensors),
        value=min(24, len(sensors)),
    )
    selected_sensors = sensors[:sensor_count]
    response_delay = st.slider(
        "Latence simulée par capteur (secondes)",
        min_value=0.01,
        max_value=1.0,
        value=0.10,
        step=0.01,
    )
    strategy_label = st.segmented_control(
        "Stratégie de collecte",
        options=list(_STRATEGIES),
        default="Séquentiel",
        key="collection_strategy",
    )
    strategy = _STRATEGIES[strategy_label]

    workers = 4
    if strategy == "threaded":
        workers = st.slider(
            "Nombre de threads workers",
            min_value=1,
            max_value=min(8, sensor_count),
            value=min(4, sensor_count),
            key="collection_workers",
        )

    if st.button("Exécuter et enregistrer", type="primary", width="stretch"):
        with st.spinner("Collecte des capteurs en cours..."):
            started = time.perf_counter()
            result = _collect(
                strategy,
                selected_sensors,
                response_delay,
                workers,
            )
            execution_time = time.perf_counter() - started
            persisted = measurement_repository.insert_many(
                conn,
                result["measurements"],
            ) if result["measurements"] else 0
        st.session_state["latest_collection_result"] = {
            **result,
            "strategy": strategy,
            "execution_time": execution_time,
            "processed": len(selected_sensors),
            "persisted": persisted,
        }

    latest_result = st.session_state.get("latest_collection_result")
    if latest_result:
        _render_collection_result(latest_result)

    st.subheader("Benchmark comparatif")
    repetitions = st.slider(
        "Répétitions par configuration",
        min_value=1,
        max_value=5,
        value=3,
    )
    st.caption(
        "Le benchmark utilise les mêmes capteurs, le même délai, l'horodatage "
        "et la graine par répétition; il ne persiste pas les mesures."
    )
    if st.button("Comparer les stratégies", width="stretch"):
        worker_counts = sorted(
            {count for count in (1, 2, 4, 8, workers) if count <= sensor_count}
        )
        with st.spinner("Benchmark en cours..."):
            results = benchmark_service.run_benchmark(
                [{"sensors": selected_sensors}],
                response_delay,
                repetitions=repetitions,
                seed=42,
                worker_counts=worker_counts,
            )
        st.session_state["sprint4_benchmark"] = results

    _render_benchmark(st.session_state.get("sprint4_benchmark", []))

    st.subheader("Comment interpréter les stratégies")
    st.markdown(
        """
        - **Séquentiel** : chaque collecte attend la fin de la précédente.
        - **Asyncio** : une boucle d'événements coordonne des coroutines qui
          cèdent la main pendant l'attente, sans créer un thread par capteur.
        - **Multithreading** : un pool borné de threads exécute les opérations
          bloquantes; les workers renvoient leurs résultats et le thread
          principal effectue seul les écritures SQLite.

        En CPython standard, le **GIL** empêche généralement plusieurs threads
        d'exécuter du bytecode Python simultanément. Les threads conviennent
        donc surtout aux attentes d'entrées-sorties, pas au calcul Python
        intensif. L'analyse CPU ci-dessous illustre le multiprocessing pour
        comparer les pertes d'eau entre zones.
        """
    )

    st.subheader("Analyse CPU des pertes d'eau par zone")
    st.caption(
        "Cette démonstration utilise des débits synthétiques déterministes "
        "et ne modifie pas la base de données."
    )
    zones = zone_repository.get_all(conn)
    if not zones:
        st.info("Aucune zone disponible pour l'analyse.")
        return

    zone_workloads = [
        {
            "id": zone["id"],
            "name": zone["name"],
            "inflow_m3_h": 1000 + zone["id"] * 50,
            "delivered_m3_h": 920 + zone["id"] * 45,
        }
        for zone in zones
    ]
    analysis_mode = st.segmented_control(
        "Mode d'analyse",
        options=["Séquentiel", "Multiprocessing", "Dask Distributed"],
        default="Multiprocessing",
        key="sprint5_analysis_mode",
    )
    iterations = st.slider(
        "Calculs par zone",
        min_value=1000,
        max_value=100000,
        value=20000,
        step=1000,
        key="sprint5_iterations",
    )
    worker_count = 2
    if analysis_mode == "Multiprocessing":
        worker_count = st.select_slider(
            "Nombre de processus",
            options=[1, 2, 4],
            value=2,
            key="sprint5_process_count",
        )
    elif analysis_mode == "Dask Distributed":
        worker_count = st.select_slider(
            "Nombre de workers Dask",
            options=[1, 2, 4],
            value=2,
            key="sprint6_dask_workers",
        )

    if st.button("Exécuter l'analyse CPU", key="sprint5_run_analysis"):
        started = time.perf_counter()
        with st.spinner(f"Analyse {analysis_mode} des zones..."):
            if analysis_mode == "Séquentiel":
                analysis_results = (
                    multiprocessing_service.analyze_zones_sequential(
                        zone_workloads,
                        iterations=iterations,
                    )
                )
            elif analysis_mode == "Multiprocessing":
                analysis_results = multiprocessing_service.analyze_zones(
                    zone_workloads,
                    iterations=iterations,
                    max_workers=worker_count,
                )
            else:
                analysis_results = dask_analysis_service.analyze_zones_dask(
                    zone_workloads,
                    iterations=iterations,
                    n_workers=worker_count,
                )
        st.session_state["sprint5_analysis_result"] = {
            "mode": analysis_mode,
            "worker_count": worker_count,
            "execution_time": time.perf_counter() - started,
            "results": analysis_results,
        }

    analysis_result = st.session_state.get("sprint5_analysis_result")
    if analysis_result:
        result_worker_count = analysis_result.get(
            "worker_count",
            analysis_result.get("process_count", 0),
        )
        process_details = (
            f" ({result_worker_count} workers)"
            if analysis_result["mode"] != "Séquentiel"
            else ""
        )
        st.caption(
            f"{analysis_result['mode']}{process_details} — "
            f"{analysis_result['execution_time']:.4f} s"
        )
        st.dataframe(
            pd.DataFrame(analysis_result["results"]),
            hide_index=True,
        )

    if st.button(
        "Comparer séquentiel, multiprocessing et Dask",
        key="sprint6_benchmark",
    ):
        with st.spinner("Benchmark CPU en cours..."):
            benchmark = benchmark_service.benchmark_cpu_analysis(
                zone_workloads,
                iterations=iterations,
                process_counts=[1, 2, 4],
                dask_worker_counts=[1, 2, 4],
            )
        st.session_state["sprint6_benchmark_result"] = benchmark

    benchmark = st.session_state.get("sprint6_benchmark_result")
    if benchmark:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Stratégie": row["strategy"],
                        "Workers / processus": row["worker_count"],
                        "Séquentiel (s)": benchmark["sequential_time"],
                        "Durée (s)": row["execution_time"],
                        "Speedup": row["speedup"],
                    }
                    for row in benchmark["comparisons"]
                ]
            ),
            hide_index=True,
        )
        st.caption(
            "Le démarrage des processus, la communication et la planification "
            "Dask ont un coût; le calcul distribué n'est pas toujours plus rapide."
        )
