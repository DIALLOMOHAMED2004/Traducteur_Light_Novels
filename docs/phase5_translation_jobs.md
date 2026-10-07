# Phase 5 — TranslationJob et isolation des fichiers

## Audit initial

Dépôt initialement propre. Audit avant modification : arborescence, modèles et
migrations des deux applications, vues, formulaires, UsagePolicy, tous les
services, tests, settings, URLs, administration, templates utiles et documents
de `docs/`, particulièrement la Phase 4. Les deux documents
`../tsukiyomi_roadmap_refactorisation_finale.md` et
`../tsukiyomi_parcours_backend_developer.md` ont également été consultés.
Baseline : **50 tests réussis**.

Le parcours existant authentifie l'utilisateur, valide `DocumentForm`, contrôle
les quotas par utilisateur/type et le nombre de pages, puis sauvegarde `DocFile`.
Ce modèle conserve l'upload sous `MEDIA_ROOT/media/` et sert au comptage des
quotas. Un échec après sauvegarde consomme toujours le quota.

`process_document(document)` orchestre les services de Phase 4 sans HTTP :
Poppler à 300 dpi pour les PDF, OCR, traduction Google en français, DOCX avec
`TRADUIT PAR ZENIA`, fusion dans l'ordre explicite et e-mail à l'utilisateur.
Les images passent par Pillow. Les six mappings, options OCR et particularités
du paramètre de traduction `timeout` sont conservés.

Problèmes confirmés : dossiers rasterisés `media/mediaby<username>`, dossiers
DOCX `repository-<username>` / `repositoryImg-<username>` et noms de résultats
réutilisés. `cleanup_previous_files()` supprime récursivement des dossiers
partagés, intervient même en GET et utilise une casse différente pour les DOCX.
Il peut supprimer les rasterisations d'un traitement en cours. Aucun de ces
nettoyages n'a été exécuté sur les fichiers réels.

## Changements limités

| Fichier | Intervention |
| --- | --- |
| `Tsukiyomi_app/models.py` | Ajout de `TranslationJob` uniquement. |
| `Tsukiyomi_app/migrations/0009_translationjob.py` | Une seule opération `CreateModel(TranslationJob)`. |
| `Tsukiyomi_app/services/workspace.py` | Petite dataclass de chemins, calcul par UUID et copie de la source. |
| `Tsukiyomi_app/services/processor.py` | Cycle de vie persistant et orchestration dans le workspace du job. |
| `Tsukiyomi_app/services/extraction.py` | Rasterisation dans le dossier reçu ; retrait du nettoyage par utilisateur. |
| `Tsukiyomi_app/views.py` | Création du job après sauvegarde du document, appel du processor, retrait du nettoyage en entrée. |
| `Tsukiyomi_app/tests.py`, `Tsukiyomi_app/test_services.py` | Adaptations internes des tests historiques aux jobs et nouveaux chemins. |
| `Tsukiyomi_app/test_jobs.py` | Douze nouveaux tests de Phase 5, avec sous-cas. |
| `docs/phase5_translation_jobs.md` | Audit, décisions, validation et limites. |

Le job porte une clé primaire UUID native, deux clés étrangères (`user`,
`source` vers `DocFile`), les langues source/cible, le statut, les dates de
création/début/fin et une erreur courte. `output_file` conserve uniquement le
chemin relatif du DOCX dont le traitement et l'envoi ont terminé sans exception.
La cible reste exclusivement le français ; aucun nouveau choix de traduction.
Les langues du job décrivent le traitement lors de sa création.

**Aucune définition de modèle existant ni migration historique modifiée.**
Les relations nouvelles résident dans la nouvelle table. Aucun backfill des
anciens documents. Aucune migration appliquée à PostgreSQL pendant l'intervention.
Pour utiliser cette version hors tests, appliquer la migration additive avec
`python manage.py migrate` dans l'environnement habituel configuré.

## Isolation et nettoyage

```text
MEDIA_ROOT/jobs/<job_uuid>/
    source/source.pdf        # ou source.png / source.jpg / source.PDF
    working/                 # rasterisations Poppler, page_0000.docx, ...
    output/translation.docx
```

`workspace_for(job)` fournit `source_dir`, `working_dir` et `output_dir`.
Le processor lit une copie de l'upload dans `source/`. Cette copie évite de
modifier le champ, le chemin ou le fichier d'origine de `DocFile` et rend la
source indépendante pour chaque job, au prix d'une copie disque supplémentaire.
La création exclusive du workspace refuse de réutiliser un dossier existant.

Tous les fichiers produits sont sous l'UUID ; aucune recherche de fichiers
par username ni fusion d'un répertoire entier. La fusion garde la liste des
pages du job dans l'ordre numérique. Les anciens dossiers restent intacts.

Le pipeline ne supprime désormais aucun fichier : le nettoyage historique est
retiré, sans remplacement par une purge automatique. Les fichiers intermédiaires
restent dans `working/`, y compris après échec ou OCR vide. Aucune suppression
globale n'est nécessaire pour éviter une collision ; une future politique de
rétention devra cibler explicitement les jobs. La route administrative de
suppression historique reste inchangée et ne cible pas `MEDIA_ROOT/jobs/`.

