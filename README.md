<center>
   <h1>Application à la Démarche Scientifique : Simulation de Microservices</h1>
   <p>Projet de simulation de microservices pour l'Application à la Démarche Scientifique</p>
   <p>Alban GODIER - Étudiant à CESI École d'ingénieur</p>
   <p>13/05/2026</p>
</center>

> [!WARNING]
> Ce projet est massivement "vibe codé" (c'est à dire que le code a été écrit majoritaire par un outil IA, en l'occurence, Github Copilot). Par conséquent, je recommande fortement de ne pas se baser sur ce projet. En effet, je ne connais pas tous les détails de son implémentation, et il est fort probable que le code contienne des erreurs, des incohérences, ou des choix d'implémentation discutables. De plus, le code généré par une IA peut être difficile à comprendre et à maintenir, surtout si vous n'avez pas une connaissance approfondie du projet.
>
> J'ai réalisé ce projet dans le cadre d'un module d'enseignement en école d'ingénieur, et il a été conçu trop rapidement et principalement pour illustrer des concepts et des idées, plutôt que pour être utilisé comme une base de code solide.
>
> Je ne m'attribue pas la paternité du code, et je ne peux pas garantir sa qualité ou sa fiabilité. Si vous souhaitez utiliser ce projet comme référence, je vous encourage à l'examiner attentivement, à comprendre son fonctionnement, et à le modifier ou l'améliorer selon vos besoins.

---

# Application à la Démarche Scientifique : Simulation de Microservices

Ce projet est la partie simulation de l'**Application à la Démarche Scientifique**, un module d'enseignement en école d'ingénieur dont l'objectif est de découvrir le processus de recherche scientifique.

## Titre de Recherche

**Influence de la granularité des microservices et de leur déploiement conteneurisé sur les performances d'une application distribuée simulée**

## Problèmatique

Dans une architecture microservices déployée en conteneurs, **comment la variation du niveau de granularité et de la distribution des services influence-t-elle les performances globales du système** (latence, temps de réponse, charge CPU, taux d'échec) ?

## Résumé de Recherche

La granularité des microservices et le mode de déploiement conteneurisé sont deux paramètres architecturaux majeurs dont l'impact combiné sur les performances reste peu étudié en simulation contrôlée. Cette étude évalue **six configurations architecturales** issues du croisement de trois niveaux de granularité et deux modes d'isolation conteneurisée, testées sur **dix applications distribuées générées aléatoirement** sous **sept niveaux de charge**.

Les résultats montrent que :

- **L'isolation conteneurisée est le facteur déterminant à forte charge**, réduisant la latence et les échecs au prix d'une consommation CPU élevée
- Un **découplage inattendu existe entre utilisation CPU et latence** selon le mode de déploiement
- Les configurations présentent des profils de performance distincts selon le niveau de charge

## Architecture Conceptuelle

L'architecture simulée se compose de trois niveaux :

- **Microservices** : Unités de travail individuelles exécutant une tâche de calcul simple (20 000 itérations de division euclidienne) représentative d'une charge réelle
- **Services** : Regroupements de microservices exposant une fonctionnalité via une API HTTP multi-threadée
- **Conteneurs** : Isolation matérielle et logicielle hébergeant un ou plusieurs services, avec limits CPU configurables

Les microservices communiquent selon un **graphe de dépendances généré aléatoirement**, avec un **point d'entrée unique** recevant les requêtes HTTP de test.

---

# Méthodologie

## Conception Expérimentale

Trois dimensions structurent l'expérimentation :

### 1. Niveau de Granularité (3 niveaux)

- **Fine** : Chaque microservice s'exécute dans un service dédié (maximum d'isolation logique)
- **Moyenne** : Plusieurs microservices (entre 1 et 4) regroupés dans un même service
- **Grossière** : Tous les microservices regroupés dans un seul service (monolith)

### 2. Isolation Conteneurisée (3 niveaux)

- **Nulle** : Un conteneur unique regroupant tous les services (application monolithique)
- **Moyenne** : Plusieurs conteneurs regroupant entre 1 et 4 services
- **Forte** : Un conteneur par service (isolement maximal)

### 3. Six Configurations Étudiées

Les combinaisons possibles et testées :

