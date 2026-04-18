# Tsukiyomi003 bY zEnIa

[Application WEB pour la traduction de tes documents , image au format png et jpg ]
le code source vous est accessible et vous pouvez le tester sans soucis.
il suffit de cloner ce depot et de preparer votre environnement .



## Etape 1 [Cloner le dépot]
NB: Python et PostgreSQL doivent être installés

--> initialiser la base de donnees (initdb -D \usr\local\pgsql\data) puis (pg_ctl -D \usr\local\pgsql\data start) pour lancer le serveur de base de données. \n
--> création de votre environnement virtuel (python -m virtualenv nom_environnement)\n
--> activer son environnement ( cd chemin_vers_environnement\scripts) puis (activate.bat)\n
--> cloner le depot (git clone chemin_vers_depot.git)\n
--> ouvrir le dossier du depot (cd depot)\n
--> installer les dependances (python -m pip install -r requirements.txt)\n
-->demarrer le serveur local (python manage.py runserver )\n
--> tester l'application

## Enjoy :)

[Img illustration](folder_img/tsukiyomi.PNG)








