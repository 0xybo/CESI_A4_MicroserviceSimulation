Ce projet est la partie simulation de l'application à la démarche scientifique, un module d'enseignement en école d'ingénieur dont l'object est de découvrir le processus de recherche.

Titre : Influence de la granularité des microservices et de leur déploiement conteneurisé sur les performances d’une application distribuée simulée

Problèmatique : Dans une architecture microservices déployée en conteneurs, comment la variation du niveau de granularité et de la distribution des services influence-t-elle les performances globales du système (latence, temps de réponse, charge) ?

L'objectif de ce projet est de simuler sur deux supports différents (Python Thread, Docker) une architecture en microservices décrite dans un fichier de configuration founi (une partie du schéma de cette configuration est décrit dans le fichier Common/Config/schema.json). Une architecture se composera de :

- conteneurs (Container) : Représente la séparation matérielle des services. Un conteneur peut héberger un ou plusieurs services.
- services (Service) : Représente les différentes fonctionnalités de l'application. Un service peut contenir un ou plusieurs microservices.
- microservices (Microservice) : Représente les unités de travail individuelles qui composent les services.

---

# Hypothèses

Pour déterminer les hypothèses, il faut déjà se pencher sur la variable importante du sujet : le niveau de granularité. En effet, ce sujet implique de faire évoluer cette variable afin de trouver sa valeur optimale. Une architecture logicielle étant complexe, la valeur trouvée de niveau de granularité correspondra directement à l'architecture adoptée. Dans le but de généraliser au maximum l'expérimentation, il est envisagé de créer une architecture qui peut être modulée à volonté grâce un simple fichier de configuration. Pour plus de facilité, ne seront étudiés que trois cas, deux extrêmes et un intermédiaire de façon à montrer que la solution intermédiaire cherchant à trouver un juste milieu entre les deux solutions extrêmes est la meilleure.

Niveau de granularité :

- **Fine** : Une granularité trop fine devrait augmenter le nombre d'interactions réseau, la latence, les surcoûts de coordination et la consommation d’énergie, tout en améliorant potentiellement la flexibilité de déploiement et la scalabilité ciblée.
  ➡️ Cette solution sera simulée en séparant au maximum (en microservices) l'ensemble des briques impliquées dans l'application simulée.
- **Intermédiaire** : La solution intermédiaire doit maximiser chacun des paramètres importants (interactions réseau, la latence, les surcoûts de coordination et la consommation d’énergie, flexibilité de déploiement, maintenabilité, la scalabilité, ...)
  ➡️ La solution intermédiaire sera choisie de manière arbitraire en ne divisant qu'une partie de l'application simulée.
- **Grossière** : Une granularité trop grossière réduit les surcoûts de communication, mais peut dégrader la maintenabilité, la modularité et la possibilité de scaler indépendamment certaines parties.
  ➡️ La solution grossière correspondra à une application monolithe exécutant l'ensemble des tâches dans un seul et même programme.

Dans le but de simuler également la répartition des microservices sur différentes machines, il est également envisagé de faire intervenir un autre niveau de séparation, cette fois-ci, au niveau matériel :

- Un seul conteneur Docker pour l'ensemble des microservices. Cette solution devrait montrer une faible résilience et une capacité de maintenance faible. Par contre, du fait de la présence d'un seul conteneur, les ressources de gestion des conteneurs et des conteneurs eux-mêmes seront grandement réduits.
- Un conteneur par regroupement de microservices.
- Un conteneur par microservice. Cette solution devrait montrer une grande facilité à maintenir le système et une bonne résilience, mais au contraire, devrait surcharger le système hôte, en l'occurrence, mon ordinateur personnel.

Situations envisagées :

| Granularité ➡️<br>Séparation matérielle ⬇️ | Grossière | Moyenne | Fine |
| ------------------------------------------ | --------- | ------- | ---- |
| **Nulle**                                  |           |         |      |
| **Moyenne**                                | X         |         |      |
| **Forte**                                  | X         | X       |      |

## Hypothèse 1 — Impact des communications réseau

**H1 :**
Une granularité fine des microservices augmente le nombre de communications inter-services, ce qui entraîne une augmentation de la latence et du temps de réponse global du système.

Justification :

- plus de microservices
- plus d’appels réseau
- surcharge de communication

Mesure :

- nombre d’appels inter-services
- latence moyenne
- temps de réponse

---

## Hypothèse 2 — Réduction des surcoûts avec une granularité grossière

**H2 :**
Une granularité grossière réduit le nombre de communications inter-services et améliore les performances globales du système en diminuant la latence et la charge réseau.

Justification :

- moins de services
- moins de communications réseau
- moins de surcharge protocolaire

Mesure :

- temps de réponse
- latence
- trafic réseau

---

## Hypothèse 3 — Existence d’un compromis optimal

**H3 :**
Un niveau de granularité intermédiaire permet d’obtenir un compromis optimal entre modularité du système et performances globales.

Justification :

- trop fin → surcharge réseau
- trop grossier → complexité interne et manque de modularité

Mesure :

- comparaison des performances entre
    - architecture fine
    - architecture intermédiaire
    - architecture grossière

---

## Hypothèse 4 — Impact du déploiement conteneurisé

**H4 :**
La distribution des microservices dans plusieurs conteneurs augmente les coûts de communication inter-processus et peut dégrader les performances par rapport à une exécution dans un seul conteneur.

Justification :

- communication inter-processus
- virtualisation
- réseau Docker

Mesure :

- temps de réponse
- latence
- consommation CPU

---

## Hypothèse 5 — Influence de la charge système

**H5 :**
L’impact de la granularité sur les performances devient plus significatif lorsque la charge du système augmente.

Justification :

- plus de requêtes
- plus de communications
- saturation réseau possible

Mesure :

- tests avec plusieurs niveaux de charge
    - faible
    - moyen
    - élevé

---

# Demarrage rapide

## Prerequis

- Python 3.11+

## Lancer une simulation Python (threads)

Depuis la racine du projet:

```bash
python -m Python.main --config config-test.json --requests 200 --workers 2
```

Options utiles:

- `--requests`: nombre de requetes par service
- `--workers`: nombre de threads pour executer les conteneurs en parallele
- `--output`: ecrit le resultat JSON dans un fichier

Exemple:

```bash
python -m Python.main --config config-test.json --requests 500 --workers 4 --output results.json
```

## Generer un compose Docker

```bash
python -m Docker.main --config config-test.json --output Docker/docker-compose.generated.yml
```

Le fichier genere decrit les conteneurs logiques declares dans la configuration.

## Logging

The application includes a comprehensive logging system that tracks execution across all components:

- **Log Location**: `.logs/` folder in the project root
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Files**:
    - `simulation_YYYYMMDD_HHMMSS.log` - Complete logs at all levels
    - `errors_YYYYMMDD_HHMMSS.log` - Errors and warnings only
    - Console output - INFO level and above

For detailed logging documentation and usage examples, see [LOGGING.md](LOGGING.md)

### View Logs

```bash
# View latest simulation log
tail -f .logs/simulation_*.log

# View errors only
tail -f .logs/errors_*.log

# Search for specific events
grep "microservice_name" .logs/*.log
```
