# Phase 2 — Tests de caractérisation et corrections fonctionnelles

Intervention fondée sur `tsukiyomi_roadmap_refactorisation_finale.md` (Phase 2)
et `tsukiyomi_parcours_backend_developer.md` (chantiers 3 et 4), fournis dans le
dossier parent du dépôt. Audit effectué avant les modifications fonctionnelles.

## Architecture et comportement observés

- `Tsukiyomi_account_app` : utilisateur personnalisé `UserTsukiyomi`, inscription,
  connexion, déconnexion. `state_abonnement=False` sélectionne l'offre gratuite,
  `True` l'offre payante ; `state` ne pilote pas les quotas.
- `Tsukiyomi_app` : `DocFile` appartient à un utilisateur et conserve le type,
  la langue, le fichier et la date d'upload. `Subscriber` conserve une adresse
  unique et sa date d'inscription.
- `DocumentForm` valide avant sauvegarde : extension, contenu lisible, taille
  maximale de 20 × 1024 × 1024 octets, PDF non vide, dimensions d'image au plus
  20 000 pixels par côté et surface au plus 40 000 000 pixels. Les bornes sont
  inclusives. Extensions acceptées : `.pdf`, `.PDF`, `.jpg`, `.png`.
- Les décorateurs free/paid imposent déjà l'authentification. Un abonnement
  incompatible affiche le template de refus existant avec un statut 200.
  `return_type_televerse` redirige vers la vue correspondant au booléen.
- Le formulaire d'upload utilise le préfixe `pi` et `profileType=pdf_img`.
  Un formulaire invalide n'enregistre aucun document et ne lance pas le pipeline.
- `get_televerse` et `get_televerse2` restent deux vues distinctes. Elles comptent
  les documents de l'utilisateur par type, contrôlent les pages PDF puis
  enregistrent un `DocFile`. Aucun quota journalier ni remise à zéro automatique
  n'est implémenté.
- PDF : `PdfReader` compte les pages ; `convert_from_path`/Poppler rasterise à
  300 dpi ; Tesseract extrait le texte de chaque page ; GoogleTranslator traduit
  en français ; python-docx produit les pages puis un DOCX fusionné.
- Image : Pillow ouvre l'image ; Tesseract extrait le texte ; GoogleTranslator
  traduit ; un DOCX est produit. Aucun remplacement de ces bibliothèques.
- Les langues proposées sont français, anglais, italien, espagnol, japonais et
  chinois. Les codes OCR restent `fra`, `eng`, `ita`, `spa`, `jpn`, `chi_tra`.
- Le DOCX est joint à un `EmailMessage` adressé à l'utilisateur du document.
  La page de succès affiche la traduction (la dernière page dans le cas PDF).
  La conversion DOCX vers PDF est commentée dans le code existant.
- La newsletter est publique : le subscriber est enregistré avant l'envoi
  du message de bienvenue. Ce caractère public est conservé ; le contrôle des
  anonymes concerne le pipeline documentaire.
- Les URLs existantes comportent plusieurs préfixes incluant les mêmes routes.
  Elles n'ont pas été restructurées.

### Quotas vérifiés dans le code et dans l'image des offres

| Offre | PDF enregistrés maximum | Pages par PDF maximum | Images enregistrées maximum |
| --- | ---: | ---: | ---: |
| Gratuite | 2 | 5 | 3 |
| Payante | 10 | 30 | 15 |

Les comparaisons avant sauvegarde `<= 1`, `<= 9`, `<= 2`, `<= 14` autorisent
respectivement le deuxième/dixième PDF et la troisième/quinzième image.
Il n'y a donc pas de décalage d'une unité à corriger. Les quotas et la validation
existante de `DocumentForm` n'ont pas été modifiés.

### Fichiers utilisés

- Uploads : `MEDIA_ROOT/media/`, normalement `media_upload/media/`.
- Images rasterisées : chemin relatif `media_upload/media/mediaby<username>/`.
- Pages DOCX : `Tsukiyomi_doc/repository-<username>/trad_fr<index>.docx`.
- Fusion : même dossier, `trad_fusion_<username>.docx`.
- Images traduites : `Tsukiyomi_doc/repositoryImg-<username>/trad_fr.docx`.
- Le nettoyage historique référence aussi `tsukiyomi_doc/` avec une minuscule,
  contrairement aux chemins de génération. Il reste hors de cette correction.

## Défauts reproduits et corrections

