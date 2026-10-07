# Phase 4 — Sortir le métier de views.py

## Audit initial

L'audit et les tests ont précédé toute modification. Le dépôt était propre.
Sources consultées : applications et migrations existantes, formulaires,
modèles, vues, routes, templates, tests, settings et test_settings, documents
des phases 0, 2 et 3 dans `docs/`, ainsi que
`../tsukiyomi_roadmap_refactorisation_finale.md` et
`../tsukiyomi_parcours_backend_developer.md`. Aucun document spécifique à la
Phase 1 n'est présent dans `docs/` ; ses protections sont visibles dans le code
et les tests existants.

Deux applications Django : `Tsukiyomi_account_app` gère l'utilisateur et son
authentification ; `Tsukiyomi_app` gère les documents et la newsletter.
`views.py` compte initialement 1 202 lignes. Le pipeline Free/Paid est déjà
commun, mais conserve douze branches PDF/Image/langue presque identiques.

Le flux validé dans le code est le suivant :

1. Authentification, choix de `UsagePolicy`, nettoyage historique des dossiers.
2. `DocumentForm` préfixé `pi`, avec `profileType=pdf_img` : validation des
   choix, extensions, contenu, taille et dimensions.
3. Comptage des `DocFile` par utilisateur/type, puis contrôle des pages PDF.
4. Sauvegarde du nouveau `DocFile`, utilisé directement pour le traitement.
5. PDF : création des dossiers, Poppler à 300 dpi, OCR page par page,
   traduction en français, DOCX de chaque page, fusion numérique explicite.
   Image : ouverture Pillow dans un contexte, OCR, traduction, DOCX unique.
6. E-mail avec le DOCX joint, puis affichage de la traduction ; pour un PDF,
   la page affiche la dernière traduction.

Particularités conservées :

| Langue | Tesseract | GoogleTranslator |
| --- | --- | --- |
| Français | fra | fr |
| Anglais | eng | en |
| Italien | ita | it |
| Espagnol | spa | es |
| Japonais | jpn | ja |
| Chinois | chi_tra | zh-TW |

- `--oem 3 --psm 6` pour tous les PDF et uniquement l'image française.
- `timeout=10` transmis à la traduction, sauf pour le PDF français.
  La Phase 4 n'ajoute aucune garantie de délai absente du provider actuel.
- OCR vide ou `None` : arrêt sans fusion ni e-mail, avec la page historique
  de succès et son message d'absence de texte, distinct pour PDF et image.
- Les erreurs prévues de dépendance produisent une réponse 502. Une erreur
  de programmation inattendue reste visible. Un échec après sauvegarde conserve
  le document et consomme le quota ; aucun remboursement implicite.
- Les chemins et noms restent fondés sur l'utilisateur. Le nettoyage conserve
  sa différence de casse `tsukiyomi_doc`/`Tsukiyomi_doc` et intervient même en GET.

## Découpage et extractions progressives

Des fonctions suffisent : aucun état de service ne nécessite une classe,
une factory ou un framework d'injection. Seul le résultat du pipeline utilise
une petite dataclass immuable.

| Fichier | Modification et raison |
| --- | --- |
| `Tsukiyomi_app/services/__init__.py` | Package des responsabilités documentaires. |
| `services/notification.py` | Construction et envoi du message, destinataire, sujet, corps, pièce jointe et `fail_silently=False`. |
| `services/rendering.py` | Création avec le titre `TRADUIT PAR ZENIA`, sauvegarde et fusion des seules pages explicitement fournies, dans leur ordre. |
| `services/ocr.py` | Appel Tesseract et conservation des options historiques PDF/Image. |
| `services/languages.py` | Mappings des six langues centralisés, sans branche par langue dans le pipeline. |
| `services/translation.py` | Appel GoogleTranslator, cible française et paramètres historiques. |
| `services/extraction.py` | Lecture du nombre de pages, rasterisation Poppler, ouverture Pillow et déplacement du nettoyage existant. |
| `services/errors.py` | Une exception `DocumentProcessingError`, avec cause technique conservée ; interception limitée aux mêmes exceptions qu'en Phase 2. |
| `services/processor.py` | `process_document(document)` orchestre les étapes sans HTTP ni écriture en base. `ProcessingResult` porte la dernière traduction et le chemin envoyé, ou aucun artefact si l'OCR est vide. |
| `Tsukiyomi_app/views.py` | Formulaire, policy, contrôles de quotas, sauvegarde et réponses HTTP ; traduction de l'erreur métier en réponse 502. Passe de 1 202 à 166 lignes. |
| `Tsukiyomi_app/tests.py` | Seuls quatre chemins de mocks sont adaptés à leurs nouveaux modules propriétaires. Aucune assertion changée. |
| `Tsukiyomi_app/test_services.py` | Six tests directs du pipeline sans HTTP ni accès DB, avec fichiers/DOCX réels et dépendances externes simulées. |
| `docs/phase4_services_documentaires.md` | Audit, décisions, validation et limites de cette intervention. |

