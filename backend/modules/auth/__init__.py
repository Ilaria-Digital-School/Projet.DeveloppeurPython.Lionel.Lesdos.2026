"""
Module d'authentification unifié.

Ce module gère l'authentification et l'autorisation des utilisateurs
avec une architecture simplifiée et cohérente.

Structure:
- auth_routes.py : Routes unifiées (web + API)
- auth_forms.py : Formulaires avec validation
- config.py : Configuration d'authentification
"""

import logging

from flask import current_app

# Configuration du logger
logger = logging.getLogger(__name__)

# Imports des services centralisés
from core.services.auth import (
    AuthSecurityService,
    RoleService,
    SecurityService,
    get_auth_service,
    get_role_service,
    get_security_service,
)

# Import du Blueprint unifié
from .auth_routes import auth_bp

# Exports pour compatibilité
__all__ = [
    "auth_bp",
    "init_auth_module",
    "AuthSecurityService",
    "RoleService",
    "SecurityService",
    "get_auth_service",
    "get_role_service",
    "get_security_service",
]


def init_auth_module(app):
    """
    Initialise le module d'authentification avec architecture simplifiée.

    Args:
        app: L'application Flask

    Returns:
        app: L'application Flask configurée
    """
    try:
        # Enregistrement du Blueprint unifié
        app.register_blueprint(auth_bp)

        # Configuration du logging
        if app.config.get("AUTH_LOGGING_ENABLED", True):
            logger.setLevel(logging.INFO)

        # Initialisation des services d'authentification
        with app.app_context():
            get_auth_service()
            get_role_service()
            get_security_service()

            logger.info("Services d'authentification initialisés")

        # Configuration des hooks d'authentification
        _setup_auth_hooks(app)

        logger.info("Module d'authentification unifié initialisé avec succès")
        return app

    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du module auth: {e}")
        raise


def _setup_auth_hooks(app):
    """
    Configure les hooks d'authentification Flask-Login et JWT.

    Args:
        app: L'application Flask
    """
    from flask_jwt_extended import JWTManager
    from flask_login import LoginManager

    from core.models.user import User

    # Configuration Flask-Login
    login_manager = app.extensions.get("login_manager")
    if login_manager:

        @login_manager.user_loader
        def load_user(user_id):
            # "<id>.<empreinte>" : session refusée après un changement de mot de passe
            return User.depuis_identifiant_session(user_id)

        @login_manager.unauthorized_handler
        def unauthorized():
            from flask import redirect, request, url_for

            return redirect(url_for("auth.login", next=request.endpoint))

    # Configuration JWT (si activé)
    jwt_manager = app.extensions.get("flask-jwt-extended")
    if jwt_manager:

        @jwt_manager.user_identity_loader
        def user_identity_lookup(user):
            return str(user.id if hasattr(user, "id") else user)

        @jwt_manager.user_lookup_loader
        def user_lookup_callback(_jwt_header, jwt_data):
            identity = jwt_data["sub"]
            return User.query.filter_by(id=identity).one_or_none()

    logger.info("Hooks d'authentification configurés")


# Fonction d'initialisation principale (alias pour compatibilité)
init_app = init_auth_module
