# AquaWatch Grand Tunis — Sprint 2 : Surveillance de l'Approvisionnement & Détection d'Interruptions

**AquaWatch Grand Tunis** est une application académique de simulation et de surveillance de l'approvisionnement en eau potable à travers les quatre gouvernorats du Grand Tunis.

Ce projet s'inscrit dans le cadre du cours **Systèmes Parallèles et Distribués** (ISAMM, 2ème année). À terme, l'application servira de support pour démontrer des techniques de programmation concurrente et distribuée en Python.

---

## 1. Objectifs des Sprints

### Sprint 1 : Socle architectural et simulation
- **Structure géographique** : 4 gouvernorats du Grand Tunis et 8 zones de surveillance hypothétiques (2 par gouvernorat).
- **Capteurs virtuels** : 24 capteurs (pression, débit, combiné) rattachés aux zones de surveillance.
- Chaque zone possède un capteur de pression, un capteur de débit et un capteur combiné, ce dernier représentant un seul appareil virtuel qui mesure les deux variables.
- Les mesures non prises en charge par un capteur sont stockées en `NULL` (et affichées comme indisponibles), jamais comme zéro. Toutes les mesures sont simulées.
- **Simulateur de mesures** : Générateur déterministe et réaliste de mesures de pression (bar) et de débit (m³/h).
- **Base de données relationnelle** : SQLite avec tables, clés étrangères activées, index et scripts SQL dédiés.
- **Tableau de bord Streamlit initial** : Navigation et visualisation Plotly.

### Sprint 2 : Surveillance fiable et détection des interruptions
Le Sprint 2 enrichit le socle avec un moteur d'analyse et d'alertes déterministe :
- **Surveillance au niveau zone** : Dérivation d'une mesure représentative par métrique avec politique de sélection stricte et repli automatique sur capteur combiné.
- **Seuils paramétrables** : Pression basse (<= 1.5 bar) et Débit bas (<= 50.0 m³/h).
- **Validation par lectures consécutives** : Exigence de 3 lectures anormales consécutives avant déclenchement d'alerte, évitant les fausses alertes sur anomalies passagères.
- **Gestion rigoureuse de la qualité** : Traitement explicite des données manquantes, invalides (`quality_status != 'valid'`) et obsolètes (> 24h).
- **Persistance et cycle de vie des alertes** : Nouvelles tables `alerts` et `monitoring_states` avec index, historique préservé et résolution automatique lors du retour à la normale.
- **Tableau de bord enrichi** :
  - Synthèse globale sur la page *Vue d'ensemble* (6 cartes KPI, table détaillée).
  - Page dédiée *Alertes & Incidents* avec filtres multi-critères et injecteur de scénarios de test.
  - Page *Gouvernorats et zones* affichant l'état temps-réel, les lectures représentatives et le statut de repli.
  - Graphiques Plotly avec lignes de référence des seuils critiques.
- **Suite de tests automatisée** : 92 tests validant l'intégrité, les repositories, les règles de détection et les 12 scénarios d'acceptation.

---

## 2. Distinction entre données réelles et données simulées

AquaWatch distingue clairement les données contextuelles réelles des mesures opérationnelles :

| Type d'information | Source | Nature |
|---|---|---|
| Gouvernorats du Grand Tunis | Découpage administratif officiel | ✅ Données réelles |
| Population par gouvernorat | INS Tunisie (Recensement 2024 / estimations publiques) | ✅ Données réelles de référence |
| Découpage administratif | OCHA / HDX / data4tunisia | ✅ Données réelles de référence |
| Zones de surveillance | Configuration du projet AquaWatch | ⚠️ Hypothétique (démonstration) |
| Capteurs virtuels | Modèle du simulateur | ⚠️ Virtuel / Simulé |
| Pression (bar) & Débit (m³/h) | Simulateur Python | ⚠️ Simulé (`SIMULATED`) |

> ⚠️ **Avertissement éthique & méthodologique** : Les capteurs et leurs relevés de pression/débit sont entièrement simulés. Ils ne représentent en aucun cas des mesures effectives du réseau SONEDE.

Les plages de simulation utilisées par le projet (pression : 1,5–6,0 bar ; débit : 50–500 m³/h) sont illustratives. Elles ne constituent pas des seuils officiels de la SONEDE.

