"""
Script pour gérer les migrations de base de données.

Ce script permet de créer et d'appliquer des migrations pour les modèles de données.
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire du projet au PYTHONPATH
project_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(project_dir))

# Charger les variables d'environnement
from dotenv import load_dotenv

load_dotenv()


def create_migration():
    """Crée une nouvelle migration."""
    from flask_migrate import Migrate

    from app import create_app, db

    app = create_app()
    migrate = Migrate(app, db)

    with app.app_context():
        migrate()


def upgrade_db():
    """Applique les migrations en attente."""
    from flask_migrate import upgrade

    from app import create_app

    app = create_app()

    with app.app_context():
        upgrade()


def reset_db():
    """Réinitialise complètement la base de données (à utiliser avec précaution en développement)."""
    from flask_migrate import upgrade
    from sqlalchemy import text

    from app import create_app, db

    app = create_app()

    with app.app_context():
        # Supprimer toutes les tables (y compris alembic_version,
        # sinon Alembic se croit à jour et ne recrée rien)
        db.drop_all()
        db.session.execute(text("DROP TABLE IF EXISTS alembic_version"))
        db.session.commit()
        # Recréer le schéma via les migrations
        upgrade()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Gestion des migrations de base de données"
    )
    parser.add_argument(
        "command",
        choices=["migrate", "upgrade", "reset"],
        help="Commande à exécuter: migrate (crée une migration), upgrade (applique les migrations), reset (réinitialise la base)",
    )

    args = parser.parse_args()

    if args.command == "migrate":
        create_migration()
    elif args.command == "upgrade":
        upgrade_db()
    elif args.command == "reset":
        db_url = os.environ.get("DATABASE_URL", "")
        db_name = db_url.rsplit("/", 1)[-1].split("?")[0] if db_url else "(inconnue)"
        flask_env = os.environ.get("FLASK_ENV", "development")

        print("=" * 60)
        print("ATTENTION : cette opération SUPPRIME toutes les tables")
        print("et toutes les données de la base ciblée.")
        print(f"  Base ciblée   : {db_name}")
        print(f"  Environnement : {flask_env}")
        print("=" * 60)

        # Refus si pas de terminal interactif (cron, pipe, CI...)
        if not sys.stdin.isatty():
            print("REFUS : confirmation interactive impossible (pas de terminal).")
            sys.exit(1)

        # Refus catégorique en production
        if flask_env == "production":
            print("REFUS : réinitialisation interdite en environnement de production.")
            print("(Incident du 05/07/2026 : base de production détruite par erreur.)")
            sys.exit(1)

        # Confirmation forte : taper le nom exact de la base
        confirm = input(
            f"Pour confirmer, tapez le nom exact de la base ('{db_name}') : "
        )
        if confirm.strip() == db_name:
            reset_db()
            print("Base de données réinitialisée avec succès.")
        else:
            print("Opération annulée (nom de base incorrect).")
            sys.exit(1)
    else:
        print("Commande non reconnue. Utilisez 'migrate', 'upgrade' ou 'reset'.")
