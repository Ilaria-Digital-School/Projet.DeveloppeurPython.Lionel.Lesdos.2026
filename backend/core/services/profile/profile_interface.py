from abc import ABC, abstractmethod
from typing import Dict, List, Tuple


class IProfileService(ABC):
    """Interface pour le service de gestion des profils utilisateurs"""

    @abstractmethod
    def update_profile(self, user_id: int, profile_data: Dict) -> Tuple[bool, str, int]:
        """Met à jour le profil d'un utilisateur

        Args:
            user_id: ID de l'utilisateur
            profile_data: Dictionnaire contenant les données à mettre à jour

        Returns:
            Tuple[bool, str, int]: (succès, message, code_http)
        """

    @abstractmethod
    def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> Tuple[bool, str, int]:
        """Change le mot de passe d'un utilisateur

        Args:
            user_id: ID de l'utilisateur
            current_password: Mot de passe actuel
            new_password: Nouveau mot de passe

        Returns:
            Tuple[bool, str, int]: (succès, message, code_http)
        """


class ISessionManager(ABC):
    """Interface pour la gestion des sessions utilisateur"""

    @abstractmethod
    def get_active_sessions(self, user_id: int) -> List[Dict]:
        """Récupère les sessions actives d'un utilisateur

        Args:
            user_id: ID de l'utilisateur

        Returns:
            List[Dict]: Liste des sessions actives
        """

    @abstractmethod
    def revoke_session(self, session_id: str, user_id: int) -> Tuple[bool, str]:
        """Révoque une session spécifique

        Args:
            session_id: ID de la session à révoquer
            user_id: ID de l'utilisateur propriétaire

        Returns:
            Tuple[bool, str]: (succès, message)
        """
