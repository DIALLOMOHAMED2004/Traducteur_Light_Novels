# Phase 7 — Dépendances et runtime portable

## Audit initial (7 octobre 2026)

Audit avant toute modification du dépôt : les deux documents de référence du
répertoire parent, les notes des phases 0 à 6B, les applications, modèles,
12 migrations applicatives, services, formulaires, routes, templates, tests,
configuration et dépendances ont été examinés. Aucun `AGENTS.md` applicable.
Le dépôt était propre. Aucun Dockerfile, Compose ou `.dockerignore` existant.

Deux applications : `Tsukiyomi_account_app` pour `UserTsukiyomi` et
l'authentification ; `Tsukiyomi_app` pour `DocFile`, `Subscriber`, les uploads,
la newsletter et `TranslationJob`. La vue valide l'upload, applique
`UsagePolicy` (Free : 2 PDF / 5 pages / 3 images ; Paid : 10 / 30 / 15),
sauvegarde le document puis crée le job synchrone. Les quotas restent consommés
si le traitement échoue après sauvegarde.

Le processor réserve PENDING → PROCESSING, prépare
`MEDIA_ROOT/jobs/<uuid>/{source,working,output}`, puis orchestre l'extraction,
la segmentation, la traduction, la reconstruction/fusion DOCX et l'e-mail.
Le résultat est `output/translation.docx` ; les statuts finaux restent
SUCCEEDED/FAILED. PyPDF2 extrait et valide le texte natif page par page.
`pdf2image.convert_from_path` rasterise seulement les pages refusées, à 300 dpi,
avant Tesseract. Les images utilisent Pillow puis Tesseract. Les segments et
le contrat `TranslationProvider` existent déjà ; `deep_translator.GoogleTranslator`
reste l'unique implémentation, avec cible française et options inchangées.

Les chemins de services sont déjà portables (`Path`, chemins relatifs,
exécutables trouvés dans `PATH`). Aucune utilisation active de `poppler_path`,
`tesseract_cmd`, `C:\\...` ou `Program Files`. Les commandes Windows restantes
étaient dans le README ; elles sont remplacées par une installation documentée.
Les chemins historiques du nettoyage administratif, la configuration des
statiques et les URLs restent inchangés. `WORKDIR /app` respecte leurs chemins
relatifs. Aucun correctif historique déjà réalisé n'est réintroduit.

Django 5.2.17 et Python 3.12.3 fonctionnaient dans le venv local. PostgreSQL
est configuré par environnement ; les tests utilisent explicitement SQLite en
mémoire. L'hôte possède Poppler 24.02.0 et Tesseract 5.3.4 avec les six langues
requises plus `osd`. La suite simule Google, SMTP, Poppler et Tesseract ; les
PDF, DOCX, copies et workspaces sont réels. Les tests documentaires interdisent
réseau et sous-processus. Baseline : **94 tests réussis**, check sans problème,
`No changes detected`, `git diff --check` et `git status --short` sans sortie.

## Dépendances directes

La recherche couvre les imports et références du code actuel, pas seulement
les descriptions historiques. Aucune version active n'est mise à jour.

| Dépendance | Décision et preuve d'utilisation |
| --- | --- |
| `Django==5.2.17` | Conservée : framework, ORM, HTTP, auth, formulaires, tests et e-mails. |
| `deep-translator==1.11.4` | Conservée : `services/translation.py` importe `GoogleTranslator` ; exceptions dans `services/errors.py`. |
| `pdf2image==1.17.0` | Conservée : rasterisation ciblée dans `services/extraction.py` ; nécessite Poppler. |
| `pillow==11.3.0` | Conservée : imports `PIL` dans formulaires/extraction, validation et ouverture des images ; utilisée aussi par pdf2image/pytesseract. |
| `psycopg2-binary==2.9.11` | Conservée : driver `psycopg2` chargé par le backend PostgreSQL Django ; déjà employé dans le venv. |
| `PyPDF2==3.0.1` | Conservée : validation/comptage et extraction native ; aucun changement de moteur PDF. |
| `pytesseract==0.3.13` | Conservée : `services/ocr.py` et gestion des erreurs ; nécessite l'exécutable et les traineddata Tesseract. |
| `python-docx==1.2.0` | Conservée : `services/rendering.py` importe `docx.Document` pour création et fusion. Pas de Word nécessaire. |
| `requests==2.34.2` | Désormais déclarée directement : `services/errors.py` importe `RequestException`, les tests importent ses exceptions. Version déjà installée, auparavant transitive de deep-translator. |
| `argostranslate==1.10.0` | Retirée : aucun import ni appel dans les sources actuelles. Les mentions de code commenté sont historiques. Aucun moteur local actif. |
| `googletrans==4.0.2` | Retirée : aucun import ni appel. Ce package est distinct de la classe GoogleTranslator de deep-translator. |
| `docx2pdf==0.1.8` | Retirée : aucun import ni appel actuel ; la sortie est directement DOCX. Aucune dépendance Word/desktop à conserver. |
| `psycopg2==2.9.11` | Retirée : second paquet fournissant le même module que psycopg2-binary ; exigerait compilateur et en-têtes libpq. |

