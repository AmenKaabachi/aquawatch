# AquaWatch Grand Tunis — Sprint 1 : Socle du Projet

**AquaWatch Grand Tunis** est une application académique de simulation et de surveillance de l'approvisionnement en eau potable à travers les quatre gouvernorats du Grand Tunis.

Ce projet s'inscrit dans le cadre du cours **Systèmes Parallèles et Distribués** (ISAMM, 2ème année). À terme, l'application servira de support pour démontrer des techniques de programmation concurrente et distribuée en Python.

---

## 1. Objectifs du Sprint 1

Le Sprint 1 met en place le socle fonctionnel, architectural et persistant du projet sans introduire de complexité superflue (pas de microservices, d'ORM lourd ou de conteneurisation prématurée) :

- **Structure géographique** : 4 gouvernorats du Grand Tunis et 8 zones de surveillance hypothétiques (2 par gouvernorat).
- **Capteurs virtuels** : 24 capteurs (pression, débit, combiné) rattachés aux zones de surveillance.
- Chaque zone possède un capteur de pression, un capteur de débit et un capteur combiné, ce dernier représentant un seul appareil virtuel qui mesure les deux variables.
- Les mesures non prises en charge par un capteur sont stockées en `NULL` (et affichées comme indisponibles), jamais comme zéro. Toutes les mesures sont simulées.
- **Simulateur de mesures** : Générateur déterministe et réaliste de mesures de pression (bar) et de débit (m³/h).
- **Statut de surveillance** : Indicateurs initiaux (`Normal`, `Données insuffisantes`, `Inactive`).
- **Base de données relationnelle** : SQLite avec tables, clés étrangères activées, index et scripts SQL dédiés (`schema.sql`, `seed.sql`).
- **Tableau de bord Streamlit** : Interface en français avec indicateurs clés, fiches gouvernorats/zones, visualisations graphiques Plotly et table filtrable avec déclenchement manuel de génération de mesures.
- **Tests automatisés** : Suite complète avec `pytest` isolée sur base temporaire.

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

### Migration des mesures par type de capteur

Chaque zone possède un capteur de pression, un capteur de débit et un capteur combiné (un appareil virtuel qui mesure les deux). Les colonnes non mesurées sont stockées comme `NULL`, et non comme zéro. Après sauvegarde, la migration peut être lancée avec :

```powershell
python -m backend.database.migrate_sensor_measurements
```

Le script crée et vérifie une sauvegarde horodatée avant d'effectuer une migration transactionnelle. Les plages de simulation configurées sont illustratives et ne sont pas des seuils officiels de la SONEDE.

---

## 8. Scénario de démonstration (Sprint 1)

1. **Initialiser la base** : `python -m backend.database.init_db`
2. **Lancer le dashboard** : `streamlit run app.py`
3. **🏠 Vue d'ensemble** :
   - Constater les 4 gouvernorats, 8 zones, 24 capteurs et l'avertissement de simulation.
   - Constater que les zones sont initialement à l'état `Données insuffisantes`.
4. **🗺️ Gouvernorats et zones** :
   - Consulter la hiérarchie des 4 gouvernorats et déployer les fiches des zones pour voir le détail des capteurs.
5. **📋 Données** :
   - Cliquer sur le bouton **🔄 Générer** pour simuler un premier lot de mesures.
   - Constater l'apparition des mesures dans la table et tester les filtres par gouvernorat, zone et capteur.
6. **📊 Surveillance des capteurs** :
   - Sélectionner un capteur et observer les graphiques Plotly retraçant l'historique de pression et de débit.
7. **Retour à la Vue d'ensemble** :
   - Constater que le statut des zones est désormais passé à `🟢 Normal` suite à l'acquisition des données simulées.
8. **Persistance** :
   - Actualiser le navigateur : toutes les données générées restent stockées dans SQLite.

---

## 9. Limites connues et périmètre du Sprint 1

Conformément au cahier des charges de la phase 1 :
- **Pas d'alertes temps-réel ni de détection automatique d'interruption** : ces règles seront introduites au Sprint 2.
- **Pas de parallélisme / concurrence (multiprocessing, multithreading, asyncio)** : l'architecture a été conçue pour brancher ces modules ultérieurement sans modifier l'interface.
- **Capteurs virtuels** : aucun matériel physique n'est raccordé.
