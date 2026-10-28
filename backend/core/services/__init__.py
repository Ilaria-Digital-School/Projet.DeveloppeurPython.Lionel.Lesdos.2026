"""
Services de l'application.

Ce module exporte tous les services disponibles dans l'application.
"""

# Import des services de base
try:
    from .auth.auth_service import (
        auth_security_service,
        get_auth_security_service,
        init_auth_security_service,
    )
    from .auth.role_service import get_role_service, role_service
    from .user import get_user_service

    # Initialisation différée des services
    auth_service = None
    user_service = None

    def init_services(app):
        """Initialise tous les services avec le contexte de l'application."""
        global auth_service, user_service

        with app.app_context():
            # Initialiser le service d'authentification
            from core.extensions import db

            init_auth_security_service(app, db)
            auth_service = get_auth_security_service()

            # Initialiser le service utilisateur
            user_service = get_user_service()

            # Initialiser le service de rôles
            from .auth.role_service import init_role_service

            init_role_service(app, db)

            app.logger.info("Services de base initialisés")

    # Créer un alias pour la compatibilité
    auth_service = auth_security_service

except ImportError as e:
    import logging
    import sys

    logging.getLogger(__name__).error(
        f"Erreur lors de l'importation des services : {e}"
    )
    raise

__all__ = ["auth_service", "role_service", "user_service", "init_services"]