Le choix du wheel `psycopg2-binary` conserve le runtime déjà testé et évite une
chaîne de compilation. Ses bibliothèques natives sont embarquées : leur mise
à jour passe par celle du wheel. La documentation Psycopg recommande une
compilation source pour un déploiement de production ; ce choix sera réévalué
lors de ce chantier, sans installer les deux distributions simultanément.
Voir [l'installation officielle Psycopg](https://www.psycopg.org/docs/install.html).

`requirements.txt` contient les neuf dépendances directes ; `requirements.lock`
l'inclut et fige les onze transitives de l'environnement validé :
`asgiref`/`sqlparse` (Django), `beautifulsoup4`/`soupsieve` (deep-translator),
`certifi`/`charset-normalizer`/`idna`/`urllib3` (requests), `lxml` et
`typing_extensions` (python-docx, également requis par Beautiful Soup),
`packaging` (pytesseract). `tqdm`, apporté par docx2pdf, n'est plus nécessaire.
Le lock est un fichier pip simple, sans nouvel outil de gestion. Lors d'une
mise à jour, résoudre dans un venv neuf, actualiser les pins transitifs et
relancer les validations ; ne pas recopier tout le venv historique.

## Docker et stockage

L'image officielle `python:3.12-slim-bookworm` est figée par digest dans le
Dockerfile : Python 3.12.15 sur Debian Bookworm. Une seule étape de construction,
pas de worker, proxy, ordonnanceur ou nouveau serveur Python.

Paquets système explicites : `poppler-utils`, `tesseract-ocr`,
`tesseract-ocr-fra`, `tesseract-ocr-eng`, `tesseract-ocr-ita`,
`tesseract-ocr-spa`, `tesseract-ocr-jpn`, `tesseract-ocr-chi-tra`.
Les codes vérifiés dans `services/languages.py` sont exactement
`fra`, `eng`, `ita`, `spa`, `jpn`, `chi_tra`. `osd` est aussi installé par Debian.
Poppler apporte notamment `pdfinfo` et `pdftoppm` au fallback PDF.

Les dépendances Python sont installées depuis `requirements.lock`, puis
`pip check` vérifie leur cohérence. Le processus applicatif tourne sous
`tsukiyomi` (UID 1000), sans privilèges root, dans `/app`.
`/app/media_upload` est créé avec les droits de cet utilisateur.

`.dockerignore` utilise une liste d'inclusion : seules les sources Django,
les migrations/tests/templates, `manage.py`, les requirements et les assets
statiques compilés sont envoyés. Les `.env`, clés, caches, venv, `.git`,
backups PostgreSQL, documents locaux et outils de développement sont exclus.
Aucun secret n'est demandé pendant le build ni inscrit dans l'image.

Compose ajoute seulement `web` et `db` : PostgreSQL **18.6 Bookworm**, même
version majeure que l'environnement documenté, figé lui aussi par digest.
Le port web est limité à `127.0.0.1:8000` ; PostgreSQL n'expose aucun port hôte.
Le healthcheck attend PostgreSQL avant le lancement web. Les volumes nommés
`media` et `postgres` persistent respectivement `/app/media_upload` et
`/var/lib/postgresql` (emplacement de volume de l'image officielle PostgreSQL 18).
Voir [la documentation de l'image PostgreSQL](https://hub.docker.com/_/postgres).

Le service `db` démarre une base de développement séparée. Il ne migre ni ne
remplace la base existante de l'hôte. Les migrations ne sont exécutées ni au
build ni au démarrage : la commande explicite du README initialise uniquement
une nouvelle base avec les migrations déjà présentes. Ne pas monter un ancien
répertoire PostgreSQL d'une autre version majeure dans ce volume.

## Configuration et lancement

Aucun changement dans `settings.py` ni `.env.example`. Django lit `os.environ`,
pas directement un fichier `.env`. Compose injecte ce fichier au démarrage.

| Variables | Usage |
| --- | --- |
| `DJANGO_SECRET_KEY` | Obligatoire, valeur personnelle fournie à l'exécution. |
| `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` | Pour le serveur local HTTP : `True` et `localhost,127.0.0.1`. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Identifiants de la base ; requis explicitement par Compose. |
| `POSTGRES_HOST`, `POSTGRES_PORT` | Utilisés en Linux/image seule ; Compose les remplace par `db` et `5432` uniquement dans `web`. |
| `EMAIL_BACKEND` | SMTP par défaut ; un backend console peut être sélectionné volontairement pour un essai local sans envoi. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS` | Connexion SMTP existante. |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | Identifiants et expéditeur nécessaires pour l'envoi réel. |

Ne pas écraser un `.env` existant. Pour une installation neuve, copier
`.env.example`, remplacer les placeholders et garder ce fichier hors Git.
Les variables exportées dans le shell priment sur `.env` pour l'interpolation
Compose ; ces identifiants sont transmis identiquement aux deux services.
Une modification de mot de passe dans `.env` ne reconfigure pas un volume
PostgreSQL déjà initialisé.

```bash
# Image autonome, sans besoin de secrets ni de base pendant la construction.
docker build -t tsukiyomi:phase7 .
# Développement avec une nouvelle base Docker : voir aussi le README.
docker compose build
docker compose up -d db
docker compose run --rm web python manage.py migrate
docker compose up -d web
docker compose logs web
# Arrêt en conservant les volumes.
docker compose down
```

Accès : <http://localhost:8000/accounts/login/>. Pour une base PostgreSQL
existante, lancer seulement l'image, avec un `.env` dont `POSTGRES_HOST`
désigne un hôte accessible depuis le conteneur (son `127.0.0.1` désigne le
conteneur lui-même). Ne pas lancer `migrate` automatiquement sur cette base.

```bash
docker run --rm --env-file .env -p 127.0.0.1:8000:8000 \
  --mount type=volume,source=tsukiyomi-media,target=/app/media_upload \
  tsukiyomi:phase7
```

Avec un bind mount existant, son propriétaire doit permettre l'écriture à
l'UID 1000 ; un volume nommé neuf reçoit les droits du dossier de l'image.
Il faut conserver à la fois la base et les médias pour retrouver les jobs.

### Installation Linux sans Docker

Sur Debian/Ubuntu, installer Python 3.12 avec venv et disposer d'un serveur
PostgreSQL accessible. Depuis la racine du dépôt :

```bash
sudo apt-get update
sudo apt-get install poppler-utils tesseract-ocr \
  tesseract-ocr-fra tesseract-ocr-eng tesseract-ocr-ita \
  tesseract-ocr-spa tesseract-ocr-jpn tesseract-ocr-chi-tra
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.lock
# Après création/vérification de votre .env :
set -a
. ./.env
set +a
python manage.py check
# Seulement pour initialiser une nouvelle base : python manage.py migrate
python manage.py runserver
```

Tesseract/Poppler sont découverts via `PATH` ; aucun chemin machine à ajouter
au code. Le fichier chargé par le shell doit être un fichier de confiance,
avec ses valeurs correctement citées pour le shell.

## Validations

### Commandes et résultats

Avant modification (Python du venv existant), puis après modification avec
`/tmp/tsukiyomi-phase7-venv/bin/python`, créé sans les packages historiques :

```bash
venv/bin/python manage.py check --settings=Tsukiyomi_project.test_settings
venv/bin/python manage.py test --settings=Tsukiyomi_project.test_settings --noinput --buffer
venv/bin/python manage.py makemigrations --check --dry-run --settings=Tsukiyomi_project.test_settings
python3 -m venv /tmp/tsukiyomi-phase7-venv
/tmp/tsukiyomi-phase7-venv/bin/python -m pip install --disable-pip-version-check --no-cache-dir -r requirements.lock
/tmp/tsukiyomi-phase7-venv/bin/python -m pip check
/tmp/tsukiyomi-phase7-venv/bin/python manage.py check --settings=Tsukiyomi_project.test_settings
/tmp/tsukiyomi-phase7-venv/bin/python manage.py test --settings=Tsukiyomi_project.test_settings --noinput --buffer
/tmp/tsukiyomi-phase7-venv/bin/python manage.py makemigrations --check --dry-run --settings=Tsukiyomi_project.test_settings
```

| Contrôle | Baseline | Venv neuf | Docker |
| --- | --- | --- | --- |
| Suite existante | 94 OK | 94 OK | 94 OK |
| Django check | Aucun problème | Aucun problème | Aucun problème |
| Migrations dry-run | No changes detected | No changes detected | No changes detected |
| pip check | OK | OK | OK |

Les 94 tests et leurs assertions sont inchangés. Aucune dépendance historique
installée dans le venv neuf ou l'image. Le premier essai pip dans le sandbox
était bloqué par le DNS ; l'installation autorisée avec accès réseau a réussi.
L'accès au socket Docker a également nécessité une exécution hors sandbox.
Aucun échec applicatif préexistant ou introduit n'a été observé.

```bash
docker build -t tsukiyomi:phase7 .
docker run --rm --network none tsukiyomi:phase7 python manage.py check --settings=Tsukiyomi_project.test_settings
docker run --rm --network none tsukiyomi:phase7 python manage.py test --settings=Tsukiyomi_project.test_settings --noinput --buffer
docker run --rm --network none tsukiyomi:phase7 python manage.py makemigrations --check --dry-run --settings=Tsukiyomi_project.test_settings
docker run --rm --network none tsukiyomi:phase7 sh -c 'python --version && python -m pip check && tesseract --version && tesseract --list-langs && pdftoppm -v && pdfinfo -v && id && test ! -e /app/.env && test ! -e /app/backups && test ! -e /app/venv && test ! -e /app/.git'
```

Builds Docker et Compose réussis. Python **3.12.15**, Tesseract **5.3.0**, Poppler **22.12.0**,
UID/GID **1000**, sept traineddata (`chi_tra`, `eng`, `fra`, `ita`, `jpn`,
`osd`, `spa`). Les neuf dépendances directes sont présentes, les distributions
retirées et `tqdm` sont absentes. `.env`, `.git`, venv, backups et le script
local d'export sont absents de l'image. Le contexte transmis est d'environ
17,7 Mo, comprenant les assets existants.

### Intégration réelle, sans services externes

Un script ponctuel conservé dans
`/tmp/tsukiyomi-phase7-validation/smoke.py` a été exécuté sur l'hôte et dans
l'image :

```bash
PYTHONPATH=. /tmp/tsukiyomi-phase7-venv/bin/python /tmp/tsukiyomi-phase7-validation/smoke.py
docker run --rm --network none -i tsukiyomi:phase7 python - < /tmp/tsukiyomi-phase7-validation/smoke.py
```

Le script utilise les services réels et le générateur PDF existant des tests,
une base SQLite en mémoire et des fichiers temporaires. Il crée un utilisateur
et quatre jobs : PDF numérique, PDF scanné, PDF hybride et PNG. Le provider
est injecté localement et les e-mails sont en mémoire ; les connexions réseau
sont interdites. Poppler et Tesseract sont réellement exécutés, et chacun des
six modèles OCR est chargé. Les vérifications portent sur :

- texte natif intact et zéro rasterisation pour le PDF numérique ;
- OCR anglais exact sur le scan (« Scanned second chapter ») ;
- rasterisation de la seule page 2 du PDF hybride ;
- OCR réel de l'image ;
- quatre jobs SUCCEEDED, chemins UUID distincts, contenu/ordre des DOCX et
  relecture de chacune des quatre pièces jointes.

**Quatre scénarios réussis sur l'hôte et quatre dans Docker.** Le chargement
des six modèles ne constitue pas une évaluation de qualité linguistique sur
six corpus. Le script ponctuel est un artefact de validation local, pas un
nouveau test automatique dépendant des binaires système.

### Compose, PostgreSQL et persistance

Un projet jetable `tsukiyomi-phase7-check` a été utilisé avec un fichier
`runtime.env` temporaire (secrets aléatoires non affichés) et un override
remplaçant le fichier d'environnement web et le port hôte par `18007`.
Les commandes utilisent le préfixe suivant, sans charger le `.env` réel :

```bash
docker compose -p tsukiyomi-phase7-check \
  --env-file /tmp/tsukiyomi-phase7-validation/runtime.env \
  -f compose.yaml -f /tmp/tsukiyomi-phase7-validation/override.yaml config --quiet
```

Avec le même préfixe : `build`, `up -d db`,
`run --rm web python manage.py migrate --noinput`, `up -d web`,
`exec -T web python manage.py check` et
`exec -T web python manage.py makemigrations --check --dry-run`.
Les migrations **historiques** sont appliquées uniquement à cette nouvelle
base temporaire ; aucune table existante de l'utilisateur n'est consultée ou
modifiée. Le driver PostgreSQL réel exécute `SELECT 1` avec succès.
Les paramètres Django/DB/e-mail sont comparés aux variables injectées sans
afficher les secrets. Check sans problème et `No changes detected` également
avec les settings PostgreSQL réels.

GET `http://127.0.0.1:18007/accounts/login/` et
`http://127.0.0.1:18007/static/assets/css/theme.css` : **200**.
Un fichier écrit dans MEDIA_ROOT par le serveur est relu depuis un second
conteneur, puis retiré. Les ressources du seul projet de validation sont
nettoyées avec le même préfixe et `down --volumes` ; les fichiers et services
de l'utilisateur sont conservés. L'image `tsukiyomi:phase7` reste disponible.

### Revue finale

```bash
git diff --check
git status --short
git diff --exit-code -- Tsukiyomi_app Tsukiyomi_account_app Tsukiyomi_project
```

Diff sans défaut d'espacement, aucun changement dans les trois packages
Python. Fichiers modifiés : `requirements.txt`, `README.md`. Fichiers créés :
`requirements.lock`, `Dockerfile`, `.dockerignore`, `compose.yaml`, cette note.
**Aucun fichier supprimé, aucun modèle modifié, aucune migration créée ou
modifiée, aucune table existante modifiée.** Aucun commit ni push.

## Limites conservées

Le runtime et Compose servent le développement local avec `runserver`.
Le serveur WSGI/ASGI de production, HTTPS, le service des statiques/médias en
production, la CI/CD et la politique de mise à jour restent des chantiers
ultérieurs. Avec `DEBUG=False`, les cookies exigent HTTPS et le serveur local
ne fournit plus les statiques comme en développement : aucun contournement.

Les images de base sont figées par digest et les versions Python directes et
transitives sont fixées. Les paquets APT proviennent des dépôts Bookworm de
sécurité maintenus : leurs révisions peuvent évoluer à reconstruction sans
cache. Ce n'est donc pas une promesse d'image identique octet pour octet ;
aucun dépôt snapshot ou miroir privé n'est ajouté. Conserver le digest de
l'image construite pour redéployer exactement le même artefact. Validation
sur Linux amd64 ; les autres architectures ne sont pas déclarées testées.

Le pipeline reste synchrone, sur disque local, avec ses limites documentées
(quota non atomique, jobs interrompus, qualité OCR, taille des segments,
timeout Google non garanti, envoi non transactionnel). Pas de Celery, Redis,
S3, nouveau provider ou modification fonctionnelle. Google et SMTP ne sont
pas contactés pendant les validations ; la qualité linguistique et la
livraison réelle restent hors de cette phase.
