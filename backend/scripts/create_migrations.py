"""
Script pour créer les migrations de base de données.

Ce script initialise Alembic et crée la première migration pour les modèles de l'application.
"""

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

# Ajouter le répertoire racine au chemin Python
root_dir = str(Path(__file__).parent.absolute())
sys.path.append(root_dir)


def create_migrations():
    """Crée les migrations de base de données"""
    # Chemin vers le fichier de configuration Alembic
    alembic_cfg = Config(os.path.join(root_dir, "migrations", "alembic.ini"))

    # Définir le chemin vers le répertoire des migrations
    alembic_cfg.set_main_option("script_location", os.path.join(root_dir, "migrations"))

    # Créer le répertoire des migrations s'il n'existe pas
    migrations_dir = os.path.join(root_dir, "migrations")
    if not os.path.exists(migrations_dir):
        os.makedirs(migrations_dir)

    # Initialiser Alembic si ce n'est pas déjà fait
    if not os.path.exists(os.path.join(migrations_dir, "versions")):
        print("Initialisation d'Alembic...")
        command.init(alembic_cfg, migrations_dir, "flask")

    # Créer une nouvelle migration
    print("Création de la migration...")
    command.revision(alembic_cfg, autogenerate=True, message="Initial migration")

    print("Migration créée avec succès.")
    print("Pour appliquer les migrations, exécutez: flask db upgrade")


if __name__ == "__main__":
    create_migrations()
