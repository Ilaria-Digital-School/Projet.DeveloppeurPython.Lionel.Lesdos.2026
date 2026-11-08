"""
Services spécifiques au module utilisateur.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import current_app

from core.models.user import User
from core.services.user import UserService as CoreUserService


class UserService(CoreUserService):
    """Service utilisateur étendu avec des fonctionnalités spécifiques au module."""

    def __init__(self, app=None):
        """Initialise le service utilisateur étendu."""
        super().__init__(app or current_app._get_current_object())

    def update_user_profile(
        self, user_id: int, profile_data: Dict[str, Any]
    ) -> Optional[User]:
        """Met à jour le profil utilisateur avec des données spécifiques.

        Args:
            user_id: L'ID de l'utilisateur à mettre à jour
            profile_data: Dictionnaire des données de profil à mettre à jour

        Returns:
            L'utilisateur mis à jour ou None si non trouvé
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        # Mise à jour des champs de profil
        if "first_name" in profile_data:
            user.first_name = profile_data["first_name"]
        if "last_name" in profile_data:
            user.last_name = profile_data["last_name"]
        if "phone" in profile_data:
            user.phone = profile_data["phone"]

        self.db.session.commit()
        return user

    def deactivate_user(self, user_id: int, reason: str = None) -> bool:
        """Désactive un utilisateur de manière sécurisée.

        Args:
            user_id: L'ID de l'utilisateur à désactiver
            reason: Raison de la désactivation (optionnel)

        Returns:
            bool: True si la désactivation a réussi, False sinon
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = False
        user.deactivated_at = datetime.now(timezone.utc)
        user.deactivation_reason = reason

        try:
            self.db.session.commit()
            return True
        except Exception as e:
            current_app.logger.error(
                f"Erreur lors de la désactivation de l'utilisateur {user_id}: {e}"
            )
            self.db.session.rollback()
            return False
