# Phase 8 — Intégration continue minimale

## Périmètre et choix

Le workflow [CI](../.github/workflows/ci.yml) automatise les commandes existantes
de Tsukiyomi. Il complète le [runtime de phase 7](phase7_runtime_portable.md)
sans modifier les applications, les modèles, les migrations, les dépendances,
le Dockerfile ou Compose. Seuls le workflow, le README et cette note changent.

Un seul job, **Django et Docker**, s'exécute sur un runner GitHub hébergé
`ubuntu-24.04`, avec Python `3.12` et une limite de 20 minutes. La version
corrective de Python dépend de celle disponible pour cette branche 3.12 ;
l'image Docker conserve sa propre version, fixée par le digest existant.

Les déclencheurs sont les pushs sur `develop` et `main`, et les pull requests
vers ces branches (ouverture, réouverture et nouveaux commits). `develop`
reçoit les travaux des phases ; `main` est la branche par défaut. Une branche
de travail comme `phase8` est vérifiée par sa PR, sans exécution sur chacun de
ses pushs avant ouverture de PR. Aucun filtre de chemins ne saute le contrôle.

Les deux actions appartiennent à l'organisation officielle GitHub `actions`.
Leurs tags ont été résolus en commits le 26 octobre 2026 et leurs manifestes
`action.yml` consultés :