| Défaut confirmé | Test de régression | Correction minimale |
| --- | --- | --- |
| Login personnalisé : réponse 200 malgré authentification réussie | `test_valid_login_redirects_to_home` | Retourner `redirect('reindex')` |
| Login natif : champs absents après redirection anonyme | `test_anonymous_redirect_leads_to_usable_login_form` | Afficher également `form.as_p` dans le template partagé |
| Login natif : destination par défaut `/accounts/profile/` inexistante | `test_native_login_without_next_redirects_to_home` | `LOGIN_REDIRECT_URL = 'reindex'` |
| Formulaire natif envoyé à la vue personnalisée, perdant `next` | `test_native_login_form_returns_to_requested_page_after_invalid_then_valid_login` | Poster vers `request.path` et conserver `next` dans un champ caché |
| Newsletter : 19 messages pour `reader@example.test`, un destinataire par caractère | `test_public_subscription_sends_to_one_complete_address` | Une seule liste contenant l'adresse complète |
| Newsletter : erreurs de formulaire perdues et erreurs SMTP non présentées | Tests invalidité/doublon et erreur d'envoi | Conserver le formulaire lié, afficher une erreur non liée à un champ et retourner 502 en cas d'échec SMTP |
| Ancien PDF/image sélectionné avec dates identiques et ordre de requête différent | `test_newly_uploaded_document_is_processed_among_existing_documents` | Utiliser directement le `DocFile` qui vient d'être enregistré |
| Fusion désordonnée incluant des résultats anciens | `test_docx_pages_remain_in_numeric_order_and_exclude_previous_results` | Lire uniquement `trad_fr0.docx` à `trad_fr<N-1>.docx`, dans cet ordre |
| Codes GoogleTranslator rejetés par le constructeur installé | `test_all_six_languages_work_for_pdf_and_image_in_both_plans` | `it`, `es`, `ja`, `zh-TW` ; chinois traditionnel cohérent avec l'OCR `chi_tra` |
| Exception de traduction interceptée puis variable non initialisée / traitement poursuivi | Tests d'erreurs provider et d'erreur sur une page ultérieure | Retirer les interceptions incomplètes et laisser remonter vers la réponse d'erreur commune |
| Exceptions Poppler, OCR et SMTP non contrôlées | Tests d'erreurs propres à chaque dépendance | Un petit décorateur local aux deux vues intercepte les exceptions connues, journalise leur type et retourne 502 |

Les tests concernés ont été exécutés avant correction : échecs observés pour
les destinations de login, destinataires, erreurs, mauvais fichiers sources,
ordre/contenu du DOCX et codes de langues. Ils passent après correction.

Le décorateur d'erreurs ne crée ni service, ni pipeline commun, ni policy. Il est
placé après le contrôle d'accès et ne capture pas toutes les exceptions Python.
Un test vérifie notamment qu'une `ValueError` inattendue reste détectable.
L'échec externe ne déclenche pas les étapes suivantes ; une erreur sur la seconde
page ne provoque ni fusion ni envoi d'un résultat partiel. Les erreurs ne sont
pas transformées en succès. Les images ouvertes sont fermées par un contexte.

## Exécution reproductible et isolement

Depuis la racine du dépôt, avec l'environnement Python existant :

```bash
venv/bin/python manage.py test --settings=Tsukiyomi_project.test_settings --buffer
```

Ou, dans un shell dédié aux tests :

```bash
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=Tsukiyomi_project.test_settings
python manage.py test
```

La configuration dédiée utilise une base SQLite **en mémoire** gérée par Django,
les migrations existantes, une clé de test et le backend e-mail en mémoire.
Elle n'ouvre aucune connexion PostgreSQL. Ne pas utiliser cette configuration
pour servir l'application. La configuration PostgreSQL habituelle n'est pas
remplacée ; il faut sélectionner explicitement les paramètres de test ci-dessus.

Les tests documentaires changent temporairement le répertoire de travail vers
un `TemporaryDirectory` et redéfinissent `MEDIA_ROOT`. Cela isole aussi les
chemins relatifs encore présents dans les vues. Le répertoire de travail et les
paramètres sont restaurés avant la suppression du répertoire temporaire.
Les fichiers existants de développement ne sont ni utilisés ni supprimés.

Dépendances simulées : conversion Poppler, OCR Tesseract, traduction Google,
envoi `EmailMessage.send()` et newsletter `send_mass_mail()`. Les tests de langues
utilisent le constructeur réel GoogleTranslator pour valider les codes, mais
simulent sa méthode de traduction. Les tests documentaires interdisent aussi
l'ouverture de connexions réseau et le lancement de sous-processus.

Les PDF/PNG/JPG sont fabriqués pendant les tests. La génération, la fusion et la
lecture des DOCX joints restent réelles. Aucun logiciel OCR, serveur SMTP,
service Google ou document de développement n'est nécessaire.

### Couverture et résultats

