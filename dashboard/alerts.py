"""Page Alertes et Incidents du tableau de bord AquaWatch (Sprint 2).

Affiche les alertes actives et l'historique des incidents résolus avec :
- Filtres multi-critères (Gouvernorat, Zone, Sévérité, Type, Statut).
- Indicateurs visuels explicites et textes descriptifs en français.
- Zone de démonstration contrôlée de scénarios anormaux (SIMULATED).
"""

import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

from backend.config import (
    ALERT_STATUS_ACTIVE,
    ALERT_STATUS_RESOLVED,
    ALERT_TYPE_LOW_FLOW,
    ALERT_TYPE_LOW_PRESSURE,
    ALERT_TYPE_POSSIBLE_INTERRUPTION,
    SEVERITY_CRITICAL,
    SEVERITY_WARNING,
)
from backend.repositories import (
    alert_repository,
    governorate_repository,
    zone_repository,
)
from backend.services import monitoring_service, simulation_service

_ALERT_TYPE_FR = {
    ALERT_TYPE_LOW_PRESSURE: "Pression faible",
    ALERT_TYPE_LOW_FLOW: "Débit faible",
    ALERT_TYPE_POSSIBLE_INTERRUPTION: "Interruption possible",
}

_SEVERITY_BADGES = {
    SEVERITY_CRITICAL: "🔴 CRITIQUE",
    SEVERITY_WARNING: "🟠 AVERTISSEMENT",
}

_STATUS_BADGES = {
    ALERT_STATUS_ACTIVE: "⚡ Active",
    ALERT_STATUS_RESOLVED: "✅ Résolue",
}


