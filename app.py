"""AquaWatch Grand Tunis — Point d'entrée Streamlit.

Application de surveillance simulée de l'approvisionnement en eau
pour les quatre gouvernorats du Grand Tunis.

Lancement::

    streamlit run app.py
"""

import streamlit as st

from backend.config import DATABASE_PATH
from backend.database.connection import get_connection
from backend.database.init_db import init_database
from dashboard import alerts, async_collection, measurements, overview, zones


# ── Configuration de la page ─────────────────────────────────
st.set_page_config(
    page_title="AquaWatch Grand Tunis",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Initialisation automatique de la BDD ─────────────────────
if not DATABASE_PATH.exists():
    with st.spinner("Initialisation de la base de données..."):
        success = init_database()
        if not success:
            st.error(
                "❌ Impossible d'initialiser la base de données. "
                "Exécutez `python -m backend.database.init_db` manuellement."
            )
            st.stop()

# ── Connexion ────────────────────────────────────────────────
conn = get_connection()

# ── Barre latérale ───────────────────────────────────────────
st.sidebar.title("💧 AquaWatch")
st.sidebar.caption("Grand Tunis — Sprint 3 : Collecte asynchrone")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    options=[
        "🏠 Vue d'ensemble",
        "🗺️ Gouvernorats et zones",
        "🚨 Alertes & Incidents",
        "📊 Surveillance des capteurs",
        "📋 Données",
        "⚡ Collecte asynchrone",
    ],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "🔬 **Prototype académique**\n\n"
    "Les mesures sont **simulées** et ne proviennent "
    "pas du réseau SONEDE.\n\n"
    "Projet : Systèmes Parallèles et Distribués — ISAMM"
)

# ── Rendu de la page sélectionnée ────────────────────────────
if page == "🏠 Vue d'ensemble":
    overview.render(conn)
elif page == "🗺️ Gouvernorats et zones":
    zones.render(conn)
elif page == "🚨 Alertes & Incidents":
    alerts.render(conn)
elif page == "📊 Surveillance des capteurs":
    measurements.render_sensors(conn)
elif page == "📋 Données":
    measurements.render_data(conn)
elif page == "⚡ Collecte asynchrone":
    async_collection.render(conn)

# ── Fermeture de la connexion ────────────────────────────────
conn.close()
