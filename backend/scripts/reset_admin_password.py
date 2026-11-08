#!/usr/bin/env python3
"""
Script pour réinitialiser le mot de passe de l'administrateur.

Réinitialise le mot de passe du compte admin@example.com (et le débloque),
ou crée ce compte avec le rôle admin s'il n'existe pas.

Utilisation (depuis le dossier backend, DATABASE_URL défini) :
    python scripts/reset_admin_password.py [nouveau_mot_de_passe]

Dans Docker :
    docker compose exec -w /app/backend app python scripts/reset_admin_password.py

Si aucun mot de passe n'est fourni, un mot de passe aléatoire est généré.
Le schéma de la base doit déjà exister (migrations Alembic appliquées).
"""

import os
import secrets
import string
import sys
from pathlib import Path

# Ajouter le répertoire backend au PYTHONPATH pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

ADMIN_EMAIL = "admin@example.com"


def generate_password(length=16):
    """Génère un mot de passe aléatoire."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def reset_admin_password(app, new_password=None):
    """Réinitialise (ou crée) le compte administrateur.

    Args:
        app: application Flask configurée (create_app).
        new_password: le nouveau mot de passe ; aléatoire si None.

    Returns:
        tuple: (email, nouveau_mot_de_passe, cree)
    """
    from sqlalchemy import inspect

    from core.extensions import db
    from core.models.role import Role
    from core.models.user import User

    with app.app_context():
        if "users" not in inspect(db.engine).get_table_names():
            sys.exit(
                "ERREUR : la table 'users' n'existe pas. "
                "Appliquer d'abord les migrations (flask db upgrade)."
            )

        if new_password is None:
            new_password = generate_password()

        admin = User.query.filter_by(email=ADMIN_EMAIL).first()
        cree = admin is None
        if cree:
            admin = User(
                username="admin",
                email=ADMIN_EMAIL,
                first_name="Administrateur",
                last_name="Système",
                email_verified=True,
            )
            db.session.add(admin)

        # Le setter hache le mot de passe et invalide les sessions existantes
        admin.password = new_password
        admin.is_active = True
        admin.is_locked = False
        admin.login_attempts = 0

        admin_role = Role.query.filter_by(name="admin").first()
        if not admin_role:
            admin_role = Role(
                name="admin",
                description="Administrateur système avec tous les droits",
            )
            db.session.add(admin_role)
        if admin_role not in admin.roles:
            admin.roles.append(admin_role)

        db.session.commit()
        return admin.email, new_password, cree


def main():
    if not os.environ.get("DATABASE_URL"):
        sys.exit("ERREUR : la variable d'environnement DATABASE_URL est obligatoire.")

    from app import create_app

    app = create_app()
    new_password = sys.argv[1] if len(sys.argv) > 1 else None
    email, password, cree = reset_admin_password(app, new_password)

    print("\n" + "=" * 50)
    print(
        "Administrateur créé."
        if cree
        else "Mot de passe de l'administrateur mis à jour."
    )
    print(f"Email: {email}")
    print(f"Nouveau mot de passe: {password}")
    print("=" * 50 + "\n")
    print("N'oubliez pas de changer ce mot de passe après votre première connexion !")


if __name__ == "__main__":
    main()