def render(conn: sqlite3.Connection) -> None:
    """Affiche la page Gestion et Historique des Alertes."""

    st.title("🚨 Alertes et Détection d'Interruptions")
    st.markdown(
        """
        Surveillance en temps simulé des anomalies d'approvisionnement en eau.
        Les alertes requièrent **3 lectures consécutives anormales** avant d'être déclenchées.
        """
    )

    st.warning(
        "⚠️ **Avertissement prototype académique** — Toutes les alertes sont issues "
        "de mesures simulées. Elles ne reflètent en aucun cas des coupures réelles du réseau SONEDE."
    )

    st.caption(
        "Les alertes sont mises à jour automatiquement après l'enregistrement "
        "des nouvelles mesures."
    )

    # ── Métriques clés des alertes ────────────────────────────
    st.subheader("📊 État global des alertes")
    counts = alert_repository.count_by_status(conn)
    active_count = counts.get(ALERT_STATUS_ACTIVE, 0)
    resolved_count = counts.get(ALERT_STATUS_RESOLVED, 0)

    active_alerts = alert_repository.get_all_active(conn)
    critical_count = sum(
        1 for a in active_alerts if a["severity"] == SEVERITY_CRITICAL
    )
    warning_count = sum(
        1 for a in active_alerts if a["severity"] == SEVERITY_WARNING
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Alertes actives", active_count)
    col2.metric("Critiques (Interruption)", critical_count)
    col3.metric("Avertissements", warning_count)
    col4.metric("Incidents résolus", resolved_count)

    # ── Section 1 : Alertes actives ───────────────────────────
    st.subheader("⚡ Alertes actives")

    if not active_alerts:
        st.success("🟢 Aucune alerte active. Tous les réseaux surveillés fonctionnent normalement.")
    else:
        for alert in active_alerts:
            sev_badge = _SEVERITY_BADGES.get(alert["severity"], alert["severity"])
            type_fr = _ALERT_TYPE_FR.get(alert["alert_type"], alert["alert_type"])
            with st.container(border=True):
                col_title, col_time = st.columns([3, 2])
                with col_title:
                    st.markdown(
                        f"### {sev_badge} — **{type_fr}**"
                    )
                    st.markdown(
                        f"📍 **Zone :** {alert['zone_name']} ({alert['zone_code']}) | "
                        f"🏛️ **Gouvernorat :** {alert['governorate_name']}"
                    )
                    st.write(f"📝 {alert['message']}")
                with col_time:
                    st.info(
                        f"⏱️ **Début :** {alert['started_at'][:19].replace('T', ' ')}\n\n"
                        f"🔄 **Dernière confirmation :** {alert['last_detected_at'][:19].replace('T', ' ')}"
                    )

    # ── Section 2 : Historique et filtres ───────────────────────
    st.subheader("📋 Historique complet des alertes")

    governorates = governorate_repository.get_all(conn)
    gov_options = {"Tous": None}
    gov_options.update({g["name"]: g["id"] for g in governorates})

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        selected_gov_name = st.selectbox(
            "Filtrer par gouvernorat", list(gov_options.keys()), key="alert_gov_filter"
        )
        selected_gov_id = gov_options[selected_gov_name]

    if selected_gov_id is not None:
        zones_list = zone_repository.get_by_governorate(conn, selected_gov_id)
    else:
        zones_list = zone_repository.get_all(conn)

    zone_options = {"Toutes": None}
    zone_options.update({f"{z['code']} — {z['name']}": z["id"] for z in zones_list})

    with col_f2:
        selected_zone_name = st.selectbox(
            "Filtrer par zone", list(zone_options.keys()), key="alert_zone_filter"
        )
        selected_zone_id = zone_options[selected_zone_name]

    with col_f3:
        status_filter = st.selectbox(
            "Statut",
            ["Tous", "Actives seulement", "Résolues seulement"],
            key="alert_status_filter",
        )
        db_status = None
        if status_filter == "Actives seulement":
            db_status = ALERT_STATUS_ACTIVE
        elif status_filter == "Résolues seulement":
            db_status = ALERT_STATUS_RESOLVED

    with col_f4:
        sev_filter = st.selectbox(
            "Sévérité", ["Toutes", "CRITICAL", "WARNING"], key="alert_sev_filter"
        )
        db_sev = None if sev_filter == "Toutes" else sev_filter

    alerts_list = alert_repository.get_filtered(
        conn,
        governorate_id=selected_gov_id,
        zone_id=selected_zone_id,
        severity=db_sev,
        status=db_status,
        limit=100,
    )

    if not alerts_list:
        st.info("Aucune alerte ne correspond aux filtres sélectionnés.")
    else:
        display_data = []
        for a in alerts_list:
            display_data.append(
                {
                    "ID": a["id"],
                    "Statut": _STATUS_BADGES.get(a["status"], a["status"]),
                    "Sévérité": _SEVERITY_BADGES.get(a["severity"], a["severity"]),
                    "Type": _ALERT_TYPE_FR.get(a["alert_type"], a["alert_type"]),
                    "Gouvernorat": a["governorate_name"],
                    "Zone": f"{a['zone_code']} — {a['zone_name']}",
                    "Message": a["message"],
                    "Début": a["started_at"][:19].replace("T", " "),
                    "Dernière détection": a["last_detected_at"][:19].replace("T", " "),
                    "Résolue le": (
                        a["resolved_at"][:19].replace("T", " ")
                        if a.get("resolved_at")
                        else "—"
                    ),
                }
            )
        st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)

    # ── Section 3 : Démonstration contrôlée (Simulation) ───────
    with st.expander("🧪 Démonstration de scénarios d'anomalies (SIMULATION)", expanded=False):
        st.markdown(
            """
            Cette section permet d'injecter des anomalies contrôlées pour tester
            le mécanisme de détection et la création/résolution d'alertes.
            Toutes les mesures générées portent la mention explicite `data_origin = 'SIMULATED'`.
            """
        )

        col_demo_zone, col_demo_type, col_demo_btn = st.columns([2, 2, 1])
        all_zones = zone_repository.get_all(conn)
        demo_zone_map = {f"{z['code']} — {z['name']}": z["id"] for z in all_zones}

        with col_demo_zone:
            chosen_zone_label = st.selectbox(
                "Zone cible", list(demo_zone_map.keys()), key="demo_zone"
            )
            chosen_zone_id = demo_zone_map[chosen_zone_label]

        with col_demo_type:
            demo_condition = st.selectbox(
                "Scénario à simuler",
                [
                    "interruption",
                    "low_pressure",
                    "low_flow",
                    "normal",
                ],
                format_func=lambda x: {
                    "interruption": "🔴 Interruption possible (Pression + Débit faibles, 3 lectures)",
                    "low_pressure": "🟠 Pression faible seule (3 lectures)",
                    "low_flow": "🟠 Débit faible seul (3 lectures)",
                    "normal": "🟢 Rétablissement normal (1 lecture normale)",
                }.get(x, x),
                key="demo_cond",
            )

        with col_demo_btn:
            st.write("")
            st.write("")
            if st.button("⚡ Injecter le scénario", use_container_width=True):
                count_to_gen = 1 if demo_condition == "normal" else 3
                with st.spinner("Génération des mesures de test..."):
                    simulation_service.generate_abnormal_measurements(
                        conn=conn,
                        zone_id=chosen_zone_id,
                        condition=demo_condition,
                        count=count_to_gen,
                        save=True,
                    )
                st.success(f"✅ Scénario '{demo_condition}' simulé et traité automatiquement !")
                st.rerun()
