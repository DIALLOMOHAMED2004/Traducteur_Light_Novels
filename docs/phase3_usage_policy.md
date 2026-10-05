# Phase 3 — UsagePolicy et pipeline Free/Paid commun

## Audit avant modification

État initial propre, sans modifications locales. Lecture des applications,
modèles, formulaires, vues, routes, templates, tests, migrations et documents
de `docs/` avant modification. La suite existante passe : **42 tests**.

- `Tsukiyomi_account_app` gère `UserTsukiyomi` et l'authentification.
  Son booléen `state_abonnement` distingue Free (`False`) et Paid (`True`).
- `Tsukiyomi_app` gère `DocFile`, `Subscriber`, le téléversement, le traitement
  synchrone et la newsletter. `DocumentForm` contrôle type, langue, extension,
  contenu, taille et dimensions avant toute sauvegarde.
- `get_televerse` et `get_televerse2` contiennent respectivement 958 et 956 lignes.
  La comparaison de leurs arbres syntaxiques confirme les mêmes traitements :
  formulaire préfixé `pi`, comptage par utilisateur/type, lecture des pages,
  sauvegarde, Poppler à 300 dpi, OCR, traduction en français, DOCX, fusion
  numérique et e-mail. Même gestion des erreurs de Phase 2.
- Les différences exécutables sont les décorateurs d'accès, les trois limites,
  les messages de quota/offre et des traces console (dont des points de suspension).
  Aucune différence documentaire supplémentaire à normaliser.
- Les branches de langues, identiques entre offres, restent distinctes dans
  chaque parcours PDF/Image. Leurs particularités sont conservées : configuration
  OCR explicite pour tous les PDF et l'image française, absence de `timeout=10`
  pour la traduction du PDF français, codes OCR et GoogleTranslator existants.
- Les quotas portent sur les documents enregistrés, sans période. Un échec
  externe après sauvegarde consomme toujours une place. Un changement d'offre
  ne supprime ni ne remet à zéro les documents existants.
- `return_type_televerse` ne faisait que rediriger vers Free/Paid. Les deux
  décorateurs spécialisés n'étaient employés que par ces deux vues. Les deux
  formulaires HTML étaient identiques, hormis leur action.
- Les routes sont incluses sous plusieurs préfixes dans les URLs du projet.
  Les liens d'accueil, de succès et d'offres utilisent déjà `televerse_url`.
  Le test du retour après login utilise encore l'ancienne route gratuite.

Les tests métier protègent les anonymes, les restrictions des anciennes routes,
la validation, les bornes inclusives des quotas/pages, la séparation des usages,
les changements d'offre, les erreurs OCR/traduction/Poppler/e-mail, l'OCR vide,
l'absence d'envoi partiel, les six langues, le nouveau document sélectionné,
les DOCX réels et leur ordre. Les tests d'authentification, de suppression des
médias et de newsletter doivent également rester inchangés.
Seule la redirection de `tele/` vers une route d'offre impose l'ancienne architecture.

## Modifications limitées

| Fichier | Changement et raison |
| --- | --- |
| `Tsukiyomi_app/usage_policy.py` (ajout) | Dataclass immuable à trois champs, deux constantes et sélection par `state_abonnement`, sans modèle Django. |
| `Tsukiyomi_app/views.py` | `get_televerse` devient commun, protégé par `login_required`, avec trois contrôles issus de la policy. Suppression de `get_televerse2` et du routeur `return_type_televerse`. |
| `Tsukiyomi_app/urls.py` | `tele/` appelle directement la vue commune ; les anciennes routes appellent la même vue avec leurs décorateurs existants. |
| `Tsukiyomi_app/templates/tsukiyomi_app/televerse_page.html` | Un formulaire unique vers `televerse_url`, avec mêmes champs, CSRF, styles et erreurs. |
| `Tsukiyomi_app/tests.py` | Les uploads métier passent par la route commune ; adaptation du test de routage ; deux tests ajoutés pour la policy et les POST historiques. |
| `docs/phase3_usage_policy.md` (ajout) | Audit, décisions de compatibilité et validation. |

Aucun fichier supprimé. Les refus historiques des URLs spécialisées sont
conservés, y compris leurs templates et statut 200. `views_abonnement.py` reste
donc inchangé et sert uniquement à cette compatibilité. Aucun traitement
documentaire n'y est déplacé. Aucun second moteur n'est conservé.

Le message de dépassement des pages utilise maintenant la limite de la policy
et « pages maximum », cohérent avec la borne inclusive déjà appliquée.
Le message de quota PDF reprend également la limite de la policy.

Aucun test métier supprimé ni assertion métier relâchée. Le test renommé
`test_common_form_and_legacy_access_restrictions` remplace la redirection
obsolète par l'affichage du formulaire commun, en gardant les refus GET/POST
de l'offre incompatible. Les deux nouveaux tests vérifient la sélection
Free/Paid/Free et les anciens POST PDF/Image jusqu'au quota, avec DOCX joint
et refus d'un upload supplémentaire sur la route commune.

## Quotas et base de données

| Offre | PDF enregistrés | Pages par PDF | Images enregistrées |
| --- | ---: | ---: | ---: |
| Free | 2 | 5 | 3 |
| Paid | 10 | 30 | 15 |

Aucune table modifiée. Aucune migration créée.
Modèles, champs (dont `state_abonnement`) et migrations existantes inchangés.
Aucune connexion PostgreSQL nécessaire : les tests utilisent exclusivement
la configuration existante avec SQLite en mémoire et fichiers temporaires.
Aucun billing, service métier de Phase 4 ni dépendance supplémentaire.

## Validation

Commandes exécutées avec le Python de l'environnement existant :

```bash
python manage.py test --settings=Tsukiyomi_project.test_settings --noinput --buffer
python manage.py check --settings=Tsukiyomi_project.test_settings
python manage.py makemigrations --check --dry-run --settings=Tsukiyomi_project.test_settings
git diff --check
```

Résultats : **42 tests OK avant modification, 44 tests OK après modification**,
checks Django sans problème, `No changes detected`, diff sans erreur d'espacement.
Les dépendances externes restent simulées ; génération, fusion et lecture des
DOCX restent réelles. Pas de validation d'intégration OCR/Google/SMTP/PostgreSQL.

La revue compare aussi les arbres syntaxiques des 12 branches PDF/Image/langue
à chacune des deux anciennes vues : identiques hors traces console. Les vues
de newsletter, d'accueil, d'offres et de suppression sont inchangées.

## Limites conservées hors périmètre

La vue commune reste volumineuse et conserve ses branches par langue : aucune
extraction de services de Phase 4. Les dossiers partagés par utilisateur, les
risques de collisions concurrentes et le nettoyage historique avec différence
de casse `tsukiyomi_doc`/`Tsukiyomi_doc` ne sont pas modifiés. L'OCR vide garde
la page historique de succès sans traduction ni e-mail. Aucun correctif
opportuniste n'est inclus.
