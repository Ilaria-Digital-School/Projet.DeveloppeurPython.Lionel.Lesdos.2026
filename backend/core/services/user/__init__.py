"""
Package des services utilisateur.

Ce package contient les services pour la gestion des utilisateurs.
"""

from .services import UserService


def get_user_service():
    """Retourne une instance du service utilisateur.

    Cette fonction doit être appelée à l'intérieur d'un contexte d'application Flask.
    """
    return UserService()


# Ne pas créer d'instance ici pour éviter les problèmes de contexte
user_service = None

__all__ = ["UserService", "user_service", "get_user_service"]
