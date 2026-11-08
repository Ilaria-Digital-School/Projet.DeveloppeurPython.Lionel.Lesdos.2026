"""
Configuration de la base de données.

Ce module fournit une instance unique de SQLAlchemy pour toute l'application.
"""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Création d'une instance unique de SQLAlchemy
db = SQLAlchemy()

# Initialisation de Flask-Migrate
migrate = Migrate()


def init_app(app):
    """Initialise la base de données avec l'application Flask."""
    db.init_app(app)

    # Créer les tables si elles n'existent pas
    with app.app_context():
        db.create_all()

    return db