| #   | Granularité | Isolation | Description                                          |
| --- | ----------- | --------- | ---------------------------------------------------- |
| 1   | Fine        | Nulle     | Microservices multiples dans un seul conteneur       |
| 2   | Moyenne     | Nulle     | Services moyens dans un seul conteneur               |
| 3   | Grossière   | Nulle     | Monolithe dans un seul conteneur                     |
| 4   | Moyenne     | Moyenne   | Services moyens distribués dans plusieurs conteneurs |
| 5   | Grossière   | Moyenne   | Services grossiers dans plusieurs conteneurs         |
| 6   | Grossière   | Forte     | Chaque service dans un conteneur dédié               |

## Environnement de Simulation

- **Conteneurisation** : Docker (v29.4.0) et Docker Compose (v5.1.2)
- **Runtime** : Python (v3.10+) avec serveurs HTTP multi-threadés
- **Orchestration** : Docker Compose pour déploiement rapide et collecte de métriques
- **Charge de Travail** : Chaque microservice effectue 20 000 itérations de division euclidienne
- **Plateforme d'Exécution** : Ordinateur personnel sous Windows 11

## Variables et Scénarios

### Charge de Travail (7 niveaux)

Les expériences sont menées sous des niveaux croissants de charge :

```
1, 5, 10, 50, 100, 500, 1 000, 5 000 requêtes simultanées
```

### Applications Générées

**10 applications distribuées aléatoires** contenant chacune :

