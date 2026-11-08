"""
Service unifié d'authentification et de sécurité.
"""

from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy

# Instance globale du service
auth_security_service = None


def init_auth_security_service(app: "Flask", db: SQLAlchemy) -> None:
    """Initialise le service d'authentification.

    Args:
        app: L'application Flask
        db: L'instance SQLAlchemy
    """
    global auth_security_service
    auth_security_service = AuthSecurityService(app, db)
    current_app.logger.info("Service d'authentification initialisé")


def get_auth_security_service() -> "AuthSecurityService":
    """Récupère l'instance du service d'authentification.

    Returns:
        AuthSecurityService: L'instance du service

    Raises:
        RuntimeError: Si le service n'a pas été initialisé
    """
    if auth_security_service is None:
        raise RuntimeError(
            "Le service d'authentification n'a pas été initialisé. Appelez d'abord init_auth_security_service()."
        )
    return auth_security_service


import logging
from datetime import datetime, timezone

from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
)
from werkzeug.security import check_password_hash, generate_password_hash

# Import bcrypt pour gérer les hash bcrypt existants
try:
    import bcrypt

    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

# Configuration du logger
logger = logging.getLogger(__name__)


def verify_password(password_hash, password):
    """
    Vérifie un mot de passe avec support pour bcrypt ET Werkzeug.

    Args:
        password_hash (str): Le hash du mot de passe stocké
        password (str): Le mot de passe en clair à vérifier

    Returns:
        bool: True si le mot de passe correspond, False sinon
    """
    # Vérifier si c'est un hash bcrypt
    if (
        password_hash.startswith("$2b$")
        or password_hash.startswith("$2a$")
        or password_hash.startswith("$2y$")
    ):
        if BCRYPT_AVAILABLE:
            try:
                return bcrypt.checkpw(
                    password.encode("utf-8"), password_hash.encode("utf-8")
                )
            except Exception as e:
                logger.warning(f"Erreur lors de la vérification bcrypt: {e}")
                return False
        else:
            logger.warning("Hash bcrypt détecté mais bcrypt non disponible")
            return False

    # Sinon, utiliser Werkzeug (pbkdf2, etc.)
    try:
        return check_password_hash(password_hash, password)
    except Exception as e:
        logger.warning(f"Erreur lors de la vérification Werkzeug: {e}")
        return False


