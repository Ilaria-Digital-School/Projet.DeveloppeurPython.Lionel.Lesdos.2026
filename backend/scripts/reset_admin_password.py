#!/usr/bin/env python3
"""
Script pour réinitialiser le mot de passe de l'administrateur.

Ce script permet de réinitialiser le mot de passe d'un administrateur existant
ou d'en créer un nouveau si aucun administrateur n'existe.

Utilisation:
    python -m scripts.reset_admin_password [nouveau_mot_de_passe]

Si aucun mot de passe n'est fourni, un mot de passe aléatoire sera généré.
"""

import os
import secrets
import string
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask
from werkzeug.security import generate_password_hash

# Créer une application Flask minimale pour le contexte
app = Flask(__name__)

# Charger la configuration de l'application
app.config.from_pyfile("config.py", silent=True)
_database_url = os.environ.get("DATABASE_URL")
if not _database_url:
    sys.exit("ERREUR : la variable d'environnement DATABASE_URL est obligatoire.")
app.config["SQLALCHEMY_DATABASE_URI"] = _database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialiser les extensions
from core.extensions import db, init_extensions

# Initialiser les extensions avec l'application
init_extensions(app)


def generate_password(length=16):
    """Génère un mot de passe aléatoire."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def reset_admin_password(new_password=None):
    """Réinitialise le mot de passe de l'administrateur.

    Args:
        new_password: Le nouveau mot de passe. Si None, un mot de passe aléatoire est généré.

    Returns:
        tuple: (email, nouveau_mot_de_passe)
    """
    with app.app_context():
        # Vérifier si la table des utilisateurs existe
        from sqlalchemy import inspect, text

        # Vérifier si la base de données existe
        try:
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e:
            print(f"Erreur de connexion à la base de données: {e}")
            print("Création d'une nouvelle base de données...")
            db.create_all()

        inspector = inspect(db.engine)
        if "users" not in inspector.get_table_names():
            print("La table 'users' n'existe pas. Création de la base de données...")
            db.create_all()

        # Importer les modèles ici pour éviter les problèmes d'importation circulaire
        from core.models.role import Role
        from core.models.user import User

        # Vérifier si l'utilisateur admin existe
        admin = User.query.filter_by(email="admin@example.com").first()

        # Générer un mot de passe si aucun n'est fourni
        if new_password is None:
            new_password = generate_password()

        # Hasher le mot de passe
        password_hash = generate_password_hash(new_password)

        if admin:
            # Mettre à jour le mot de passe de l'admin existant
            admin.password_hash = password_hash
            admin.is_active = True
            admin.is_locked = False
            admin.login_attempts = 0
            db.session.commit()
            print(f"Mot de passe de l'administrateur {admin.email} mis à jour.")
        else:
            # Créer un nouvel utilisateur admin
            admin = User(
                username="admin",
                email="admin@example.com",
                first_name="Administrateur",
                last_name="Système",
                password_hash=password_hash,
                is_active=True,
                email_verified=True,
            )

            # Ajouter le rôle admin
            admin_role = Role.query.filter_by(name="admin").first()
            if not admin_role:
                admin_role = Role(
                    name="admin",
                    description="Administrateur système avec tous les droits",
                )
                db.session.add(admin_role)

            admin.roles.append(admin_role)
            db.session.add(admin)
            db.session.commit()
            print("Nouvel administrateur créé avec succès.")

        return admin.email, new_password


if __name__ == "__main__":
    # Récupérer le mot de passe en argument ou en générer un
    if len(sys.argv) > 1:
        new_password = sys.argv[1]
    else:
        new_password = None

    # Exécuter la réinitialisation
    email, password = reset_admin_password(new_password)

    print("\n" + "=" * 50)
    print(f"Email: {email}")
    print(f"Nouveau mot de passe: {password}")
    print("=" * 50 + "\n")
    print("Connexion avec ces identifiants à l'adresse: http://localhost:5000/admin")
    print("N'oubliez pas de changer ce mot de passe après votre première connexion !")