42 méthodes de test, avec sous-cas couvrant notamment :

- authentification valide/invalide/inactive, inscription, déconnexion et deux logins ;
- soumission de l'action et des champs HTML réels avec CSRF actif : retour vers
  la page demandée (paramètres de requête compris), conservation après mot de passe
  invalide, maintien du login personnalisé et refus d'une destination externe ;
- anonymes en GET/POST, mauvais abonnement en GET/POST, routage free/paid ;
- PDF/JPG/PNG, fichier corrompu, faux contenu, extension invalide, PDF sans page ;
- frontières de taille, dimensions et surface d'image, decompression bomb ;
- frontières des quatre quotas de fichiers et des deux limites de pages ;
- séparation des quotas par utilisateur/type et conservation lors d'un changement d'offre ;
- résultat OCR vide ou `None`, erreurs OCR/Poppler/provider/SMTP ;
- 24 parcours langue/type/offre, DOCX réel et pièce jointe ;
- sélection exacte du nouvel upload malgré les documents antérieurs ;
- ordre de 3 et 12 pages, présence de fichiers résiduels et ancien DOCX fusionné ;
- newsletter publique, adresse complète, doublon/invalide, erreur d'envoi ;
- protection de la route de suppression (sans exécuter de suppression autorisée réelle).

Commandes de validation exécutées :

```bash
DJANGO_SETTINGS_MODULE=Tsukiyomi_project.test_settings venv/bin/python manage.py test --noinput --buffer
DJANGO_SETTINGS_MODULE=Tsukiyomi_project.test_settings venv/bin/python manage.py check
DJANGO_SETTINGS_MODULE=Tsukiyomi_project.test_settings venv/bin/python manage.py makemigrations --check --dry-run
git diff --check
```

Résultats : **42 tests OK**, contrôles Django sans problème, **No changes detected**
pour les migrations et aucun défaut de whitespace dans le diff.
Des suites ciblées ont également été exécutées après chaque correctif.
La vérification n'est pas une validation d'intégration du moteur PostgreSQL,
d'un vrai OCR, de la qualité Google ou de la délivrabilité SMTP.

## Limites connues volontairement conservées

- Deux vues free/paid et branches de langues dupliquées : Phase 3 et suivantes.
- Dossiers et noms partagés par utilisateur : collisions possibles entre requêtes
  simultanées ; isolation par job reportée conformément à la roadmap.
- Nettoyage existant par suppression récursive, y compris défaut de casse des
  chemins ; aucune exécution sur les dossiers réels pendant cette intervention.
- Le `DocFile` est enregistré avant les appels externes : un échec consomme donc
  toujours le quota. Ni remboursement, suppression ni nouvelle règle métier.
- Les messages disent « moins de 05/30 pages » alors que le code et les offres
  autorisent exactement 5/30 pages. La borne inclusive est protégée.
- OCR vide : la page historique de succès affiche le message d'absence de texte,
  sans traduction ni e-mail ; son libellé général reste trompeur. Aucun redesign.
- Newsletter : le subscriber est conservé si l'envoi de bienvenue échoue ; pas de
  mécanisme de retry ou de désinscription ajouté. Son message de succès historique
  reste dans un commentaire HTML ; les erreurs de formulaire sont visibles.
- `timeout=10` transmis à `GoogleTranslator.translate()` n'est pas propagé par la
  bibliothèque installée à `requests.get()` : aucun délai réseau garanti ajouté.
- Les endpoints et l'organisation des URLs existants sont conservés.

## Fichiers concernés et garanties

- `Tsukiyomi_account_app/views.py` : return du login.
- `Tsukiyomi_account_app/templates/tsukiyomi_account_app/login.html` : formulaire natif, action cohérente et conservation de `next`.
- `Tsukiyomi_account_app/tests.py` : tests d'authentification.
- `Tsukiyomi_app/views.py` : correctifs documentaires/newsletter.
- `Tsukiyomi_app/tests.py` : tests formulaires, accès, quotas, pipeline et newsletter.
- `Tsukiyomi_project/settings.py` : destination du login natif.
- `Tsukiyomi_project/test_settings.py` : exécution isolée des tests.
- `docs/phase2_tests_et_correctifs.md` : audit, décisions, commandes et limites.

Aucun modèle, champ, relation, fichier de migration ou schéma PostgreSQL modifié.
Aucune migration créée et aucune donnée PostgreSQL utilisée ou supprimée.
Aucune dépendance ajoutée ou mise à jour. Aucun `UsagePolicy`, pipeline fusionné,
service métier, `TranslationJob`, worker ou autre fonctionnalité de Phase 3 ou
ultérieure introduit. Aucun commit ni push réalisé pour cette intervention.