Les chemins `services/...` de ce tableau sont relatifs à `Tsukiyomi_app/`.
Chaque extraction a été suivie de la suite complète, avant de poursuivre :
notification, rendering, OCR, traduction, extraction documentaire, orchestrateur.
Les **44 tests existants passent à chacune de ces étapes**.

```text
get_televerse : HTTP, formulaire, UsagePolicy, quotas, sauvegarde
    |
    v
process_document(document)
    +-- extraction : PDF -> Poppler ; image -> Pillow
    +-- OCR : Tesseract
    +-- traduction : GoogleTranslator
    +-- rendering : DOCX et fusion
    `-- notification : e-mail du résultat complet
```

Le nettoyage reste appelé avant validation par la vue pour préserver son ordre
historique. Le processor reçoit un document déjà validé et sauvegardé ; il ne
contrôle pas de nouveau les quotas et ne sauvegarde ni ne supprime de ligne.
Une erreur coupe l'enchaînement. Les pages déjà écrites peuvent rester sur disque,
comme auparavant, mais aucun résultat partiel n'est fusionné puis envoyé.

## Compatibilité et base de données

Les routes `tele/`, `tele_free/`, `tele_paid/`, leurs préfixes historiques et
leurs protections restent inchangés. Authentification, formulaires, templates,
newsletter, administration, modèles et `UsagePolicy` sont conservés.

| Offre | PDF enregistrés | Pages par PDF | Images enregistrées |
| --- | ---: | ---: | ---: |
| Free | 2 | 5 | 3 |
| Paid | 10 | 30 | 15 |

`state_abonnement=False` sélectionne toujours Free, `True` Paid. Les usages
restent propres à chaque utilisateur/type et persistent après changement d'offre.

**Aucun modèle modifié. Aucune migration créée, modifiée ou supprimée.
Aucun schéma ni table PostgreSQL modifié. Aucune donnée existante supprimée.**
Les essais utilisent SQLite en mémoire et des répertoires temporaires ; aucun
traitement ni nettoyage n'est lancé sur les documents de développement.
Aucune dépendance ajoutée ou mise à jour. Aucun commit, push ou changement
d'historique Git effectué.

## Validation finale

```bash
python manage.py test --settings=Tsukiyomi_project.test_settings --noinput --buffer
python manage.py check --settings=Tsukiyomi_project.test_settings
python manage.py makemigrations --check --dry-run --settings=Tsukiyomi_project.test_settings
git diff --check
```

Résultats : **44 tests avant, 50 tests après, tous réussis**. Checks Django sans
problème ; migrations : `No changes detected` ; diff sans erreur d'espacement.
Les six nouveaux tests passent aussi isolément avec
`python manage.py test Tsukiyomi_app.test_services --settings=Tsukiyomi_project.test_settings --noinput --buffer`.

Ces tests supplémentaires protègent les options exactes des six langues pour
PDF/Image, les pièces jointes réelles, le dernier texte et l'ordre des pages,
l'OCR vide ou en erreur sur une page ultérieure, la fermeture des images en cas
d'erreur prévue ou inattendue et l'arrêt avant notification si le rendu échoue.

La revue des arbres syntaxiques confirme que les vues d'accueil, de newsletter,
d'offres et de suppression des médias sont inchangées. Elle confirme également
que les tests existants ne diffèrent que par leurs quatre chemins de mocks.
Les modèles, migrations, URLs, formulaires, templates, paramètres et dépendances
ne présentent aucun diff. Les validations n'incluent pas d'appels réels à
Google/SMTP/Tesseract/Poppler ni de tests d'intégration PostgreSQL.

## Hors périmètre

Restent pour les phases suivantes : isolation par job, correction du nettoyage
et des collisions entre requêtes, extraction native/adaptative des PDF,
segmentation et qualité littéraire, changement de provider, asynchronisme,
stockage objet, nettoyage des dépendances, Docker/CI/CD et billing. Aucune
préparation spéculative de ces fonctionnalités n'est introduite ici.
