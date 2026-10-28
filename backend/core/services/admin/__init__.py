"""
Services d'administration.

Ce module fournit des services pour l'administration du système.
"""

from .admin_services import AdminService

# Créer une instance unique du service d'administration
admin_service = AdminService()


def get_admin_service() -> AdminService:
    """
    Récupère l'instance du service d'administration.

    Returns:
        AdminService: L'instance du service d'administration
    """
    return admin_service


__all__ = ["AdminService", "admin_service", "get_admin_service"]
