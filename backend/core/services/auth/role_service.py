"""
Service de gestion des rôles et permissions.

Ce module fournit des fonctionnalités pour gérer les rôles et les permissions
des utilisateurs de manière centralisée.
"""

from typing import Optional

from core.extensions import db
from core.models.permission import Permission
from core.models.role import Role


class RoleService:
    """Service de gestion des rôles et permissions.

    Ce service fournit des fonctionnalités complètes pour la gestion des rôles,
    des permissions et de leurs relations avec les utilisateurs.

    Exemple d'utilisation :

    ```python
    # Initialisation
    from app.extensions import db
    from auth.security.role_service import RoleService

    app = Flask(__name__)
    # ... configuration de l'application ...

    # Initialisation du service
    role_service = RoleService()
    role_service.init_app(app, db)

    # Création d'un rôle
    admin_role = role_service.create_role(
        name='admin',
        description='Administrateur système avec tous les droits'
    )

    # Création d'une permission
    manage_users = role_service.create_permission(
        name='manage_users',
        description='Peut gérer les utilisateurs'
    )

    # Ajout d'une permission à un rôle
    role_service.add_permission_to_role(admin_role.id, manage_users.id)

    # Vérification des permissions d'un utilisateur
    has_permission = role_service.user_has_permission(user_id=1, permission_name='manage_users')
    ```

    Attributs :
        db (SQLAlchemy): Instance de la base de données SQLAlchemy
    """

    def __init__(self, app=None, db=None):
        """Initialise le service des rôles.

        Args:
            app: Instance de l'application Flask (optionnel)
            db: Instance de la base de données SQLAlchemy (optionnel)
        """
        self.db = db

        if app is not None:
            self.init_app(app, db)

    def init_app(self, app, db=None):
        """Initialise le service avec l'application Flask.

        Args:
            app: Instance de l'application Flask
            db: Instance de la base de données SQLAlchemy (optionnel)
        """
        self.db = db or self.db

    # ===== MÉTHODES DE BASE POUR LES RÔLES =====

    def get_role_by_id(self, role_id: int) -> Optional[Role]:
        """Récupère un rôle par son ID.

        Args:
            role_id: ID du rôle

        Returns:
            Role: Le rôle correspondant, ou None si non trouvé
        """
        return db.session.get(Role, role_id)

    def get_role_by_name(self, name: str) -> Optional[Role]:
        """Récupère un rôle par son nom.

        Args:
            name: Nom du rôle

        Returns:
            Role: Le rôle correspondant, ou None si non trouvé
        """
        return Role.query.filter_by(name=name).first()

    def create_role(self, name: str, description: str = None, **kwargs) -> Role:
        """Crée un nouveau rôle.

        Args:
            name: Nom du rôle
            description: Description du rôle
            **kwargs: Autres attributs du rôle

        Returns:
            Role: Le rôle créé

        Raises:
            ValueError: Si un rôle avec le même nom existe déjà
        """
        if self.get_role_by_name(name):
            raise ValueError(f"Un rôle avec le nom '{name}' existe déjà")

        role = Role(name=name, description=description, **kwargs)
        self.db.session.add(role)
        self.db.session.commit()

        return role

    # ===== MÉTHODES DE BASE POUR LES PERMISSIONS =====

    def get_permission_by_id(self, permission_id: int) -> Optional[Permission]:
        """Récupère une permission par son ID.

        Args:
            permission_id: ID de la permission

        Returns:
            Permission: La permission correspondante, ou None si non trouvée
        """
        return db.session.get(Permission, permission_id)

    def get_permission_by_name(self, name: str) -> Optional[Permission]:
        """Récupère une permission par son nom.

        Args:
            name: Nom de la permission

        Returns:
            Permission: La permission correspondante, ou None si non trouvée
        """
        return Permission.query.filter_by(name=name).first()

    def create_permission(
        self, name: str, description: str = None, **kwargs
    ) -> Permission:
        """Crée une nouvelle permission.

        Args:
            name: Nom de la permission
            description: Description de la permission
            **kwargs: Autres attributs de la permission

        Returns:
            Permission: La permission créée

        Raises:
            ValueError: Si une permission avec le même nom existe déjà
        """
        if self.get_permission_by_name(name):
            raise ValueError(f"Une permission avec le nom '{name}' existe déjà")

        permission = Permission(name=name, description=description, **kwargs)
        self.db.session.add(permission)
        self.db.session.commit()

        return permission

    # ===== MÉTHODES POUR GÉRER LES RELATIONS =====

    def add_permission_to_role(self, role_id: int, permission_id: int) -> bool:
        """Ajoute une permission à un rôle.

        Args:
            role_id: ID du rôle
            permission_id: ID de la permission

        Returns:
            bool: True si l'opération a réussi, False sinon
        """
        role = self.get_role_by_id(role_id)
        permission = self.get_permission_by_id(permission_id)

        if not role or not permission:
            return False

        if permission not in role.permissions:
            role.permissions.append(permission)
            self.db.session.commit()

        return True

    def user_has_permission(self, user_id: int, permission_name: str) -> bool:
        """Vérifie si un utilisateur a une permission spécifique.

        Args:
            user_id: ID de l'utilisateur
            permission_name: Nom de la permission à vérifier

        Returns:
            bool: True si l'utilisateur a la permission, False sinon
        """
        from core.models.user import User

        user = db.session.get(User, user_id)
        if not user:
            return False

        return any(
            permission.name == permission_name
            for role in user.roles
            for permission in role.permissions
        )

    # ===== MÉTHODES UTILITAIRES =====


# Instance singleton du service
role_service = RoleService()


def get_role_service() -> RoleService:
    """Récupère l'instance du service des rôles.

    Returns:
        RoleService: L'instance du service des rôles

    Raises:
        RuntimeError: Si le service n'a pas été initialisé
    """
    if role_service is None:
        raise RuntimeError(
            "Le service des rôles n'a pas été initialisé. Appelez d'abord init_role_service()."
        )
    return role_service


def init_role_service(app, db=None):
    """Initialise le service des rôles.

    Args:
        app: Instance de l'application Flask
        db: Instance de la base de données SQLAlchemy (optionnel)

    Returns:
        RoleService: Instance du service des rôles
    """
    role_service.init_app(app, db)
    return role_service
