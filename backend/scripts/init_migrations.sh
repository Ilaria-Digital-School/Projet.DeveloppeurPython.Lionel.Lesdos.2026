#!/bin/bash
# Script pour initialiser les migrations et créer la migration initiale

# Configuration de l'environnement
export FLASK_APP=wsgi.py
export FLASK_ENV=development

# Créer le dossier instance s'il n'existe pas
mkdir -p instance

# Initialiser le dossier de migrations
flask db init

# Créer la migration initiale
flask db migrate -m "Initial migration"

# Appliquer les migrations
flask db upgrade

echo "Migrations initialisées et appliquées avec succès !"