Pour plus de détails, consultez [DATA_SOURCES.md](DATA_SOURCES.md).

---

## 3. Architecture et arborescence du projet

```text
aquawatch-grand-tunis/
├── app.py                      # Point d'entrée du tableau de bord Streamlit
├── requirements.txt            # Dépendances Python minimales
├── README.md                   # Documentation complète et guide d'exécution
├── DATA_SOURCES.md             # Documentation détaillée des sources de données
├── .gitignore                  # Fichiers exclus du contrôle de version
├── .env.example                # Modèle de configuration locale
├── backend/
│   ├── __init__.py
│   ├── config.py               # Constantes, chemins et paramètres du projet
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py       # Gestionnaire de connexion SQLite
│   │   ├── init_db.py          # Script idempotent d'initialisation de la BDD
│   │   ├── schema.sql          # Définition des tables, contraintes et index
│   │   └── seed.sql            # Données initiales (gouvernorats, zones, capteurs)
│   ├── models/
│   │   ├── __init__.py
│   │   └── measurement.py      # Dataclasses représentatives des entités
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── governorate_repository.py # Accès données gouvernorats
│   │   ├── zone_repository.py        # Accès données zones
│   │   ├── sensor_repository.py      # Accès données capteurs
│   │   └── measurement_repository.py # Insertion et requêtes sur les mesures
│   ├── services/
│   │   ├── __init__.py
│   │   ├── simulation_service.py     # Générateur de mesures simulées
│   │   └── monitoring_service.py     # Logique de statut de surveillance
│   └── utils/
│       ├── __init__.py
│       └── time_utils.py       # Horodatages ISO 8601 UTC
├── dashboard/
│   ├── __init__.py
│   ├── overview.py             # Page 1 : Vue d'ensemble & métriques globales
│   ├── zones.py                # Page 2 : Gouvernorats et zones de surveillance
│   └── measurements.py         # Pages 3 & 4 : Surveillance capteurs & Données
├── data/
│   └── .gitkeep                # Dossier accueillant aquawatch.db
├── docs/
│   └── DATA_SOURCES.md         # Copie documentaire
└── tests/
    ├── __init__.py
    ├── conftest.py             # Fixtures Pytest (BDD de test temporaire)
    ├── test_database.py        # Tests d'intégrité BDD et contraintes
    ├── test_simulation.py      # Tests du générateur de mesures
    ├── test_repositories.py    # Tests des requêtes et filtres
    └── test_monitoring.py      # Tests des règles de statut
```

---

## 4. Prérequis

- **Python** : Version 3.10 ou supérieure (testé sous Python 3.13)
- **Système d'exploitation** : Windows, Linux ou macOS
- **Gestionnaire de paquets** : `pip`

---

## 5. Guide d'installation et de lancement (Windows PowerShell)

Toutes les commandes ci-dessous sont à exécuter dans le répertoire du projet `aquawatch-grand-tunis`.

### 5.1 Création et activation de l'environnement virtuelLoad older messages
Conversation Log
continue
La suite de tests automatisés Pytest a été lancée et s'exécute actuellement en arrière-plan. Je vous informe dès que l'exécution est terminée avec le rapport complet des résultats.

💧 AquaWatch Grand Tunis — Rapport d'Implémentation Sprint 1
Le Sprint 1 (Project Foundation) d'AquaWatch Grand Tunis est entièrement implémenté, initialisé et validé par une suite complète de tests automatisés.

1. Ce qui a été implémenté
Architecture & Structure modulaire :
Séparation stricte des responsabilités : configuration (backend/config.py), persistance SQLite (backend/database/), modèles (backend/models/), repositories (backend/repositories/), services métier (backend/services/), utilitaires de temps ISO 8601 (backend/utils/) et interface utilisateur (dashboard/ et app.py).
Couche de données relationnelle SQLite :
Fichiers SQL dédiés et indépendants : 
schema.sql
 et 
