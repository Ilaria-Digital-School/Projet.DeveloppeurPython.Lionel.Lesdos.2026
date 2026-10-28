"""
Services d'authentification et d'autorisation.

Ce module fournit des services pour l'authentification, l'autorisation,
la gestion des rôles et la sécurité.
"""

from .auth_service import AuthSecurityService
from .role_service import RoleService
from .security_service import SecurityService

# Créer des instances des services
auth_service = None
role_service = None
security_service = None


def get_auth_service() -> AuthSecurityService:
    """
    Récupère l'instance du service d'authentification.

    Returns:
        AuthSecurityService: L'instance du service d'authentification
    """
    global auth_service
    if auth_service is None:
        auth_service = AuthSecurityService()
    return auth_service


def get_role_service() -> RoleService:
    """
    Récupère l'instance du service de rôles.

    Returns:
        RoleService: L'instance du service de rôles
    """
    global role_service
    if role_service is None:
        role_service = RoleService()
    return role_service


def get_security_service():
    """Retourne l'instance singleton du service de sécurité.

    Returns:
        SecurityService: L'instance du service de sécurité
    """
    from core.extensions import db

    global security_service
    if security_service is None:
        security_service = SecurityService(db)
    return security_service


__all__ = [
    "AuthSecurityService",
    "RoleService",
    "SecurityService",
    "get_auth_service",
    "get_role_service",
    "get_security_service",
]
