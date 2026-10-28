"""
Extensions Flask

Ce module initialise toutes les extensions Flask utilisées dans l'application.
"""

from flask_babel import Babel
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy

# Initialisation des extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
login_manager = LoginManager()
session = Session()
cache = Cache()
mail = Mail()
babel = Babel()


def init_extensions(app):
    """Initialise toutes les extensions Flask avec l'application.

    Args:
        app: L'application Flask
    """
    # Initialisation de SQLAlchemy
    db.init_app(app)

    # Initialisation de Flask-Migrate
    migrate.init_app(app, db)

    # Initialisation de JWT
    jwt.init_app(app)

    # Callback pour vérifier si un token est dans la blacklist
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        from core.models.token_blacklist import TokenBlacklist

        jti = jwt_payload["jti"]
        if TokenBlacklist.is_token_revoked(jti):
            return True
        # Jeton émis avant le dernier changement de mot de passe : révoqué
        from core.models.user import User

        try:
            user = db.session.get(User, int(jwt_payload.get("sub")))
        except TypeError, ValueError:
            return True
        return user is not None and user.jeton_emis_avant_changement(
            jwt_payload.get("iat", 0)
        )

    # Note: CORS est configuré dans app/__init__.py (create_app) avec la config complète

    # Initialisation de Bcrypt
    bcrypt.init_app(app)

    # Initialisation de Flask-Session (sessions côté serveur)
    session.init_app(app)

    # Initialisation de Flask-Caching
    cache.init_app(app)

    # Initialisation de Flask-Mail
    mail.init_app(app)

    # Initialisation de Flask-Babel
    babel.init_app(app)

    # Initialisation de Flask-Login
    login_manager.init_app(app)

    # Configuration Flask-Login
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
    login_manager.login_message_category = "info"

    # Configuration de session pour Flask-Login
    login_manager.session_protection = "strong"  # Protection de session renforcée
    login_manager.refresh_view = "auth.login"
    login_manager.needs_refresh_message = "Veuillez vous reconnecter pour continuer."
    login_manager.needs_refresh_message_category = "info"

    # Réponse non authentifiée : 401 JSON pour l'API, redirection pour le web
    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import flash, jsonify, redirect, request
        from flask_login import login_url

        if request.path.startswith("/api/"):
            return (
                jsonify({"status": "error", "message": "Authentification requise"}),
                401,
            )
        flash(login_manager.login_message, login_manager.login_message_category)
        return redirect(login_url(login_manager.login_view, request.url))

    # User loader callback pour Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from core.models.user import User

        # "<id>.<empreinte>" : session refusée après un changement de mot de passe
        return User.depuis_identifiant_session(user_id)

    # Authentification alternative par Bearer JWT : permet aux clients API
    # (sans cookie de session) d'accéder aux routes @login_required.
    # La validation est déléguée à flask-jwt-extended : signature, expiration
    # et révocation (token_in_blocklist_loader ci-dessus).
    @login_manager.request_loader
    def load_user_from_request(request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        try:
            from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

            verify_jwt_in_request()
            user_id = get_jwt_identity()
            if user_id is None:
                return None
            from core.models.user import User

            user = db.session.get(User, int(user_id))
            if user is None or not user.is_active:
                return None
            return user
        except Exception:
            # Token invalide/expiré/révoqué : pas d'authentification JWT,
            # le unauthorized_handler renverra 401 (API) ou redirigera (web)
            return None

    return app