seed.sql
.
Activation des clés étrangères (PRAGMA foreign_keys = ON), contraintes CHECK, et index d'optimisation de requêtes.
Initialisation idempotente avec INSERT OR IGNORE via 
init_db.py
.
Périmètre géographique & Capteurs virtuels :
4 gouvernorats du Grand Tunis : Tunis, Ariana, Ben Arous, Manouba.
8 zones de surveillance hypothétiques (2 par gouvernorat).
24 capteurs virtuels (3 par zone : pression, débit, combiné).
Moteur de simulation déterministe :
Module 
simulation_service.py
 simulant un profil de consommation journalier réaliste (pics le matin et en soirée, creux la nuit).
Plages paramétrables : Pression [1.5, 6.0] bar, Débit [50.0, 500.0] m³/h.
Reproductibilité garantie via graine aléatoire (seed).
Marquage systématique et explicite de chaque relevé : data_origin = 'SIMULATED'.
Règles de surveillance (Sprint 1) :
Statuts disponibles : Normal, Données insuffisantes, Inactive.
Tableau de bord Streamlit (en Français) :
Vue d'ensemble : Indicateurs clés (KPIs), compteurs de statuts et récapitulatif par zone avec avertissement clair de données simulées.
Gouvernorats et zones : Fiches détaillées des 4 gouvernorats, zones associées et inventaire des capteurs.
Surveillance des capteurs : Sélection dynamique, dernière mesure et graphiques interactifs Plotly (historique pression et débit).
Données : Tableau filtrable (Gouvernorat, Zone, Capteur) et bouton d'action 🔄 Générer exécutant le simulateur et persistant les nouvelles mesures dans SQLite.
2. Structure finale du projet
text


aquawatch-grand-tunis/
├── app.py
├── requirements.txt
├── .gitignore
├── .env.example
├── README.md
├── DATA_SOURCES.md
├── backend/
│   ├── __init__.py
│   ├── config.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   ├── init_db.py
│   │   ├── schema.sql
│   │   └── seed.sql
│   ├── models/
│   │   ├── __init__.py
│   │   └── measurement.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── governorate_repository.py
│   │   ├── zone_repository.py
│   │   ├── sensor_repository.py
│   │   └── measurement_repository.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── simulation_service.py
│   │   └── monitoring_service.py
│   └── utils/
│       ├── __init__.py
│       └── time_utils.py
├── dashboard/
│   ├── __init__.py
│   ├── overview.py
│   ├── zones.py
│   └── measurements.py
├── data/
│   ├── .gitkeep
│   └── aquawatch.db
├── docs/
│   └── DATA_SOURCES.md
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_database.py
    ├── test_simulation.py
    ├── test_repositories.py
    └── test_monitoring.py
3. Schéma relationnel de la base SQLite
Mermaid diagram
4. Sources de données et transparence
Documentées dans 
DATA_SOURCES.md
 :

Entité	Nature	Source
Gouvernorats (Tunis, Ariana, Ben Arous, Manouba)	✅ Réelle	Découpage administratif officiel tunisien
Population	✅ Réelle (référence)	INS Tunisie — Recensement 2024 / estimations publiques
Limites administratives	✅ Réelle (référence)	OCHA / HDX (data4tunisia.org)
Zones de surveillance	⚠️ Hypothétique	Démonstration académique (non SONEDE)
Capteurs virtuels	⚠️ Simulé	Générés par le projet
Pression & Débit	⚠️ Simulé	Générés en Python (SIMULATED)
5. Résultats de la suite de tests automatisés
Suite exécutée avec pytest -v sur une base temporaire isolée (tmp_path) :

text


============================= test session starts =============================
platform win32 -- Python 3.13.1, pytest-9.0.1, pluggy-1.6.0
collected 56 items
tests/test_database.py (13 tests) .............                       [ 23%]
tests/test_monitoring.py (8 tests) ........                           [ 37%]
tests/test_repositories.py (24 tests) ........................        [ 80%]
tests/test_simulation.py (11 tests) ...........                       [100%]
============================= 56 passed in 9.29s ==============================
100% des 56 tests passent avec succès.

6. Commandes pour exécuter l'application (PowerShell)
Depuis le dossier du projet :

powershell


