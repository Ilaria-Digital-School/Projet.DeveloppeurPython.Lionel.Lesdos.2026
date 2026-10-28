"""
Service de gestion des rôles et permissions.

Ce module fournit des fonctionnalités pour gérer les rôles et les permissions
des utilisateurs de manière centralisée.
"""

from typing import List, Optional

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

    def get_all_roles(self) -> List[Role]:
        """Récupère tous les rôles.

        Returns:
            List[Role]: Liste de tous les rôles
        """
        return Role.query.order_by(Role.name).all()

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

    def update_role(self, role_id: int, **kwargs) -> Optional[Role]:
        """Met à jour un rôle existant.

        Args:
            role_id: ID du rôle à mettre à jour
            **kwargs: Attributs à mettre à jour

        Returns:
            Role: Le rôle mis à jour, ou None si non trouvé
        """
        role = self.get_role_by_id(role_id)
        if not role:
            return None

        if "name" in kwargs and kwargs["name"] != role.name:
            if self.get_role_by_name(kwargs["name"]):
                raise ValueError(f"Un rôle avec le nom '{kwargs['name']}' existe déjà")
            role.name = kwargs["name"]

        if "description" in kwargs:
            role.description = kwargs["description"]

        self.db.session.commit()
        return role

    def delete_role(self, role_id: int) -> bool:
        """Supprime un rôle.

        Args:
            role_id: ID du rôle à supprimer

        Returns:
            bool: True si le rôle a été supprimé, False si non trouvé
        """
        role = self.get_role_by_id(role_id)
        if not role:
            return False

        # Vérifier si le rôle est utilisé par des utilisateurs
        if role.users:
            raise ValueError(
                "Impossible de supprimer un rôle associé à des utilisateurs"
            )

        self.db.session.delete(role)
        self.db.session.commit()
        return True

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

    def get_all_permissions(self) -> List[Permission]:
        """Récupère toutes les permissions.

        Returns:
            List[Permission]: Liste de toutes les permissions
        """
        return Permission.query.order_by(Permission.name).all()

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

    def remove_permission_from_role(self, role_id: int, permission_id: int) -> bool:
        """Supprime une permission d'un rôle.

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

        if permission in role.permissions:
            role.permissions.remove(permission)
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

    def get_roles_for_user(self, user_id: int) -> List[Role]:
        """Récupère tous les rôles d'un utilisateur.

        Args:
            user_id: ID de l'utilisateur

        Returns:
            List[Role]: Liste des rôles de l'utilisateur
        """
        from core.models.user import User

        user = db.session.get(User, user_id)
        return user.roles if user else []

    def get_permissions_for_role(self, role_id: int) -> List[Permission]:
        """Récupère toutes les permissions d'un rôle.

        Args:
            role_id: ID du rôle

        Returns:
            List[Permission]: Liste des permissions du rôle
        """
        role = self.get_role_by_id(role_id)
        return role.permissions if role else []

    def get_all_permissions_for_user(self, user_id: int) -> List[Permission]:
        """Récupère toutes les permissions d'un utilisateur (via ses rôles).

        Args:
            user_id: ID de l'utilisateur

        Returns:
            List[Permission]: Liste de toutes les permissions de l'utilisateur
        """
        from core.models.user import User

        user = db.session.get(User, user_id)
        if not user:
            return []

        permissions = set()
        for role in user.roles:
            permissions.update(role.permissions)

        return list(permissions)


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
