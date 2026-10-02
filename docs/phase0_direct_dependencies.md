# Dépendances directes utilisées pour la baseline

- Django==5.2.7
- deep-translator==1.11.4
- docx2pdf==0.1.8 — import actuel conservé provisoirement ; conversion non supportée sous Linux
- pdf2image==1.17.0
- pillow==11.3.0
- psycopg2-binary==2.9.11
- PyPDF2==3.0.1
- pytesseract==0.3.13
- python-docx==1.2.0

## Dépendances du requirements.txt non installées volontairement

- argostranslate==1.10.0 — utilisation actuelle commentée
- googletrans==4.0.2 — aucune nécessité identifiée pour le pipeline utilisant deep-translator
- psycopg2==2.9.11 — doublon évité avec psycopg2-binary pour l'environnement local

Cette liste est provisoire et doit être validée par l'audit Phase 0.