cd c:\Programs\XAMPP\htdocs\projects\ISAMM\2eme\Python\aquawatch-grand-tunis
# 1. Créer et activer l'environnement virtuel (optionnel si déjà configuré)
python -m venv .venv
.venv\Scripts\Activate.ps1
# 2. Installer les dépendances
pip install -r requirements.txt
# 3. Initialiser la base de données SQLite (déjà effectuée)
python -m backend.database.init_db
# 4. Lancer le tableau de bord Streamlit
streamlit run app.py
# 5. Exécuter la suite de tests
pytest -v
7. Validation des critères d'acceptation du Sprint 1
Critère d'acceptation	Statut	Note de vérification
Projet créé de zéro	✅	Arborescence modulaire et documentée
Structure claire et maintenable	✅	Code propre, typé et documenté sans ORM lourd
Schéma et seed SQL complets	✅	schema.sql et seed.sql opérationnels et idempotents
4 gouvernorats & 8 zones créés	✅	Présents en base et testés
24 capteurs virtuels associés	✅	3 capteurs par zone (pression, débit, combiné)
Simulateur de mesures réaliste	✅	Variations diurnes, pics de consommation, déterministe avec seed
Persistance SQLite	✅	Insertion et requêtage paramétrés
Dashboard Streamlit complet	✅	4 pages : Vue d'ensemble, Zones, Capteurs, Données
Bouton de génération de mesures	✅	Génère et persiste immédiatement en base
Filtres et graphiques Plotly	✅	Filtres hiérarchiques et courbes de pression/débit
Mention explicite des données simulées	✅	Avertissements dans l'UI et champ data_origin en base
Tests automatisés réussis	✅	56 tests passés sans erreur
Documentation complète	✅	README.md et DATA_SOURCES.md complets
Le socle du Sprint 1 est prêt, stable et préparé pour l'introduction future des techniques de concurrence et d'analyse au Sprint 2.


excute le porjet open the dhaborad 
Conformément aux règles de sécurité configurées pour cet environnement, l'agent n'est pas autorisé à lancer lui-même des serveurs de développement ou des applications en arrière-plan (streamlit run, npm run dev, etc.).

Vous pouvez exécuter le tableau de bord directement dans votre terminal PowerShell :

Commande à exécuter dans votre terminal :
powershell


cd c:\Programs\XAMPP\htdocs\projects\ISAMM\2eme\Python\aquawatch-grand-tunis
streamlit run app.py
Accès au tableau de bord :
Une fois la commande lancée, Streamlit ouvrira automatiquement votre navigateur à l'adresse : 👉 http://localhost:8501

Ce que vous pourrez faire immédiatement :
🏠 Vue d'ensemble : Consulter les 4 gouvernorats, les 8 zones de surveillance et les 24 capteurs virtuels.
📋 Données : Cliquer sur le bouton 🔄 Générer pour simuler et enregistrer un premier lot de mesures dans SQLite.
📊 Surveillance des capteurs : Sélectionner un capteur et observer les graphiques interactifs Plotly de pression et de débit.
🗺️ Gouvernorats et zones : Explorer le détail de chaque zone et la liste des capteurs associés.

