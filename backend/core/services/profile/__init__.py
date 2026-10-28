"""
Services de gestion des profils utilisateurs.

Ce module fournit des services pour gérer les profils utilisateurs.
"""

from .profile_services import ProfileService

# Créer une instance unique du service de profil
profile_service = ProfileService()


def get_profile_service() -> ProfileService:
    """
    Récupère l'instance du service de profil.

    Returns:
        ProfileService: L'instance du service de profil
    """
    return profile_service
