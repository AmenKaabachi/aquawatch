# Sources de données — AquaWatch Grand Tunis

Ce document identifie toutes les sources de données utilisées par le projet,
distingue les données réelles des données simulées, et documente les
limitations et hypothèses.

---

## 1. Données contextuelles réelles

### 1.1 Institut National de la Statistique de Tunisie (INS)

| Élément | Détail |
|---|---|
| **Source** | Recensement de la population et de l'habitat 2024 |
| **URL** | https://www.ins.tn/enquetes/population-and-housing-census-2024 |
| **Informations fournies** | Population par gouvernorat, indicateurs de raccordement au réseau d'eau |
| **Utilisation dans le projet** | Chiffres de population approximatifs pour les 4 gouvernorats du Grand Tunis |
| **Nature** | ✅ Données réelles de référence |
| **Limitations** | Les chiffres utilisés sont des valeurs approximatives issues de sources publiques. Les données officielles détaillées du recensement 2024 doivent être consultées directement sur le site de l'INS pour obtenir les valeurs exactes. |

### 1.2 Statistiques de population INS

| Élément | Détail |
|---|---|
| **Source** | Statistiques démographiques INS |
| **URL** | https://www.ins.tn/en/statistiques/111 |
| **Informations fournies** | Population par gouvernorat (séries historiques) |
| **Utilisation dans le projet** | Référence complémentaire pour les données de population |
| **Nature** | ✅ Données réelles de référence |

### 1.3 Limites administratives de la Tunisie

| Élément | Détail |
|---|---|
| **Source** | OCHA / HDX — Tunisia subnational administrative boundaries |
| **URL** | https://www.data4tunisia.org/datasets/cod-ab-tun |
| **Informations fournies** | Découpage administratif (gouvernorats, délégations) |
| **Utilisation dans le projet** | Référence pour la géographie administrative du Grand Tunis |
| **Nature** | ✅ Données réelles de référence |
| **Limitations** | Non téléchargé ni intégré automatiquement. Utilisé comme référence documentaire uniquement. |

---

## 2. Données simulées

### 2.1 Zones de surveillance

| Élément | Détail |
|---|---|
| **Source** | Configuration du projet AquaWatch |
| **Nature** | ⚠️ **Hypothétique** |
| **Description** | 8 zones de surveillance réparties sur les 4 gouvernorats (2 par gouvernorat). Ces zones sont des emplacements de démonstration et ne correspondent pas à des installations vérifiées du réseau SONEDE. |

### 2.2 Capteurs virtuels

| Élément | Détail |
|---|---|
| **Source** | Simulateur Python AquaWatch |
| **Nature** | ⚠️ **Simulé** |
| **Description** | 24 capteurs virtuels (3 par zone). Types : pression, débit, combiné. Aucune connexion à du matériel physique. |

### 2.3 Mesures de pression

| Élément | Détail |
|---|---|
| **Source** | `backend/services/simulation_service.py` |
| **Nature** | ⚠️ **Simulé** |
| **Plage** | 1,5 — 6,0 bar |
| **Statut des valeurs** | Plage illustrative de simulation, non officielle et non assimilable à un seuil SONEDE |
| **Profil** | Variation journalière avec baisses aux heures de pointe (6h-9h, 17h-21h) |
| **Reproductibilité** | Déterministe avec graine aléatoire configurable |

### 2.4 Mesures de débit

| Élément | Détail |
|---|---|
| **Source** | `backend/services/simulation_service.py` |
| **Nature** | ⚠️ **Simulé** |
| **Plage** | 50 — 500 m³/h |
| **Statut des valeurs** | Plage illustrative de simulation, non officielle et non assimilable à un seuil SONEDE |
| **Profil** | Consommation urbaine typique : pics matin/soir, creux nocturne |
| **Reproductibilité** | Déterministe avec graine aléatoire configurable |

---

## 3. Récapitulatif

| Donnée | Source | Nature |
|---|---|---|
| Gouvernorats | INS Tunisie | ✅ Réelle |
| Population | INS recensement 2024 | ✅ Réelle (approximative) |
| Limites administratives | OCHA / data4tunisia | ✅ Réelle (référence) |
| Zones de surveillance | Configuration projet | ⚠️ Hypothétique |
| Capteurs | Simulateur Python | ⚠️ Simulé |
| Mesures de pression | Simulateur Python | ⚠️ Simulé |
| Mesures de débit | Simulateur Python | ⚠️ Simulé |

---

## 4. Avertissement important

> **Ce projet est un prototype académique.**
> Les mesures de pression et de débit sont entièrement générées par un
> simulateur Python. Elles ne proviennent pas de capteurs réels et ne
> doivent en aucun cas être présentées comme des mesures opérationnelles
> collectées par la SONEDE ou tout autre organisme.
>
> Les chiffres de population utilisés sont des valeurs approximatives
> tirées de sources publiques. Pour des données officielles exactes,
> consulter directement le site de l'INS :
> https://www.ins.tn/enquetes/population-and-housing-census-2024

Chaque zone dispose d'un capteur virtuel de pression, d'un capteur virtuel de débit et d'un capteur combiné qui mesure les deux variables. Une mesure non prise en charge par un capteur est stockée en `NULL` : cela signifie « non mesuré », et non une valeur égale à zéro.
