# Phase 6B — Segmentation, provider et reconstruction

## Audit initial

Lecture des deux documents de référence situés dans le dossier parent :
`tsukiyomi_roadmap_refactorisation_finale.md` et
`tsukiyomi_parcours_backend_developer.md`, ainsi que du code et de la
documentation des phases précédentes. Dépôt initialement propre.
Baseline exécutée avant modification : **77 tests OK**.

Le projet est un monolithe Django à deux applications : comptes/authentification
dans `Tsukiyomi_account_app`, documents et newsletter dans `Tsukiyomi_app`.
`DocFile` conserve l'upload et son utilisateur ; les quotas free/paid de
`UsagePolicy` comptent ces documents. La vue valide le fichier et ses limites,
enregistre le document puis crée un `TranslationJob` synchrone. Un échec après
enregistrement consomme donc toujours le quota.

Le processor réserve le job par transition conditionnelle PENDING → PROCESSING.
Il copie la source dans `jobs/<uuid>/source`, écrit les intermédiaires dans
`working` et le résultat dans `output/translation.docx`. Les états, dates,
erreurs et résultat sont déjà suivis. Les tests protègent l'isolation des jobs,
y compris leurs traitements simultanés et le refus des doubles appels.

La Phase 6A est déjà réalisée : PyPDF2 extrait et valide le texte page par page,
puis Poppler/Tesseract interviennent uniquement pour les pages refusées. Les
images utilisent Pillow et Tesseract. La traduction Google est déjà isolée dans
`translation.py`, mais ne propose pas de contrat injectable. Le renderer reçoit
une chaîne par page ; la fusion utilise la liste explicite des pages DOCX.
L'e-mail est envoyé seulement après reconstruction complète.

Les erreurs attendues deviennent `DocumentProcessingError`, cause conservée ;
le job enregistre FAILED avec le seul type d'erreur, et la vue répond HTTP 502.
Les erreurs Python inattendues sont relancées. Une extraction vide termine
historiquement SUCCEEDED sans artefact ni e-mail. Les services emploient des
fonctions courtes et quelques dataclasses immuables : cette convention est
conservée, sans couche supplémentaire.

Les manques réels étaient les segments identifiables, le contrat du provider
et leur reconstruction. Les risques ciblés étaient la perte de contenu,
l'inversion des blocs/pages, les options historiques du provider et l'envoi
partiel après erreur. Aucun besoin de modification de schéma n'a été identifié.

## Fichiers et décisions

| Fichier sous `Tsukiyomi_app/` | Rôle |
| --- | --- |
| `services/segmentation.py` (nouveau) | Dataclass `Segment` immuable et segmentation déterministe. |
| `services/translation.py` | Contrat appelable `TranslationProvider` et traduction ordonnée des segments ; fonction Google existante conservée. |
| `services/rendering.py` | Rendu d'une séquence de segments en paragraphes, titres et dialogues ; séparateurs conservés. |
| `services/processor.py` | Injection optionnelle du provider, orchestration segmentation/traduction/rendu pour PDF et images. |
| `test_segmentation.py` (nouveau) | 17 tests supplémentaires avec sous-cas, sans supprimer ni modifier les tests existants. |

Cette note est le sixième fichier ajouté ou modifié. Aucun changement dans les
modèles, migrations, comptes, formulaires, vues, routes, templates, quotas,
configuration, dépendances, extraction, OCR, workspaces, gestion d'erreurs ou
notification. La fusion DOCX existante reste inchangée.

### Contrats

- Un segment porte `id`, `order`, `page_number`, `kind`, `source_text` et
  `translated_text`. Numérotation dès 1 dans chaque page ; identifiants
  `p0001-s0001`, `p0001-s0002`, `p0002-s0001`. L'image utilise la page 1.
  L'ordre documentaire est celui des pages puis des segments. Aucune persistance.
- Les lignes vides séparent les paragraphes. Les lignes ordinaires contiguës
  restent ensemble, avec leurs sauts de ligne internes. Les fins de ligne sont
  normalisées en LF ; les espaces internes, signes et caractères sont conservés.
- Seuls les titres à marqueur Markdown explicite (`#` à `######`) sont reconnus.
  Les dialogues sont des lignes à tiret cadratin/demi-cadratin suivi d'un espace
  ou entièrement délimitées par `« »`, `“ ”`, `「 」`, `『 』`. Les séparateurs
  répètent au moins trois fois un même signe parmi `* _ = - — ※ ★ ☆`, avec
  éventuellement des espaces. Un bloc incertain reste un paragraphe.