class AuthSecurityService:
    """Service unifié d'authentification et de sécurité."""

    def __init__(self, app=None, db=None):
        """Initialise le service d'authentification et de sécurité."""
        self.app = app
        self.db = db
        self.logger = logger or logging.getLogger(__name__)

        if app is not None and db is not None:
            self.init_app(app, db)

    def init_app(self, app, db):
        """Initialise l'extension avec l'application Flask."""
        self.app = app
        self.db = db
        self._init_jwt_callbacks()
        self.logger.info("Service d'authentification initialisé")

    def _init_jwt_callbacks(self):
        """Initialise les callbacks JWT."""

        from core.extensions import jwt

        # Utiliser l'instance JWTManager déjà configurée
        jwt_manager = jwt

        @jwt_manager.user_identity_loader
        def user_identity_lookup(user):
            # Retourne l'ID sous forme de chaîne (requis par Flask-JWT-Extended ≥ 4.x)
            return str(user.id if hasattr(user, "id") else user)

        @jwt_manager.user_lookup_loader
        def user_lookup_callback(_jwt_header, jwt_data):
            from core.extensions import db

            from ..models.user import User

            identity = jwt_data["sub"]
            return db.session.get(User, identity)

    def authenticate(self, username, password, ip_address=None):
        """Authentifie un utilisateur avec son nom d'utilisateur/email et son mot de passe."""
        try:
            self.logger.info(f"Tentative d'authentification pour: {username}")

            # Utiliser le service utilisateur pour récupérer l'utilisateur
            from core.services.user.services import UserService

            user_service = UserService()

            # Essayer de récupérer l'utilisateur par nom d'utilisateur ou email
            user = user_service.get_user_by_username(
                username
            ) or user_service.get_user_by_email(username)

            if not user:
                self.logger.warning(f"Aucun utilisateur trouvé pour: {username}")
                return None, None

            # Vérifier le mot de passe avec support bcrypt ET Werkzeug
            if not verify_password(user.password_hash, password):
                self.logger.warning(
                    f"Mot de passe incorrect pour l'utilisateur: {username}"
                )
                return None, None

            # Suppression demandée et pas encore échue : se reconnecter l'annule
            # (promis par DELETE /settings/account ; la connexion était refusée)
            from core.services.user.account_deletion import annuler_si_planifiee

            user._suppression_annulee = annuler_si_planifiee(user)

            # Vérifier si le compte est actif
            if not user.is_active:
                self.logger.warning(
                    f"Tentative de connexion à un compte désactivé: {username}"
                )
                return None, None

            # Générer les tokens JWT
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)

            # Mettre à jour la dernière connexion
            user.last_login_at = datetime.now(timezone.utc)
            self.db.session.commit()

            self.logger.info(f"Authentification réussie pour: {username}")

            return user, {"access_token": access_token, "refresh_token": refresh_token}

        except Exception as e:
            self.logger.error(
                f"Erreur lors de l'authentification: {str(e)}", exc_info=True
            )
            return None, None

    def request_password_reset(self, email):
        """
        Demande de réinitialisation de mot de passe.

        Args:
            email (str): L'email de l'utilisateur

        Returns:
            bool: True si la demande a été traitée, False sinon
        """
        try:
            from datetime import timedelta

            from flask import url_for

            from app.utils.email import send_password_reset_email
            from core.models.user import User

            # Vérifier si l'utilisateur existe
            user = User.query.filter_by(email=email.lower()).first()
            if not user:
                # Retourner True pour ne pas révéler l'existence ou non du compte
                return True

            # Générer un token de réinitialisation
            import secrets

            reset_token = secrets.token_urlsafe(32)

            # Stocker le hash du token en base de données (jamais en clair)
            user.reset_token = generate_password_hash(reset_token)
            user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
            _db = self.db or __import__("core.extensions", fromlist=["db"]).db
            _db.session.commit()

            # Construire l'URL de réinitialisation
            reset_url = url_for(
                "auth.reset_password", token=reset_token, _external=True
            )

            # Envoyer l'email
            try:
                send_password_reset_email(user.email, reset_url)
                self.logger.info(f"Email de réinitialisation envoyé à {user.email}")
            except Exception as email_error:
                self.logger.error(f"Échec envoi email de reset: {email_error}")

            return True

        except Exception as e:
            self.logger.error(
                f"Erreur lors de la demande de reset: {str(e)}", exc_info=True
            )
            return False

    def reset_password_with_token(self, token, new_password):
        """
        Réinitialise le mot de passe avec un token.

        Args:
            token (str): Le token de réinitialisation
            new_password (str): Le nouveau mot de passe

        Returns:
            bool: True si le reset a réussi, False sinon
        """
        try:
            from core.models.user import User

            if not token or len(token) < 20:
                self.logger.warning("Token de reset trop court ou vide")
                return False

            _db = self.db or __import__("core.extensions", fromlist=["db"]).db

            # Rechercher les utilisateurs avec un reset en cours (token hashé en DB)
            candidates = User.query.filter(
                User.reset_token.isnot(None),
                User.reset_token_expires >= datetime.now(timezone.utc),
            ).all()

            user = None
            for candidate in candidates:
                if check_password_hash(candidate.reset_token, token):
                    user = candidate
                    break

            if not user:
                self.logger.warning("Token de reset invalide ou expiré")
                return False

            # Réinitialiser le mot de passe (le setter horodate le changement :
            # sessions et jetons ouverts avant sont coupés)
            user.password = new_password
            user.reset_token = None
            user.reset_token_expires = None
            # Le lien reçu par e-mail prouve la possession du compte : lever un
            # éventuel verrouillage dû aux tentatives échouées
            user.login_attempts = 0
            user.is_locked = False
            _db.session.commit()
            self.logger.info(f"Mot de passe réinitialisé pour {user.email}")
            return True

        except Exception as e:
            self.logger.error(
                f"Erreur lors du reset avec token: {str(e)}", exc_info=True
            )
            return False