## Statuts et erreurs

1. Après validation et sauvegarde de `DocFile` : création du job `PENDING`.
2. `process_document(job)` effectue une transition conditionnelle en base vers
   `PROCESSING` et renseigne `started_at` avant la copie et les dépendances.
   Un même job déjà commencé ne peut pas être exécuté une seconde fois, même
   à travers une instance Python ancienne. Ce contrôle n'introduit aucun retry.
3. Traitement et envoi terminés : `SUCCEEDED`, `finished_at`, chemin final.
4. Exception : `FAILED`, `finished_at`, champ d'artefact vide, puis propagation.

`document_errors()` continue de convertir les erreurs prévues en
`DocumentProcessingError`, avec leur cause intacte ; la vue garde sa réponse
502. Seul le nom de classe de la cause est persisté : pas de texte OCR, message
fournisseur, adresse e-mail ou chemin privé. Une erreur Python inattendue est
également tracée, puis relancée telle quelle ; elle n'est jamais absorbée.

Un échec SMTP peut laisser un DOCX sur disque, mais le job est `FAILED` et ne
déclare aucun artefact réussi. OCR vide ou `None`, même après une page traduite :
`SUCCEEDED` sans artefact, sans fusion ni e-mail, avec le message HTTP historique
d'absence de texte. Ce statut désigne la fin normale du traitement, sans garantir
qu'un texte ait été détecté. Les templates et leurs libellés restent inchangés.

## Tests et compatibilité

Les douze nouveaux tests couvrent UUID, relations, langues, dates, statut initial,
état `PROCESSING` observé en base avant les dépendances et l'e-mail, succès
PDF/Image et copie exacte de la source. Ils couvrent aussi les erreurs de copie,
extraction, OCR, traduction, rendu, fusion et notification, la cause préservée,
l'erreur enregistrée sans données sensibles, les bugs relancés et l'OCR vide.

L'isolation PDF/PDF, Image/Image et PDF/Image est vérifiée par comparaison des
fichiers octet par octet et lecture des DOCX réels. Un test utilise deux threads :
le job A est suspendu pendant l'OCR, B termine, puis A reprend ; les deux travaux
se chevauchent sans modification des fichiers de l'autre. Les doubles appels du
même job sont refusés pendant et après le traitement. Autres contrôles : échec
de B sans altération de A, workspace existant protégé, création HTTP après
sauvegarde, refus de validation/pages/quota sans job, GET sans nettoyage.

Adaptations nécessaires des tests historiques, sans suppression de test métier :

- Les six tests directs du processor passent de `SimpleTestCase` à `TestCase`
  et fournissent un job/document/utilisateur persistants. Ils restent sans HTTP.
- Les assertions de chemins Poppler attendent la copie sous `source/` et le
  dossier `working/`, avec les mêmes DPI et options externes.
- La sélection du nouvel upload vérifie sa relation au job, le dossier source
  de ce job et l'égalité des octets avec le document courant.
- Les assertions d'absence de résultat recherchent `output/*.docx` au lieu des
  anciens noms `trad_fusion_*.docx`, devenus obsolètes.

## Validation obtenue

```bash
python manage.py test Tsukiyomi_app.test_jobs --settings=Tsukiyomi_project.test_settings --noinput --buffer
python manage.py test --settings=Tsukiyomi_project.test_settings --noinput
python manage.py check --settings=Tsukiyomi_project.test_settings
python manage.py makemigrations --check --dry-run --settings=Tsukiyomi_project.test_settings
git diff --check
```

Résultats : **12 nouveaux tests ciblés OK ; 62 tests au total OK**. Check Django
sans problème, `No changes detected`, diff sans erreur d'espacement. Revue du
diff complet et comparaison des arbres syntaxiques : `DocFile`, `Subscriber`
et les vues hors upload sont inchangés. Aucun diff des modèles de comptes,
migrations historiques, formulaires, quotas, routes, templates, administration,
settings ou dépendances.

Exécution exclusivement sur SQLite de test et répertoires temporaires. Réseau
et sous-processus interdits dans les tests documentaires ; Google, Tesseract,
Poppler et SMTP simulés. Copie, génération, fusion et lecture des DOCX réelles.
Pas de validation d'intégration PostgreSQL/OCR/Google/SMTP. Aucune donnée réelle
supprimée ou déplacée, aucun commit/push effectué.

## Limites conservées et phases suivantes

Traitement synchrone, disque local, quota basé sur `DocFile`, cible française et
OCR systématique conservés. Aucun worker, queue, stockage objet, progression,
retry, billing, nouveau provider, segmentation ou système littéraire introduit.
Pas de nouvel écran de suivi ni de politique de rétention.

Hors périmètre observé : comptage/sauvegarde des quotas non atomiques, nettoyage
administratif historique, libellé de succès trompeur pour OCR vide et absence
de délai réseau garanti par le provider. Aucun correctif opportuniste.
Un arrêt brutal du processus peut laisser un job `PROCESSING` ; la reprise et
la réconciliation après panne restent futures. L'e-mail et la base ne forment
pas une transaction commune : aucune garantie de livraison exactement une fois.