- `TranslationProvider` est un `Protocol` appelable :
  `provider(text, language, *, is_pdf=False) -> str`. La fonction existante
  `translate_text` est son unique implémentation réelle. Une fonction ou un mock
  peut être passé à `process_document(job, provider=...)`, sans constructeur
  Google dans l'orchestrateur. Aucun provider supplémentaire ni factory.
- Le mapping des six langues, la cible `fr` et `timeout=10` sont conservés,
  ainsi que l'absence historique de cet argument pour le PDF français. Les
  erreurs suivent le mécanisme existant ; aucun retry ou fallback n'est ajouté.
- La traduction produit de nouveaux segments avec les mêmes identifiants,
  ordres, types et sources. Les séparateurs ne sont pas envoyés au provider.
- `write_docx` reçoit désormais les segments ordonnés : titre en `Heading 1`,
  dialogue en `Quote`, autres blocs en paragraphes ordinaires. Les séparateurs
  reprennent leur source. Un segment traduisible sans traduction (`None`) est
  refusé avant sauvegarde. Le titre historique `TRADUIT PAR ZENIA` reste présent
  pour chaque page, et la fusion conserve son ordre explicite.
- `ProcessingResult.text` reste le texte de la dernière page : ses segments
  traduits sont réunis avec deux sauts de ligne. Une page uniquement blanche
  produit maintenant zéro segment et suit le parcours historique « aucun texte »
  (SUCCEEDED sans artefact ni e-mail), y compris après une première page traitée.

## Validation exécutée

Commandes exécutées avec le Python du `venv` du projet :

```bash
python manage.py test Tsukiyomi_app.test_services Tsukiyomi_app.test_jobs Tsukiyomi_app.test_extraction --settings=Tsukiyomi_project.test_settings --noinput --buffer
python manage.py test Tsukiyomi_app.test_segmentation --settings=Tsukiyomi_project.test_settings --noinput --buffer
python manage.py check --settings=Tsukiyomi_project.test_settings
python manage.py test --settings=Tsukiyomi_project.test_settings --noinput --buffer
python manage.py makemigrations --check --dry-run --settings=Tsukiyomi_project.test_settings
git diff --check
```

Résultats : **33 tests historiques ciblés OK ; 17 nouveaux tests OK ;
94 tests au total OK**. Check Django sans problème ; migrations :
**No changes detected** ; diff sans erreur d'espacement.

Les nouveaux tests couvrent paragraphes, identifiants, ordre, blancs, marqueurs,
titres prudents, dialogues, séparateurs, japonais/chinois et conservation du
contenu. Ils vérifient le contrat injectable pour les six langues, les sources
et métadonnées inchangées, les erreurs attendues et les erreurs Python.
Le rendu est vérifié par relecture de vrais DOCX et de leurs styles.

Les scénarios complets numérique/scanné/hybride/image vérifient les segments
reçus par le renderer, les appels provider, l'ordre multipage, la pièce jointe,
l'état du job et le texte retourné. Le scénario hybride n'OCRise que la page 2.
Un échec sur un segment ultérieur, après une page déjà rendue pour les PDF,
interdit tout artefact final et toute notification. Les tests historiques
conservent la couverture HTTP, quotas, six langues et options Google/Tesseract,
OCR, rendu, fusion, notification, erreurs, isolation et concurrence.

Tests exécutés sur SQLite de test et dossiers temporaires. Google et SMTP sont
simulés ; le fixture de pipeline interdit les connexions réseau et processus
externes. PDF et DOCX sont réellement écrits/lus, Poppler/Tesseract simulés.
Aucune validation d'intégration réelle Google, SMTP, OCR ou PostgreSQL pour
cette phase. Revue du diff complet, nouveaux fichiers inclus ; aucun test
historique supprimé ou assoupli. Aucun modèle/table modifié, aucune migration
créée ou appliquée à la base applicative, aucune dépendance ajoutée.

## Limites

La structure dépend des sauts de ligne fournis par l'extraction. Un titre sans
marqueur explicite reste un paragraphe ; un dialogue étalé sur plusieurs lignes
n'est pas interprété. Les marqueurs de titre/dialogue sont conservés dans le
texte envoyé au provider, sans interpréteur Markdown. La multiplicité des
lignes vides, les colonnes, les polices et la mise en page graphique ne sont
pas reproduites. Il n'y a ni NLP, ni mémoire, ni contexte inter-segments.

Un paragraphe très long reste soumis aux limites existantes du provider ; aucun
découpage par taille, batching, cache ou optimisation réseau n'est introduit.
Le traitement reste synchrone sur disque local. L'intégration réelle des
services externes et l'évaluation linguistique restent à effectuer sur un corpus
représentatif. Les limites déjà documentées des quotas et notifications restent
hors périmètre.
