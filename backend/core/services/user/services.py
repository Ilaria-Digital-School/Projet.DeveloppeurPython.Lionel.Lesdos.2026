"""
Services pour la gestion des utilisateurs.

Ce module fournit des services pour gérer les opérations liées aux utilisateurs,
telles que la création, la mise à jour et la suppression des comptes utilisateurs.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flask import current_app, request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from core.extensions import db
from core.models.role import Role  # S'assurer que ce modèle existe
from core.models.user import User


class UserService:
    """Service pour la gestion des opérations utilisateur."""

    def __init__(self, app=None):
        """Initialise le service utilisateur."""
        self.app = app or current_app._get_current_object()
        from ...extensions import db

        self.db = db
        self.logger = self.app.logger

    def _commit_or_rollback(self):
        """Tente de valider la transaction ou effectue un rollback en cas d'erreur."""
        try:
            self.db.session.commit()
            return True
        except SQLAlchemyError as e:
            self.db.session.rollback()
            self.logger.error(f"Database error: {str(e)}")
            return False

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Récupère un utilisateur par son ID."""
        return self.db.session.get(User, user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Récupère un utilisateur par son email (insensible à la casse)."""
        return User.query.filter(db.func.lower(User.email) == email.lower()).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Récupère un utilisateur par son nom d'utilisateur (insensible à la casse)."""
        return User.query.filter(
            db.func.lower(User.username) == username.lower()
        ).first()

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str = None,
        last_name: str = None,
        role_names: List[str] = None,
        **extra_fields,
    ) -> Optional[User]:
        """
        Crée un nouvel utilisateur avec les rôles spécifiés.

        Args:
            username: Nom d'utilisateur unique
            email: Email de l'utilisateur
            password: Mot de passe en clair
            first_name: Prénom (optionnel)
            last_name: Nom de famille (optionnel)
            role_names: Liste des noms de rôles à attribuer
            **extra_fields: Champs supplémentaires pour le modèle User

        Returns:
            User: L'utilisateur créé ou None en cas d'erreur
        """
        try:
            # Vérifier si l'utilisateur existe déjà
            if self.get_user_by_username(username) or self.get_user_by_email(email):
                self.logger.warning(
                    f"Tentative de création d'un utilisateur existant: {username} / {email}"
                )
                return None

            # Créer l'utilisateur
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                **extra_fields,
            )

            # Hasher le mot de passe (le setter password hash automatiquement)
            user.password = password

            # Ajouter les rôles si spécifiés
            if role_names:
                roles = Role.query.filter(Role.name.in_(role_names)).all()
                if roles:
                    user.roles.extend(roles)

            # Sauvegarder l'utilisateur
            self.db.session.add(user)
            if not self._commit_or_rollback():
                return None

            self.logger.info(
                f"Nouvel utilisateur créé: {user.username} (ID: {user.id})"
            )

            # Créer les catégories par défaut pour le nouvel utilisateur
            try:
                from core.services.categories.category_services import CategoryService

                CategoryService.ensure_default_categories_exist()
                CategoryService.ensure_user_has_default_categories(user.id)
            except Exception as e:
                # Le seeding ne doit pas bloquer l'inscription
                self.logger.warning(
                    f"Impossible de créer les catégories par défaut pour {user.username}: {e}"
                )

            return user

        except IntegrityError as e:
            self.logger.error(
                f"Erreur d'intégrité lors de la création de l'utilisateur: {str(e)}"
            )
            return None

    def update_user(self, user_id: int, data: Dict[str, Any]) -> Optional[User]:
        """
        Met à jour les informations d'un utilisateur.

        Args:
            user_id: ID de l'utilisateur à mettre à jour
            data: Dictionnaire des champs à mettre à jour

        Returns:
            User: L'utilisateur mis à jour ou None si non trouvé
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return None

            # Mettre à jour les champs de base
            for key, value in data.items():
                if hasattr(user, key) and key not in ["id", "password_hash"]:
                    setattr(user, key, value)

            # Mise à jour spéciale pour le mot de passe
            if "password" in data:
                user.password = data["password"]

            # Mise à jour des rôles si spécifiés
            if "role_names" in data:
                roles = Role.query.filter(Role.name.in_(data["role_names"])).all()
                user.roles = roles

            user.updated_at = datetime.now(timezone.utc)

            if not self._commit_or_rollback():
                return None

            self.logger.info(f"Utilisateur mis à jour: {user.username} (ID: {user.id})")
            return user

        except Exception as e:
            self.logger.error(
                f"Erreur lors de la mise à jour de l'utilisateur {user_id}: {str(e)}"
            )
            return None

    def deactivate_user(self, user_id: int, reason: str = None) -> bool:
        """
        Désactive un utilisateur.

        Args:
            user_id: ID de l'utilisateur à désactiver
            reason: Raison de la désactivation

        Returns:
            bool: True si la désactivation a réussi, False sinon
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False

            user.is_active = False
            user.deactivated_at = datetime.now(timezone.utc)
            user.deactivation_reason = reason

            return self._commit_or_rollback()

        except Exception as e:
            self.logger.error(
                f"Erreur lors de la désactivation de l'utilisateur {user_id}: {str(e)}"
            )
            return False

    def update_last_login(self, user_id: int, ip_address: str = None) -> bool:
        """
        Met à jour les informations de dernière connexion.

        Args:
            user_id: ID de l'utilisateur
            ip_address: Adresse IP de la connexion

        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False

            now = datetime.now(timezone.utc)

            # Mettre à jour les informations de connexion
            user.last_login_at = user.current_login_at
            user.last_login_ip = user.current_login_ip
            user.current_login_at = now
            user.current_login_ip = ip_address or request.remote_addr
            user.login_count = (user.login_count or 0) + 1

            return self._commit_or_rollback()

        except Exception as e:
            self.logger.error(
                f"Erreur lors de la mise à jour de la dernière connexion pour l'utilisateur {user_id}: {str(e)}"
            )
            return False

    def delete_user(self, user_id: int) -> bool:
        """
        Supprime définitivement un utilisateur de la base de données.

        Les données liées (comptes, transactions, catégories, budgets, etc.)
        sont supprimées automatiquement par les contraintes ON DELETE CASCADE
        de la base (migration user_fk_cascade_01).

        Note: Cette méthode supprime physiquement l'enregistrement.
        Préférez utiliser deactivate_user pour une désactivation logique.

        Args:
            user_id: ID de l'utilisateur à supprimer

        Returns:
            bool: True si la suppression a réussi, False sinon
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False

            # Suppression en SQL direct : les cascades sont gérées par la base.
            # (session.delete(user) tenterait de mettre à NULL les FK des
            # relations sans cascade ORM, ex. transactions.user_id NOT NULL)
            self.db.session.execute(self.db.delete(User).where(User.id == user_id))
            return self._commit_or_rollback()

        except Exception as e:
            self.logger.error(
                f"Erreur lors de la suppression de l'utilisateur {user_id}: {str(e)}"
            )
            return False

    def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> Dict[str, Any]:
        """
        Change le mot de passe d'un utilisateur de manière sécurisée.

        Args:
            user_id: ID de l'utilisateur
            current_password: Mot de passe actuel
            new_password: Nouveau mot de passe (doit contenir au moins 12 caractères)

        Returns:
            Dict: Dictionnaire contenant le statut et un message
        """
        try:
            # Vérifier que le nouveau mot de passe est valide
            if len(new_password) < 12:
                return {
                    "success": False,
                    "message": "Le nouveau mot de passe doit contenir au moins 12 caractères",
                    "code": "PASSWORD_TOO_SHORT",
                }

            # Récupérer l'utilisateur
            user = self.get_user_by_id(user_id)
            if not user:
                return {
                    "success": False,
                    "message": "Utilisateur non trouvé",
                    "code": "USER_NOT_FOUND",
                }

            # Vérifier le mot de passe actuel
            if not user.check_password(current_password):
                return {
                    "success": False,
                    "message": "Mot de passe actuel incorrect",
                    "code": "INVALID_CURRENT_PASSWORD",
                }

            # Vérifier que le nouveau mot de passe est différent de l'ancien
            if user.check_password(new_password):
                return {
                    "success": False,
                    "message": "Le nouveau mot de passe doit être différent de l'ancien",
                    "code": "SAME_AS_OLD_PASSWORD",
                }

            # Mettre à jour le mot de passe
            user.password = new_password
            user.updated_at = datetime.now(timezone.utc)

            if not self._commit_or_rollback():
                return {
                    "success": False,
                    "message": "Erreur lors de la mise à jour du mot de passe",
                    "code": "UPDATE_ERROR",
                }

            self.logger.info(f"Mot de passe mis à jour pour l'utilisateur {user_id}")
            return {
                "success": True,
                "message": "Mot de passe mis à jour avec succès",
                "code": "SUCCESS",
            }

        except Exception as e:
            self.logger.error(
                f"Erreur lors du changement de mot de passe pour l'utilisateur {user_id}: {str(e)}"
            )
            return {
                "success": False,
                "message": "Une erreur est survenue lors du changement de mot de passe",
                "code": "INTERNAL_ERROR",
                "error": str(e),
            }
