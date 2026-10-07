# Phase 6A — Extraction PDF adaptative

## Audit avant modification

Le dépôt était propre. Lecture des deux applications Django, modèles et
migrations, formulaires, vues et routes, UsagePolicy, services documentaires,
tests, configuration, templates d'upload/résultat et documentation des phases
précédentes. Le code actuel a servi de référence. Baseline : **62 tests OK**.

`Tsukiyomi_account_app` gère les comptes et l'authentification.
`Tsukiyomi_app` conserve les uploads dans `DocFile`, la newsletter dans
`Subscriber` et le traitement synchrone dans `TranslationJob`.

La vue authentifiée valide le formulaire, applique les quotas free/paid et
contrôle le nombre de pages avec PyPDF2. Elle sauvegarde le document avant de
créer le job : un échec ultérieur consomme donc toujours le quota.

Le processor réserve le job par transition conditionnelle PENDING → PROCESSING,
copie l'upload dans `MEDIA_ROOT/jobs/<uuid>/source/`, utilise `working/` pour les
intermédiaires et `output/translation.docx` pour le résultat. Avant cette phase,
tout PDF était rasterisé à 300 dpi puis OCRisé. Les images passent par Pillow
et Tesseract. La traduction Google en français, les options des six langues,
la génération des pages DOCX et leur fusion ordonnée précèdent l'e-mail.

Les erreurs attendues deviennent `DocumentProcessingError` puis une réponse
HTTP 502 ; la cause reste accessible. Le processor enregistre FAILED et le seul
nom de classe de l'erreur avant de la relancer. Les bugs Python restent visibles.
Un OCR vide ou None termine historiquement SUCCEEDED sans artefact ni e-mail,
même sur une page ultérieure. Tous ces comportements sont conservés.

## Plan minimal et changements réalisés

| Fichier | Modification |
| --- | --- |
| `services/extraction.py` | Remplacement de la rasterisation globale par un parcours natif PyPDF2, une heuristique et une rasterisation ciblée. |
| `services/processor.py` | Fallback OCR seulement quand le parcours natif renvoie None pour la page. |
| `test_services.py`, `test_jobs.py`, `tests.py` | Simulations de Poppler limitées à une page ; vrais PDF multipages pour les scénarios historiques correspondants. |
| `test_extraction.py` | Quinze tests supplémentaires, avec sous-cas, dédiés à l'extraction adaptative. |
| Ce document | Audit, décisions, validation et limites. |

Les chemins de services sont relatifs à `Tsukiyomi_app/`. Aucun changement de
modèle, migration, dépendance, configuration, vue, formulaire, quota, workspace,
provider, rendu, notification ou branche Image. Aucune connexion PostgreSQL.

## Décision par page

`pdf_page_texts()` utilise un seul `PdfReader` et parcourt les pages dans l'ordre.
Le texte accepté est transmis intact : aucun strip, remplacement ou réassemblage
ne modifie ce qui part au traducteur. None signifie que cette page exige l'OCR.

`usable_native_text()` applique quelques règles déterministes :

- Refuser le vide, les marqueurs `(cid:123)` et les suites d'au moins huit
  lettres ou chiffres identiques.
- Refuser U+FFFD, les caractères privés, non assignés, surrogates et contrôles
  autres que tabulation, retour chariot et saut de ligne.
- Hors espaces et caractères de format Unicode, exiger au moins une lettre ou
  un nombre ; au moins 50 % des caractères doivent être des lettres, nombres
  ou marques diacritiques. Cela accepte les accents décomposés et les écritures
  japonaises/chinoises sans imposer de longueur minimale ni d'espaces entre mots.

Une `PdfReadError` provenant de `page.extract_text()` entraîne le fallback pour
cette seule page. Si PyPDF2 ne peut pas ouvrir ou parcourir le PDF, la même
exception est convertie localement en `DocumentProcessingError`, cause préservée.
ValueError, TypeError et KeyError inattendues ne sont pas absorbées.

Le processor appelle `rasterize_pdf_page()` uniquement sur les pages refusées.
`first_page=last_page=index+1` borne Poppler à une page. `paths_only=True` fournit
directement à Tesseract le chemin du fichier dans `working/`, sans charger une
image Pillow supplémentaire. Les options OCR PDF restent `--oem 3 --psm 6`.
Les pages DOCX gardent leur index original, leur titre historique et leur ordre
de fusion. Aucun résultat partiel n'est envoyé en cas d'échec.

## Validation

```bash
venv/bin/python manage.py test Tsukiyomi_app.test_services Tsukiyomi_app.test_jobs --settings=Tsukiyomi_project.test_settings --noinput --buffer
venv/bin/python manage.py test Tsukiyomi_app.test_extraction --settings=Tsukiyomi_project.test_settings --noinput --buffer
venv/bin/python manage.py test --settings=Tsukiyomi_project.test_settings --noinput --buffer
venv/bin/python manage.py check --settings=Tsukiyomi_project.test_settings
venv/bin/python manage.py makemigrations --check --dry-run --settings=Tsukiyomi_project.test_settings
git diff --check
```

Résultats : **18 tests historiques services/jobs OK ; 15 nouveaux tests OK ;
77 tests au total OK**. Check Django sans problème ; `No changes detected`.
Aucune migration créée ni appliquée à la base applicative.

Les nouveaux tests lisent de vrais PDF construits avec PyPDF2, dont du texte
latin accentué, et un PDF image construit avec Pillow. Le cas hybride vérifie
cinq pages avec exactement deux appels de rasterisation/OCR, sur les pages 2
et 4, puis le contenu ordonné du DOCX réel et de la pièce jointe. Les tests
couvrent également les titres courts, corruptions non vides, six langues,
erreurs d'ouverture/parcours/décodage, erreur Tesseract après une page native,
exceptions inattendues, états des jobs, isolation, double traitement et HTTP.
Les textes japonais/chinois sont testés dans l'heuristique et comme résultats
simulés de `extract_text()`, sans prétendre valider leurs polices PDF réelles.

La suite utilise SQLite de test et des fichiers temporaires. Réseau et
sous-processus y sont interdits ; traduction, SMTP, Poppler et Tesseract sont
simulés. Les tests historiques Image, quotas, erreurs et jobs concurrents sont
conservés ; aucun test métier supprimé.

Un contrôle ponctuel supplémentaire a utilisé les vrais Poppler et Tesseract
installés, sur un PDF temporaire de trois pages : texte natif, image contenant
« Scanned second chapter », texte natif. Résultat : textes natifs conservés,
un seul fichier rasterisé pour la page 2 et OCR anglais exact. Ce contrôle
n'utilise ni traduction réseau, ni SMTP, ni base de données.

## Limites assumées

L'heuristique détecte les corruptions évidentes, pas le sens d'un texte. Des
lettres incorrectes mais plausibles peuvent passer ; un texte légitime très
symbolique peut déclencher l'OCR. Une couche native partielle peut aussi être
acceptée. L'ordre de lecture interne reste celui de PyPDF2, notamment pour les
colonnes et mises en page complexes ; seul l'ordre des pages est garanti ici.
Un corpus réel multilingue permettrait d'ajuster ces règles ultérieurement.

Pas de segmentation, nouveau moteur PDF, pipeline asynchrone, changement de
stockage ou reconstruction avancée. Tesseract et Poppler restent nécessaires
pour le fallback ; Tesseract reste systématique pour PNG/JPG. Google/SMTP et
PostgreSQL n'ont pas fait l'objet de tests d'intégration réels pendant ce travail.
