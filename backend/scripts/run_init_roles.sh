#!/bin/bash

# Activer l'environnement virtuel
source venv/bin/activate

# Exécuter le script d'initialisation des rôles
python -m backend.scripts.init_roles
