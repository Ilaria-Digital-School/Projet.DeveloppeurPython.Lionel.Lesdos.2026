"""
Script pour initialiser la base de données avec des données de test.
Inclut la création des rôles et d'un utilisateur administrateur.
"""

import os
import sys
from datetime import datetime, timezone

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from core.extensions import db
from core.models.role import Role
from core.models.user import User


def init_database():
    """Initialise la base de données avec des données de test."""
    print("Initialisation de la base de données...")

    # Créer l'application Flask
    app = create_app()

    with app.app_context():
        # Créer les tables si elles n'existent pas
        db.create_all()

        # Vérifier si des rôles existent déjà
        if Role.query.count() == 0:
            print("Création des rôles...")

            # Créer les rôles par défaut
            admin_role = Role(
                name="admin",
                description="Administrateur système avec accès complet",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            user_role = Role(
                name="user",
                description="Utilisateur standard avec des droits limités",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            # Ajouter les rôles à la session
            db.session.add(admin_role)
            db.session.add(user_role)

            # Valider les changements
            db.session.commit()
            print("Rôles créés avec succès.")
        else:
            print("Des rôles existent déjà dans la base de données.")
            admin_role = Role.query.filter_by(name="admin").first()
            user_role = Role.query.filter_by(name="user").first()

        # Vérifier si l'utilisateur admin existe déjà
        admin_email = "admin@example.com"
        admin_user = User.query.filter_by(email=admin_email).first()

        if admin_user:
            print(f"L'utilisateur admin avec l'email {admin_email} existe déjà.")
            return

        # Créer l'utilisateur admin
        print("Création de l'utilisateur administrateur...")
        admin = User(
            username="admin",
            email=admin_email,
            first_name="Admin",
            last_name="System",
            is_active=True,
            email_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Définir le mot de passe depuis variable d'env ou générer un aléatoire sécurisé
        import secrets

        admin_password = os.environ.get("ADMIN_PASSWORD") or secrets.token_urlsafe(16)
        admin.password = admin_password
        print(f"Mot de passe admin: {admin_password}")
        print(
            "ATTENTION: Changez ce mot de passe immédiatement après la première connexion!"
        )

        # Ajouter les rôles à l'utilisateur admin
        if admin_role:
            admin.roles.append(admin_role)
        if user_role:
            admin.roles.append(user_role)

        # Ajouter l'utilisateur à la session
        db.session.add(admin)

        # Valider les changements
        db.session.commit()

        print("\n========================================")
        print("Initialisation terminée avec succès!")
        print(f"Email: {admin_email}")
        print(
            "Mot de passe: admin123 (à changer immédiatement après la première connexion)"
        )
        print("========================================")


if __name__ == "__main__":
    init_database()