| Action | Version | SHA utilisé |
| --- | --- | --- |
| [actions/checkout](https://github.com/actions/checkout/releases/tag/v7.0.1) | v7.0.1 | [`3d3c42e5aac5ba805825da76410c181273ba90b1`](https://github.com/actions/checkout/commit/3d3c42e5aac5ba805825da76410c181273ba90b1) |
| [actions/setup-python](https://github.com/actions/setup-python/releases/tag/v7.1.0) | v7.1.0 | [`6d4fd22b20465ccc0f7354476588e8df7c9ca0e0`](https://github.com/actions/setup-python/commit/6d4fd22b20465ccc0f7354476588e8df7c9ca0e0) |

La permission du jeton GitHub est limitée à `contents: read` ; checkout ne
conserve pas les identifiants Git. Aucun secret applicatif n'est nécessaire.
Aucun linter, formateur, cache supplémentaire ou dépendance n'est ajouté.

## Contrôles exécutés par le runner

Chaque commande constitue une étape distincte après checkout et setup-python :

```bash
python -m pip install -r requirements.lock
python -m pip check
python manage.py check --settings=Tsukiyomi_project.test_settings
python manage.py test --settings=Tsukiyomi_project.test_settings --noinput --buffer
python manage.py makemigrations --check --dry-run --settings=Tsukiyomi_project.test_settings
docker build -t tsukiyomi:ci .
```

`requirements.lock` inclut les dépendances directes de `requirements.txt`.
Les commandes Django utilisent exclusivement la configuration de tests :
SQLite en mémoire et e-mails en mémoire. Les tests documentaires créent leurs
fichiers dans des répertoires temporaires et simulent Google, SMTP, Poppler et
Tesseract. Ils n'utilisent ni `.env` personnel ni documents de `media_upload`.
Le runner de tests initialise sa base SQLite temporaire ; aucune commande
`migrate` n'est lancée sur la base applicative. Le dry-run détecte un écart
entre modèles et migrations sans écrire de migration ni modifier de table.

Le build réutilise le Dockerfile et sa liste d'inclusion `.dockerignore`.
Poppler, Tesseract et ses langues sont installés dans l'image. Aucun service
Compose n'est démarré, aucun volume n'est monté et aucun conteneur applicatif
n'est lancé. L'image `tsukiyomi:ci` reste sur le runner éphémère : aucune
publication dans un registre ni aucun déploiement.

Un code de sortie non nul fait échouer le job ; les étapes suivantes sont
alors ignorées. Une installation ou un test en échec empêche donc le build.
Le dépassement du délai interrompt également le job. Aucun échec n'est masqué.

## Validation locale

Validation du 26 octobre 2026 dans un venv neuf, Python **3.12.3** :

```bash
/usr/bin/python3 -m venv /tmp/tsukiyomi-phase8-venv
PYTHONDONTWRITEBYTECODE=1 /tmp/tsukiyomi-phase8-venv/bin/python -m pip install --disable-pip-version-check --no-cache-dir -r requirements.lock
```

Les quatre commandes `pip check`, `manage.py check`, `manage.py test` et
`manage.py makemigrations` ci-dessus ont ensuite été exécutées avec ce même
Python et `PYTHONDONTWRITEBYTECODE=1`, sans modifier le venv du projet.

| Contrôle | Résultat réellement obtenu |
| --- | --- |
| Installation depuis le lock | Réussie ; les 20 versions directes/transitives correspondent aux fichiers. |
| `pip check` | `No broken requirements found.` |
| Django check | Aucun problème. |
| Suite de tests | **94 tests réussis**, environ 20 secondes. |
| Migrations, check et dry-run | `No changes detected`. |
| YAML et commandes shell | Analyse avec PyYAML système déjà installé (`BaseLoader` pour conserver la clé `on`), vérification des paramètres et `bash -n` sur chaque commande : réussies. |
| Documentation | Liens Markdown locaux vérifiés. |
| Diff et périmètre | `git diff --check`, contrôle des deux fichiers nouveaux avec `git diff --no-index --check`, revue intégrale : seuls les trois fichiers autorisés changent. |
| Docker | Client 29.1.3 ; socket inaccessible, build **non exécuté**. |
| GitHub Actions | **Non exécuté** ; aucun commit, push ou PR réalisé. |

Le premier téléchargement pip a échoué à cause du DNS du sandbox ; la reprise
avec accès réseau autorisé a réussi dans le même venv temporaire. `pip check`
signale seulement un cache local non accessible, sans conflit de dépendances.
`docker version --format '{{.Client.Version}} {{if .Server}}{{.Server.Version}}{{end}}'`
échoue avec `permission denied` sur le socket. Aucun changement de permissions
ni tentative d'accès privilégié à Docker n'a été effectué.

Les packages Django, modèles, migrations, fichiers de dépendances, Dockerfile,
`.dockerignore` et Compose ne présentent aucun diff. Aucune opération sur
PostgreSQL ni sur les médias personnels. Aucun nouvel outil installé pour
valider le YAML. Cette analyse locale et cette revue ne remplacent pas la
validation du workflow sur un runner GitHub.

## Validation et protection sur GitHub

Après revue humaine et autorisation distincte pour commit, push et PR :

1. Vérifier dans **Settings → Actions → General** que GitHub Actions et les
   deux actions officielles sont autorisés. Aucun secret applicatif à créer.
2. Publier la branche puis ouvrir une PR vers `develop` pour lancer la CI.
3. Dans **Actions → CI → Django et Docker**, lire les étapes et leurs logs ;
   la PR affiche également le résultat dans ses contrôles. Attendre une
   exécution complète réussie, build Docker compris.
4. Dans **Settings → Rules → Rulesets**, ou les règles de protection des
   branches, exiger une PR et le contrôle **Django et Docker** avant fusion
   sur `develop`, puis `main`. Sélectionner le contrôle réellement apparu
   après la première exécution et définir explicitement les éventuels bypass.

Le workflow signale les échecs ; les règles GitHub rendent leur résolution
obligatoire avant fusion. Sans ces règles, un échec ne suffit pas à interdire
une fusion. Un simple push sur `phase8` sans PR ne déclenche pas ce workflow.

Références : [syntaxe des workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
et [protection des branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

## Limites

La phase 8 reste à valider par une exécution réelle réussie sur GitHub.
La suite SQLite ne remplace pas une validation PostgreSQL. Les services
simulés ne mesurent ni la qualité OCR/traduction ni la livraison SMTP réelle.
Un build réussi valide la construction de l'image, pas son fonctionnement en
production. Le serveur de développement et les limites métier documentées
en phase 7 restent inchangés.

GitHub, PyPI et les dépôts Debian doivent être accessibles pendant la CI.
Les versions Python des dépendances et les SHA des actions sont fixés, mais
les révisions APT peuvent évoluer : la construction n'est pas garantie
identique octet pour octet. La CI protège les comportements couverts par les
tests ; elle ne garantit pas l'absence absolue de bugs.