PS C:\Programs\XAMPP\htdocs\projects\ISAMM\2eme\Python>
PS C:\Programs\XAMPP\htdocs\projects\ISAMM\2eme\Python> cd c:\Programs\XAMPP\htdocs\projects\ISAMM\2eme\Python\aquawatch-grand-tunis
>> streamlit run app.py
streamlit : The term 'streamlit' is not recognized as the name of a cmdlet, function, script file, or operable program. Check 
the spelling of the name, or if a path was included, verify that the path is correct and try again.
At line:2 char:1
+ streamlit run app.py
+ ~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (streamlit:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException

PS C:\Programs\XAMPP\htdocs\projects\ISAMM\2eme\Python\aquawatch-grand-tunis> cd c:\Programs\XAMPP\htdocs\projects\ISAMM\2eme\Python\aquawatch-grand-tunis
PS C:\Programs\XAMPP\htdocs\projects\ISAMM\2eme\Python\aquawatch-grand-tunis> streamlit run app.py
streamlit : The term 'streamlit' is not recognized as the name of a cmdlet, function, script file, or operable program. Check 
the spelling of the name, or if a path was included, verify that the path is correct and try again.
At line:1 char:1
+ streamlit run app.py
+ ~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (streamlit:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException

PS C:\Programs\XAMPP\htdocs\projects\ISAMM\2eme\Python\aquawatch-grand-tunis> 
Vérification en cours des dépendances Python...

Le message d'erreur indique que le dossier Scripts de Python n'est pas enregistré dans votre variable d'environnement PATH Windows, ce qui empêche PowerShell de trouver directement la commande streamlit.

Toutes les dépendances (Streamlit 1.50, Pandas, Plotly, Pytest) sont bien installées et fonctionnelles.

Pour lancer le tableau de bord sans problème de PATH, utilisez la syntaxe de module Python :

powershell


python -m streamlit run app.py
Étapes dans votre terminal PowerShell :
Assurez-vous d'être dans le dossier du projet :
powershell


cd c:\Programs\XAMPP\htdocs\projects\ISAMM\2eme\Python\aquawatch-grand-tunis
Lancez Streamlit via Python :
powershell




```powershell
# Accéder au dossier du projet
cd aquawatch-grand-tunis

# Créer l'environnement virtuel
python -m venv .venv

# Activer l'environnement virtuel
.venv\Scripts\Activate.ps1
```

*(Si l'exécution de scripts PowerShell est restreinte sur votre machine, exécutez au préalable : `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### 5.2 Installation des dépendances

```powershell
pip install -r requirements.txt
```

### 5.3 Initialisation de la base de données

Initialisez la base de données SQLite avec le schéma et les données initiales :

```powershell
python -m backend.database.init_db
```

Sortie attendue :
```text
✅ Base de données initialisée : ...\data\aquawatch.db
   📍 4 gouvernorats
   🗺️  8 zones de surveillance
   📡 24 capteurs virtuels
```

*(Note : ce script est idempotent ; vous pouvez le relancer plusieurs fois sans dupliquer les données grâce aux clauses `INSERT OR IGNORE`).*

### 5.4 Lancement du tableau de bord Streamlit

```powershell
streamlit run app.py
```

L'application s'ouvrira automatiquement dans votre navigateur par défaut (généralement à l'adresse `http://localhost:8501`).

---

## 6. Exécution des tests automatisés

Le projet comprend une suite complète de tests unitaires et d'intégration validant le schéma, l'idempotence, les repositories, le simulateur et le service de surveillance.

Les tests utilisent une base temporaire SQLite (`tmp_path`) pour ne jamais altérer la base de production.

Pour exécuter la suite de tests :

```powershell
pytest -v
```

---

## 7. Inspection de la base de données SQLite

La base de données créée réside dans `data/aquawatch.db`. Vous pouvez l'inspecter de plusieurs façons :

### Via un utilitaire graphique
- Téléchargez et ouvrez **[DB Browser for SQLite](https://sqlitebrowser.org/)**, puis ouvrez le fichier `data/aquawatch.db`.

### Via la CLI SQLite ou Python en ligne de commande
```powershell
python -c "import sqlite3; conn=sqlite3.connect('data/aquawatch.db'); print('Mesures en base :', conn.execute('SELECT COUNT(*) FROM measurements').fetchone()[0])"
```

### Migration Sprint 2 : Alertes et état de surveillance

Le Sprint 2 ajoute les tables `alerts` et `monitoring_states` sans altérer les 1 152 mesures ni les 24 capteurs existants :

```powershell
python -m backend.database.migrate_sprint2_alerts
```

Le script crée une sauvegarde horodatée validée par `PRAGMA integrity_check` avant d'appliquer le schéma de façon transactionnelle et idempotente.

---

## 8. Détails d'implémentation du Sprint 2

### 8.1 Surveillance au niveau zone & Politique de repli
Chaque zone dispose de 3 capteurs virtuels : un capteur dédié de pression, un capteur dédié de débit, et un capteur combiné.
- **Pression** : La surveillance privilégie la dernière mesure valide du capteur dédié. Si celui-ci est défaillant, absent, invalide ou obsolète (> 24h), le système bascule automatiquement sur la mesure de pression du capteur combiné en repli.
- **Débit** : Règle symétrique privilégiant le capteur dédié de débit avec repli automatique sur le capteur combiné.
- Les capteurs ne sont **jamais moyennés** et le capteur combiné n'est **jamais doublement comptabilisé**.

### 8.2 Seuils de détection configurables
Centralisés dans `backend/config.py` :
- **Pression basse** : `pressure_bar <= 1.5` bar
- **Débit bas** : `flow_m3_h <= 50.0` m³/h
- **Condition A (Pression faible)** : Pression <= 1.5 bar sur 3 lectures consécutives (`WARNING`).
- **Condition B (Débit faible)** : Débit <= 50.0 m³/h sur 3 lectures consécutives (`WARNING`).
- **Condition C (Interruption possible)** : Pression et débit anormalement bas simultanément sur 3 lectures consécutives (`CRITICAL`).

### 8.3 Validation par 3 lectures consécutives & Idempotence
- Une seule anomalie isolée ne déclenche **aucune alerte**.
- 3 lectures distinctes consécutives anormales sont requises.
- Une lecture normale réinitialise immédiatement le compteur à 0 (règle de rétablissement).
- Le suivi est basé sur les identifiants uniques de mesure (`last_processed_measurement_id`) stockés dans `monitoring_states`. Exécuter plusieurs fois la surveillance contre les mêmes données est **strictement idempotent**.

### 8.4 Qualité des données & Fraîcheur
- **Données manquantes** : Aucune mesure n'est jamais interprétée comme 0. Statut affiché : `Données insuffisantes`.
- **Données invalides** : Tout relevé avec `quality_status != 'valid'` est ignoré par l'analyse et n'incrémente pas les compteurs anormaux.
- **Données obsolètes** : Tout relevé de plus de 24h est marqué `Données anciennes` et ne génère aucune fausse alerte.

### 8.5 Cycle de vie et persistance des alertes
- Les alertes sont créées dans la table `alerts` avec les statuts `ACTIVE` et `RESOLVED`.
- Lorsque pression et débit sont tous deux anormaux, une alerte `POSSIBLE_INTERRUPTION` (`CRITICAL`) est créée et résout les alertes individuelles pour éviter les doublons contradictoires.
- Lors du retour à la normale, l'alerte active est résolue (`status = 'RESOLVED'`, `resolved_at = horodatage`) et conservée dans l'historique sans écrasement.

---

## 9. Scénario de démonstration du Sprint 2

1. **Lancer le dashboard Streamlit** :
   ```powershell
   streamlit run app.py
   # ou via python si streamlit n'est pas dans le PATH :
   python -m streamlit run app.py
   ```
2. **🏠 Vue d'ensemble** :
   - Observer les 6 indicateurs de synthèse (Total zones, Normales, Données insuffisantes, Avertissements, Interruptions, Alertes actives).
   - Les états sont lus depuis les dernières mesures traitées automatiquement; le dashboard ne déclenche plus de nouvelle évaluation.
3. **🗺️ Gouvernorats et zones** :
   - Déplier les zones pour consulter les métriques représentatives en bar et m³/h, le statut individuel, et l'indicateur de repli sur capteur combiné.
4. **🚨 Alertes & Incidents** :
   - Visualiser les alertes actives et l'historique résolu avec filtres par gouvernorat, zone, statut et sévérité.
   - Ouvrir la section dépliante **🧪 Démonstration de scénarios d'anomalies (SIMULATION)** :
     - Sélectionner une zone cible (ex: `TUN-Z1`).
     - Choisir le scénario : `🔴 Interruption possible` ou `🟠 Pression faible seule`.
     - Cliquer sur **⚡ Injecter le scénario** : 3 mesures anormales simulées sont créées et traitées automatiquement par la couche de persistance.
     - Constater l'apparition de l'alerte critique ou d'avertissement.
     - Sélectionner ensuite le scénario `🟢 Rétablissement normal` et cliquer sur **⚡ Injecter le scénario** : constater la résolution automatique de l'alerte et son transfert dans l'historique des incidents résolus.
5. **📊 Surveillance des capteurs** :
   - Observer les lignes de seuil horizontales en pointillés rouges (1.5 bar) et orange (50 m³/h) sur les graphiques Plotly.

---

## 10. Limites connues et périmètre du Sprint 2

Conformément au cahier des charges :
- **Prototype académique** : toutes les mesures sont simulées (`data_origin = 'SIMULATED'`).
- **Aucune intégration physique SONEDE**.

---

## 11. Sprint 3 — Collecte asynchrone avec asyncio

Sprint 3 ajoute une démonstration académique de concurrence asynchrone avec le module
[`async_sensor_service.py`](backend/services/async_sensor_service.py) :

- `collect_sequential()` attend la latence simulée pour chaque capteur avant de passer au suivant.
- `collect_async()` crée une tâche pour chaque capteur et les attend avec `asyncio.gather()`.
- Les tâches utilisent `asyncio.sleep()` pour représenter une latence réseau simulée.
- Les résultats sont retournés une fois, puis sauvegardés par `measurement_repository.insert_many()`.
- La sauvegarde déclenche automatiquement le traitement Sprint 2 via le mécanisme existant.

Le benchmark est disponible dans [`benchmark_service.py`](backend/services/benchmark_service.py).
Il utilise `time.perf_counter()` et calcule le speedup par
`temps séquentiel / temps asyncio`. Les résultats utilisent la médiane de plusieurs
répétitions. Le benchmark ne modifie pas la base de données.

Commande Python de démonstration avec les capteurs actifs :

```powershell
python -c "from backend.database.connection import get_connection; from backend.repositories import sensor_repository; from backend.services.benchmark_service import run_benchmark; c=get_connection(); s=sensor_repository.get_active(c); print(run_benchmark([{'sensors':s[:n]} for n in (4,8,16,24)], 0.05, 3, 42)); c.close()"
```

Dans le tableau de bord, la page de collecte permet de choisir le nombre de capteurs,
la latence simulée et le nombre de répétitions. Le benchmark ne persiste pas les mesures.

**Concurrence** : plusieurs tâches progressent pendant des périodes qui se chevauchent.
**Asynchronisme** : `asyncio` suspend les tâches pendant l'attente simulée et réactive
d'autres tâches sur la boucle d'événements. **Parallélisme** : plusieurs opérations CPU
s'exécutent simultanément. Sprint 3 démontre la concurrence asynchrone, pas le parallélisme
CPU ni des communications avec des capteurs réels.

---

## 12. Sprint 4 — Collecte multithread et comparaison des stratégies

Sprint 4 ajoute une collecte bloquante multithread dans
[`threaded_sensor_service.py`](backend/services/threaded_sensor_service.py).
Le tableau de bord compare désormais séquentiel, asyncio et multithreading.

### Architecture et sécurité des données

- Chaque worker exécute une opération de collecte simulée avec `time.sleep()` et
  génère la mesure avec le simulateur existant. Les identifiants, les types de
  mesures et les horodatages restent ceux du modèle AquaWatch.
- `ThreadPoolExecutor` limite le nombre de threads (1 à 32 côté service, jusqu'à
  8 dans l'interface). Les tâches renvoient les mesures, leur durée, le nom et
  l'identifiant du thread; les erreurs individuelles sont rapportées avec le
  capteur concerné.
- Les workers ne partagent pas la connexion SQLite et ne modifient pas de
  collections partagées. Le thread appelant rassemble les résultats puis appelle
  `measurement_repository.insert_many()`, qui conserve la transaction et le
  traitement de surveillance/alertes existants.
- Une entrée contenant deux fois le même identifiant de capteur est rejetée pour
  éviter de créer plusieurs mesures pour ce capteur dans une même collecte.

Un **processus** possède son propre espace mémoire et peut contenir plusieurs
**threads**, qui partagent la mémoire du processus. Le pool réutilise et borne ces
threads au lieu de créer un thread non contrôlé par capteur. Pour cette simulation
d'attente d'entrée-sortie, un worker peut dormir pendant qu'un autre avance.

`asyncio` coordonne des coroutines sur une boucle d'événements et nécessite des
opérations asynchrones (`async`/`await`). Les threads permettent ici d'exécuter
plusieurs opérations bloquantes dans un pool. Dans CPython standard, le **GIL**
(Global Interpreter Lock) limite généralement l'exécution simultanée de bytecode
Python dans un même interpréteur : le multithreading convient à l'attente
d'entrée-sortie, mais n'accélère généralement pas un calcul CPU pur. Le
multiprocessing pourra traiter ce dernier cas dans un sprint ultérieur; il n'est
pas inclus dans Sprint 4.

### Benchmark et démonstration

Le benchmark passe la même liste de capteurs, le même délai, la même graine et le
même horodatage aux trois stratégies pour chaque répétition. Il mesure seulement
la collecte avec `time.perf_counter()`; les écritures SQLite et le rendu du
tableau de bord sont exclus. Les durées affichées sont les moyennes des
répétitions. Pour chaque comparaison, le tableau et les graphiques présentent
durée, speedup, temps économisé, amélioration en pourcentage, résultats réussis
et échecs. Les tailles de pool sont comparables, et une augmentation du nombre
de threads n'est pas présumée améliorer le temps.

Exemple de benchmark sans persistance, sur les mêmes 8 capteurs et avec des pools
de 1, 2 et 4 threads :

```powershell
python -c "from backend.database.connection import get_connection; from backend.repositories import sensor_repository; from backend.services.benchmark_service import run_benchmark; c=get_connection(); s=sensor_repository.get_active(c)[:8]; print(run_benchmark([{'sensors':s}], 0.05, 3, 42, [1,2,4])); c.close()"
```

Exemple de résultat réellement mesuré dans l'environnement local (Windows,
Python 3.13.1), avec 8 capteurs, 20 ms de latence simulée, graine 42 et 3
répétitions. Les durées sont des moyennes; les 8 mesures ont réussi dans chaque
stratégie et chaque essai.

| Workers | Séquentiel (s) | Asyncio (s) | Multithreading (s) | Speedup asyncio | Speedup threads |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.2481 | 0.0316 | 0.1659 | 7.85x | 1.50x |
| 2 | 0.2408 | 0.0319 | 0.0842 | 7.54x | 2.86x |
| 4 | 0.2474 | 0.0320 | 0.0446 | 7.72x | 5.54x |
| 8 | 0.2462 | 0.0315 | 0.0282 | 7.82x | 8.74x |

Dans cette exécution précise, augmenter le nombre de workers a réduit le temps
observé pour la collecte simulée bloquante. Ce résultat n'est pas une garantie
pour d'autres tailles de pool, machines ou charges : les timings locaux varient
selon l'ordonnanceur et la charge système.

Pour lancer la page intégrée, utilisez `streamlit run app.py`; sélectionnez une
stratégie et cliquez sur **Exécuter et enregistrer** pour persister les mesures
dans le pipeline existant. Le bouton **Comparer les stratégies** lance des essais
sans écriture en base. Les tests Sprint 4 se lancent avec :

```powershell
python -m pytest -q
```

## 13. Sprint 5 — Multiprocessing pour l'analyse CPU

Le multiprocessing exécute des calculs dans plusieurs processus, chacun avec
son propre interpréteur Python. Il est utile pour paralléliser des tâches
intensives en calcul, contrairement aux threads qui restent limités par le GIL
pour le bytecode Python. AquaWatch estime de façon déterministe les pertes
d'eau de zones de démonstration, puis compare le résultat séquentiel aux pools
de 1, 2 et 4 processus. Le lancement et le transfert des données ont un coût :
un pool de processus n'est pas toujours plus rapide.

Lancez `streamlit run app.py`, ouvrez **Collecte asynchrone**, puis choisissez
**Multiprocessing** dans la section d'analyse CPU. Le bouton de comparaison
mesure le séquentiel et les trois tailles de pool. Pour exécuter les tests Sprint
5 : `python -m pytest -q tests/test_sprint5_multiprocessing.py`; la suite
complète se lance avec `python -m pytest -q`.

## 14. Sprint 6 — Dask Distributed

Dask Distributed planifie les analyses indépendantes de chaque zone sur un
cluster local, avec un processus par worker. Le service réutilise le calcul
déterministe de Sprint 5; les workers exécutent leurs tâches sur la même
machine, et non sur plusieurs ordinateurs. Le client et le cluster sont fermés
après chaque analyse.

Dans **Collecte asynchrone**, sélectionnez **Dask Distributed**, choisissez le
nombre de workers et lancez l'analyse. Le benchmark compare les résultats
séquentiels, multiprocessing et Dask pour plusieurs tailles de pool. Le
démarrage du cluster et la planification ont un coût, donc Dask n'est pas
toujours plus rapide pour les petites charges.

Installez les dépendances avec `python -m pip install -r requirements.txt`.
Lancez les tests Sprint 6 avec
`python -m pytest -q tests/test_sprint6_dask.py`.
