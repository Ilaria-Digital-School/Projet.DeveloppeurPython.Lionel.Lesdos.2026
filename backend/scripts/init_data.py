"""
Script d'initialisation des données de base de l'application.

Ce script crée les rôles et les permissions par défaut nécessaires au bon
fonctionnement de l'application.
"""

import os
import sys

# Ajout du répertoire parent au chemin d'importation
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.role import Permission, Role


def create_default_roles_and_permissions():
    """Crée les rôles et permissions par défaut."""
    # Permissions de base
    permissions = [
        # Gestion des utilisateurs
        ("users:read", "Voir la liste des utilisateurs", "Utilisateurs"),
        ("users:write", "Créer et modifier des utilisateurs", "Utilisateurs"),
        ("users:delete", "Supprimer des utilisateurs", "Utilisateurs"),
        (
            "users:impersonate",
            "Se connecter en tant qu'un autre utilisateur",
            "Utilisateurs",
        ),
        # Gestion des rôles
        ("roles:read", "Voir la liste des rôles", "Rôles"),
        ("roles:write", "Créer et modifier des rôles", "Rôles"),
        ("roles:delete", "Supprimer des rôles", "Rôles"),
        ("roles:assign", "Attribuer des rôles aux utilisateurs", "Rôles"),
        # Gestion des permissions
        ("permissions:read", "Voir la liste des permissions", "Permissions"),
        ("permissions:assign", "Attribuer des permissions aux rôles", "Permissions"),
        # Gestion des paramètres
        ("settings:read", "Voir les paramètres", "Paramètres"),
        ("settings:write", "Modifier les paramètres", "Paramètres"),
        # Gestion du contenu
        ("content:read", "Voir le contenu", "Contenu"),
        ("content:write", "Créer et modifier du contenu", "Contenu"),
        ("content:delete", "Supprimer du contenu", "Contenu"),
        ("content:publish", "Publier du contenu", "Contenu"),
    ]

    # Création des permissions
    for name, description, category in permissions:
        Permission.get_or_create(name=name, description=description, category=category)

    # Rôles par défaut
    roles = [
        # Administrateur système (accès complet)
        {
            "name": "admin",
            "description": "Administrateur système avec tous les accès",
            "is_system": True,
            "permissions": [p[0] for p in permissions],
        },
        # Éditeur (accès complet au contenu)
        {
            "name": "editor",
            "description": "Éditeur avec accès complet au contenu",
            "is_system": True,
            "permissions": [
                "content:read",
                "content:write",
                "content:delete",
                "content:publish",
                "users:read",
            ],
        },
        # Utilisateur standard (accès limité)
        {
            "name": "user",
            "description": "Utilisateur standard avec accès de base",
            "is_system": True,
            "permissions": [
                "content:read",
                "users:read",
            ],
        },
        # Invité (accès très limité)
        {
            "name": "guest",
            "description": "Utilisateur non authentifié avec accès limité",
            "is_system": True,
            "permissions": [
                "content:read",
            ],
        },
    ]

    # Création des rôles et attribution des permissions
    for role_data in roles:
        role = Role.get_or_create(
            name=role_data["name"],
            description=role_data["description"],
            is_system=role_data["is_system"],
        )

        # Réinitialisation des permissions
        role.permissions = []

        # Ajout des permissions
        for perm_name in role_data["permissions"]:
            permission = Permission.get_by_name(perm_name)
            if permission:
                role.permissions.append(permission)

        db.session.add(role)

    # Validation des modifications
    db.session.commit()
    print("Rôles et permissions initialisés avec succès!")


def create_admin_user():
    """Crée un utilisateur administrateur par défaut."""

    from app.models.user import User

    # Vérifier si un administrateur existe déjà
    admin_role = Role.get_by_name("admin")
    if not admin_role:
        print(
            "Erreur: Le rôle 'admin' n'existe pas. Exécutez d'abord create_default_roles_and_permissions()."
        )
        return

    # Vérifier si un administrateur existe déjà
    admin_user = User.query.filter(User.roles.any(Role.name == "admin")).first()
    if admin_user:
        print(f"Un administrateur existe déjà: {admin_user.email}")
        return

    # Créer l'utilisateur administrateur
    admin_user = User(
        username="admin",
        email="admin@example.com",
        first_name="Admin",
        last_name="System",
        is_active=True,
        email_verified=True,
    )
    # Utiliser le mot de passe depuis la variable d'environnement ou générer un mot de passe aléatoire
    import os
    import secrets

    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_password:
        admin_password = secrets.token_urlsafe(16)
    admin_user.set_password(admin_password)
    admin_user.roles.append(admin_role)

    db.session.add(admin_user)
    db.session.commit()

    print("Compte administrateur créé avec succès!")
    print(f"Email: admin@example.com")
    print(f"Mot de passe: {admin_password}")
    print(
        "\nATTENTION: Changez ce mot de passe immédiatement après la première connexion!"
    )


def init_db():
    """Initialise la base de données avec les données par défaut."""
    print("Initialisation de la base de données...")

    # Création des tables
    db.create_all()

    # Création des rôles et permissions
    create_default_roles_and_permissions()

    # Création de l'utilisateur admin
    create_admin_user()

    print("\nInitialisation terminée avec succès!")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        init_db()