- 12 microservices
- Graphe de dépendances aléatoires (chaque service appelle d'autres services)
- 1 point d'entrée unique recevant les requêtes HTTP

Total : **60 configurations testées** (10 applications × 6 configurations)

## Mesures et Métriques

Trois métriques principales sont collectées pour chaque expérience :

### 1. Latence Moyenne (ms)

- Temps de réponse moyen des requêtes HTTP
- Mesuré côté client par les scripts de test
- Reflète le temps total pour traiter une requête complète (incluant tous les appels inter-services)

### 2. Taux d'Échec (%)

- Pourcentage de requêtes ayant échoué
- Inclut timeouts, erreurs serveur (5xx), et autres défaillances
- Indicateur de fiabilité et de saturation système

### 3. Utilisation CPU Moyenne par Conteneur (%)

- Mesurée via `docker stats` en temps réel
- Reflète la charge système liée à la configuration architecturale
- Évalue l'efficacité de ressource

## Procédure d'Exécution

L'expérimentation se déroule en trois phases :

### Phase 1 : Préparation (Génération de Configurations)

**Objectif** : Générer l'architecture expérimentale complète

**Commande** :

```bash
python -m src generate-configs --output ./.output --count 10
```

**Résultat** : Arborescence organisée comme suit :

```
.output/
├── 001/  # Application 1
│   ├── 1_monolithic/
│   │   ├── config.json
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── requirements.txt
│   │   ├── runtime_runner.py
│   │   └── src/ ...
│   ├── 2_microservices_medium_granularity/ ...
│   ├── 3_microservices_fine_granularity/ ...
│   ├── 4_microservices_medium_granularity_isolation/ ...
│   ├── 5_microservices_fine_granularity_isolation/ ...
│   └── 6_microservices_fine_granularity_high_isolation / ...
├── 002/ ...
└── 010/ ...
```

Chaque sous-dossier contient :

- `config.json` : Configuration de l'application (dépendances, architecture)
- `docker-compose.yml` : Orchestration Docker
- `Dockerfile` : Définition de l'image
- `runtime_runner.py` : Code d'exécution des serveurs HTTP
- `src/` : Implémentation des services et microservices

### Phase 2 : Exécution des Tests

**Objectif** : Exécuter toutes les configurations sous différentes charges et collecter les métriques

**Commande** :

```bash
python -m src test-all --output ./.output --requests "1;5;10;50;100;500;1000;5000" --missing
```

**Résultat** : Fichiers CSV de résultats pour chaque configuration et niveau de charge

```
1_monolithic/
├── result_1.csv
├── result_5.csv
├── result_10.csv
├── result_50.csv
├── result_100.csv
├── result_500.csv
├── result_1000.csv
└── result_5000.csv
```

Chaque fichier `result_X.csv` contient :

- Latence moyenne (ms)
- Taux d'échec (%)
- Utilisation CPU moyenne (%)

### Phase 3 : Agrégation et Analyse des Données

**Génération de graphiques** :

```bash
python -m src plot-results --output .output
```

**Mode par défaut** (6 graphiques en lignes) :

- Un graphique par configuration architecturale
- Comparaison des 3 métriques en fonction du nombre de requêtes

**Mode par métriques** (3 graphiques en barres) :

```bash
python -m src plot-results --output .output --plot-type bar
```

- Un graphique par métrique
- 6 barres combinées par nombre de requêtes (une par configuration)

---

# Hypothèses de Recherche

## H1 : Impact des Communications Réseau (Granularité Fine)

**Énoncé** : Une granularité fine des microservices augmente le nombre de communications inter-services, entraînant une augmentation de la latence et du temps de réponse global du système.

**Justification** :

- Plus de microservices → plus de services distincts
- Plus de services → plus d'appels réseau inter-service
- Plus d'appels → surcharge de communication et overhead protocolaire

**Prédiction** :

- Latence significativement plus élevée
- Utilisation réseau augmentée
- Dégradation progressive avec l'augmentation de la charge

---

## H2 : Réduction des Surcoûts (Granularité Grossière)

**Énoncé** : Une granularité grossière réduit le nombre de communications inter-services et améliore les performances globales du système en diminuant la latence et la charge réseau.

**Justification** :

- Moins de services → moins de communications réseau
- Communication intra-processus plus rapide que réseau
- Moins d'overhead protocolaire

**Prédiction** :

- Latence réduite à charge faible/modérée
- Meilleure utilisation des ressources
- Scalabilité limitée à forte charge

---

## H3 : Existence d'un Compromis Optimal

**Énoncé** : Un niveau de granularité intermédiaire permet d'obtenir un compromis optimal entre modularité du système et performances globales.

**Justification** :

- Granularité fine : scalabilité mais surcharge réseau
- Granularité grossière : faible latence mais complexité interne
- Granularité moyenne : équilibre des deux facteurs

**Prédiction** :

- Performances intermédiaires mais stables
- Meilleur ratio latence/scalabilité
- Robustesse à différents niveaux de charge

---

## H4 : Impact du Déploiement Conteneurisé

**Énoncé** : L'isolation conteneurisée (déploiement multi-conteneurs) augmente les coûts de communication inter-processus et peut dégrader les performances par rapport à une exécution monolithique.

**Justification** :

- Virtualisation et isolation ont un coût
- Communication inter-conteneurs via réseau Docker
- Overhead de gestion de conteneurs

**Prédiction** :

- Latence plus élevée en multi-conteneur
- Consommation CPU augmentée
- Impact croissant avec le nombre de conteneurs

---

## H5 : Influence de la Charge Système

**Énoncé** : L'impact de la granularité et de l'isolation sur les performances devient plus significatif lorsque la charge du système augmente.

**Justification** :

- Faible charge : ressources suffisantes pour tous les niveaux
- Forte charge : saturation ressource et contention
- Amplification des différences architecturales

**Prédiction** :

- Différences mineures à faible charge
- Divergence progressive avec augmentation de charge
- Configurations montrent des seuils de saturation différents

---

# Démarrage Rapide

## Prérequis

- Python 3.10+
- Docker et Docker Compose (pour simulations Docker)
- 4GB RAM minimal, 8GB recommandé

## Installation

```bash
# Créer un environnement virtuel
python -m venv .venv

# Activer l'environnement
# Windows :
.venv\Scripts\activate
# Linux/macOS :
source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

## Exécutions Rapides

### Simulation Python Simple (Threads)

```bash
python -m src.Python.main --config config-test.json --requests 200 --workers 2
```

**Options** :

- `--requests` : Nombre de requêtes par service
- `--workers` : Nombre de threads pour exécution parallèle
- `--output` : Fichier de sortie JSON

**Exemple complet** :

```bash
python -m src.Python.main --config config-test.json --requests 500 --workers 4 --output results.json
```

### Générer une Configuration Docker

```bash
python -m src build --config config-test.json --output .output
```

### Exécuter la Configuration Docker Générée

```bash
python -m src run --output .output
```

### Tester la Configuration Docker

```bash
python -m src test --output .output --requests 10
```

### Arrêter les Conteneurs

```bash
python -m src stop --output .output
```

## Workflow Complet : Générer et Tester 10 Applications

```bash
# Phase 1 : Générer 10 applications avec 6 configurations chacune
python -m src generate-configs --count 10 --output .output

# Phase 2 : Exécuter tous les tests
python -m src test-all --output .output --requests "1;5;10;50;100;500;1000;5000"

# Phase 3 : Générer les graphiques
python -m src plot-results --output .output
```

Les résultats seront disponibles dans `.output/` avec graphiques PNG et données CSV brutes.

---

# Logging et Débogage

## Configuration du Logging

Le système de logging peut être configuré dans le fichier de configuration avec la clé `logLevel` :

**Niveaux disponibles** : DEBUG, INFO, WARNING, ERROR

### Emplacements des Logs

- **Python (threads)** : `.logs/` dans la racine du projet
    - `simulation.log` : Tous les niveaux
    - `error.log` : Erreurs et avertissements uniquement
- **Docker** : `.output/<run-name>/logs/`
    - Logs d'exécution des conteneurs
    - Logs de monitoring en temps réel

### Consulter les Logs

```bash
# Visualiser logs complets
tail -f .logs/simulation.log

# Visualiser erreurs uniquement
tail -f .logs/error.log

# Rechercher un événement spécifique
grep "microservice_name" .logs/*.log
```

### Débogage Docker

```bash
# Logs en temps réel d'un compose
docker compose -f .output/001/1_monolithic/docker-compose.yml logs -f

# Inspecter les conteneurs
docker stats

# Exécuter une commande dans un conteneur
docker exec -it <container_id> /bin/bash
```

---

# Structure du Projet

```
src/
├── Config/                          # Modèles et validation de configuration
│   ├── simulation_config.py          # Configuration top-level
│   ├── container_config.py           # Configuration des conteneurs
│   ├── service_config.py             # Configuration des services
│   └── microservice_config.py         # Configuration des microservices
├── Common/                           # Domaine métier commun
│   ├── Container/                    # Gestion des conteneurs logiques
│   ├── Service/                      # Orchestration des services
│   ├── Microservice/                 # Exécution des microservices
│   └── Monitor/                      # Collecte des métriques
├── Python/                           # Runtime threads Python
│   ├── main.py                       # Point d'entrée Python
│   └── platform.py                   # Plateforme d'exécution
└── Docker/                           # Runtime Docker
    ├── compose_builder.py            # Génération docker-compose.yml
    ├── compose_runner.py             # Exécution via Docker Compose
    └── runtime_runner.py             # Gestion des conteneurs
```

---

# Résultats Clés

## Conclusions Principales

1. **Isolation conteneurisée = Facteur déterminant** à forte charge
    - Réduit latence et taux d'échec
    - Augmente consommation CPU significativement

2. **Découplage CPU/Latence** selon le déploiement
    - Monolithe : CPU bas, latence élevée à haute charge
    - Multi-conteneur : CPU élevé, latence basse

3. **Profils de performance distincts**
    - Configuration 3 (monolithe) : Performance stable jusqu'à saturation
    - Configuration 6 (isolation forte) : Scalabilité meilleure mais coûteux

## Pour Plus de Détails

Consulter le rapport complet : [Rapport d'Application à la Démarche Scientifique - Alban GODIER.txt](Rapport%20d'Application%20à%20la%20Démarche%20Scientifique%20-%20Alban%20GODIER.txt)

---

# Conventions de Code

- **Style Python** : Black (line length: 100), Pylint
- **Target Python** : 3.10+
- **Configuration JSON** : camelCase mappé en snake_case via Pydantic
- **Logging** : Utiliser utilitaires dans `src/Common/Utils/logger.py`

---

# Ressources Additionnelles

- [AGENTS.md](AGENTS.md) - Instructions pour agents IA
- [DOCKER_USAGE.md](DOCKER_USAGE.md) - Détails d'utilisation Docker
- [config-test.json](config-test.json) - Configuration d'exemple
