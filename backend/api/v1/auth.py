"""
API REST v1 — Authentification.

Routes:
    POST   /api/v1/auth/login          Connexion (JWT)
    POST   /api/v1/auth/register       Inscription
    POST   /api/v1/auth/refresh        Rafraîchir le token
    POST   /api/v1/auth/logout         Déconnexion (révocation JWT)
    GET    /api/v1/auth/user           Utilisateur courant (JWT)
    GET    /api/v1/auth/check          Vérification état d'authentification (session)
    POST   /api/v1/auth/2fa/resend     Renvoyer code 2FA (TOTP)
    POST   /api/v1/auth/2fa/resend-email  Renvoyer code 2FA par email
"""

import logging
from datetime import datetime, timezone

from flask import request, session
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import current_user, login_required

from core.extensions import db
from core.models.user import User

from . import api_v1_bp
from .helpers import api_error, api_success

logger = logging.getLogger(__name__)

# Rate limiter pour les endpoints d'authentification
auth_limiter = Limiter(key_func=get_remote_address)


@api_v1_bp.route("/auth/login", methods=["POST"])
@auth_limiter.limit("5 per minute")
def v1_auth_login():
    """Connexion API avec JWT."""
    try:
        pass

        from core.services.auth.auth_service import AuthSecurityService
        from core.services.auth.security_service import init_security_service

        data = request.get_json(silent=True) or {}

        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return api_error("Email et mot de passe requis", 400)

        if not isinstance(email, str) or not isinstance(password, str):
            return api_error("Email et mot de passe doivent être des chaînes", 400)

        if len(email) > 255 or len(password) > 128:
            return api_error("Email ou mot de passe trop long", 400)

        security_svc = init_security_service(db)

        lookup_user = User.query.filter_by(email=email.lower()).first()
        if lookup_user:
            is_locked, _ = security_svc.is_account_locked(lookup_user.id)
            if is_locked:
                return api_error(
                    "Compte temporairement verrouillé. Réessayez plus tard.", 429
                )

        auth_service = AuthSecurityService(db=db)
        result = auth_service.authenticate(email, password)

        if not result or result[0] is None:
            if lookup_user:
                security_svc.record_login_attempt(lookup_user.id, success=False)
            return api_error("Email ou mot de passe incorrect", 401)

        user, tokens = result

        # 2FA activée : aucun jeton tant que le code n'est pas vérifié
        # (POST /auth/2fa/verify). Avant, le mot de passe seul suffisait :
        # le Bearer JWT donnant accès à toutes les routes @login_required, la
        # 2FA était entièrement contournable par l'API.
        if user.two_factor_enabled:
            from core.security.two_factor_flow import demarrer_2fa, jeton_2fa

            methode, envoye = demarrer_2fa(user)
            return api_success(
                {
                    "two_factor_required": True,
                    "two_factor_method": methode,
                    "two_factor_token": jeton_2fa(user),
                    "code_sent": envoye,
                },
                message="Code de vérification requis",
            )

        security_svc.record_login_attempt(user.id, success=True)
        logger.info(f"Connexion API réussie pour: {user.email}")

        # Enregistrer l'appareil
        _register_api_login_device(user)

        return api_success(
            {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                },
            }
        )

    except Exception as e:
        logger.error(f"Erreur connexion API: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/auth/2fa/verify", methods=["POST"])
@auth_limiter.limit("10 per minute")
def v1_auth_2fa_verify():
    """Étape 2 de la connexion API : échange two_factor_token + code contre les jetons.

    Corps JSON : {"two_factor_token": "...", "code": "123456"} ou
    {"two_factor_token": "...", "backup_code": "..."}. Chaque code faux compte
    comme un échec de connexion (verrouillage au bout de 5).
    """
    try:
        from flask_jwt_extended import create_access_token, create_refresh_token

        from core.security.two_factor_flow import utilisateur_du_jeton_2fa, verifier_2fa
        from core.services.auth.security_service import init_security_service

        data = request.get_json(silent=True) or {}
        user = utilisateur_du_jeton_2fa(data.get("two_factor_token"))
        if user is None:
            return api_error("Jeton de vérification invalide ou expiré", 401)

        security_svc = init_security_service(db)
        if security_svc.is_account_locked(user.id)[0]:
            return api_error(
                "Compte temporairement verrouillé. Réessayez plus tard.", 429
            )

        ok, message = verifier_2fa(
            user, code=data.get("code", ""), backup_code=data.get("backup_code", "")
        )
        if not ok:
            non_verrouille, _ = security_svc.record_login_attempt(
                user.id, success=False
            )
            if not non_verrouille:
                user.email_2fa_code = None
                db.session.commit()
                return api_error(
                    "Compte temporairement verrouillé. Réessayez plus tard.", 429
                )
            return api_error(message or "Code de vérification invalide", 401)

        security_svc.record_login_attempt(user.id, success=True)
        logger.info(f"Connexion API (2FA) réussie pour: {user.email}")
        _register_api_login_device(user)
        return api_success(
            {
                "access_token": create_access_token(identity=user.id),
                "refresh_token": create_refresh_token(identity=user.id),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                },
            }
        )
    except Exception as e:
        logger.error(f"Erreur vérification 2FA API: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/auth/register", methods=["POST"])
@auth_limiter.limit("3 per hour")
def v1_auth_register():
    """Inscription API."""
    try:
        from core.services.auth.security_service import init_security_service
        from core.services.user import UserService

        data = request.get_json() or {}

        required_fields = ["email", "password", "username"]
        if not all(field in data for field in required_fields):
            return api_error("Données manquantes", 400)

        security_svc = init_security_service(db)
        is_valid, error_msg = security_svc.validate_password_strength(data["password"])
        if not is_valid:
            return api_error(error_msg, 400)

        user_service = UserService()
        user = user_service.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
        )

        if user:
            logger.info(f"Nouvel utilisateur créé via API: {user.email}")
            return api_success(
                {
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "username": user.username,
                    },
                },
                message="Utilisateur créé avec succès",
                status_code=201,
            )
        else:
            return api_error("Erreur lors de la création du compte", 400)

    except Exception as e:
        logger.error(f"Erreur inscription API: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)
def v1_auth_refresh():
    """Rafraîchissement du token d'accès."""
    try:
        current_user_id = get_jwt_identity()
        new_token = create_access_token(identity=current_user_id)
        return api_success({"access_token": new_token})

    except Exception as e:
        logger.error(f"Erreur rafraîchissement: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/auth/logout", methods=["POST"])
@jwt_required()
def v1_auth_logout():
    """Déconnexion API (invalidation du token via blacklist)."""
    try:
        from core.models.token_blacklist import TokenBlacklist

        jwt_data = get_jwt()
        jti = jwt_data["jti"]
        exp = datetime.fromtimestamp(jwt_data["exp"], tz=timezone.utc)
        TokenBlacklist.revoke_token(jti, exp)

        # Révoquer aussi le refresh token si fourni dans le body
        body = request.get_json(silent=True) or {}
        refresh_token_raw = body.get("refresh_token") if body else None
        if refresh_token_raw and isinstance(refresh_token_raw, str):
            try:
                from flask_jwt_extended import decode_token

                decoded = decode_token(refresh_token_raw)
                refresh_jti = decoded.get("jti")
                refresh_exp = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
                if refresh_jti:
                    TokenBlacklist.revoke_token(refresh_jti, refresh_exp)
            except Exception:
                logger.debug("Token refresh invalide ou expire, ignore")

        logger.info("Déconnexion API - token(s) révoqué(s)")
        return api_success(message="Déconnexion réussie")

    except Exception as e:
        logger.error(f"Erreur déconnexion API: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/auth/user", methods=["GET"])
@jwt_required()
def v1_auth_user():
    """Récupération des informations de l'utilisateur connecté (JWT)."""
    try:
        current_user_id = get_jwt_identity()
        user = db.session.get(User, current_user_id)
        if not user:
            return api_error("Utilisateur non trouvé", 404)
        return api_success(
            {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "is_active": user.is_active,
                },
            }
        )

    except Exception as e:
        logger.error(f"Erreur récupération utilisateur: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/auth/check", methods=["GET"])
@login_required
def v1_auth_check():
    """Vérification de l'état d'authentification (session)."""
    return api_success(
        {
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "username": current_user.username,
            },
        }
    )


@api_v1_bp.route("/auth/2fa/resend", methods=["POST"])
@auth_limiter.limit("5 per minute")
def v1_resend_2fa_code():
    """Renvoie un code 2FA (TOTP se renouvelle automatiquement)."""
    if "2fa_user_id" not in session:
        return api_error("Session expirée", 400)

    user = db.session.get(User, session["2fa_user_id"])
    if not user:
        return api_error("Utilisateur introuvable", 400)

    return api_success(
        message="Les codes TOTP se renouvellent automatiquement toutes les 30 secondes dans votre application d'authentification."
    )


@api_v1_bp.route("/auth/2fa/resend-email", methods=["POST"])
@auth_limiter.limit("5 per minute")
def v1_resend_email_2fa_code():
    """Renvoie un nouveau code 2FA par email."""
    if "2fa_user_id" not in session:
        return api_error("Session expirée", 400)

    user = db.session.get(User, session["2fa_user_id"])
    if not user or not user.two_factor_enabled:
        return api_error("Utilisateur introuvable ou 2FA non activée", 400)

    try:
        from core.security.email_2fa import EmailTwoFactorAuth

        email_2fa = EmailTwoFactorAuth()
        email_2fa.clean_expired_codes()
        code = email_2fa.generate_email_code()

        if not email_2fa.store_email_2fa_code(user, code):
            return api_error("Erreur lors de la génération du code", 500)

        if not email_2fa.send_2fa_email(user.email, code):
            return api_error("Erreur lors de l'envoi de l'email", 500)

        logger.info(f"Code 2FA renvoyé par email à {user.email}")

        return api_success(
            message=f"Un nouveau code a été envoyé par email à {user.email}. Il expire dans 15 minutes."
        )

    except Exception as e:
        logger.error(f"Erreur renvoi code email 2FA: {e}", exc_info=True)
        return api_error("Erreur lors de l'envoi du code", 500)


def _register_api_login_device(user):
    """Enregistre l'appareil utilisé pour la connexion API."""
    try:
        import hashlib
        from datetime import timezone

        from user_agents import parse as parse_ua

        from core.services.devices.device_services import DeviceService

        ua_string = request.headers.get("User-Agent", "")
        # IP de repli si remote_addr absent (valeur, pas un bind socket)
        ip = request.remote_addr or "0.0.0.0"  # nosec B104
        ua = parse_ua(ua_string)

        device_id = hashlib.sha256(f"{ua_string}:{ip}".encode()).hexdigest()[:64]

        if ua.is_mobile:
            device_type = "mobile"
        elif ua.is_tablet:
            device_type = "tablet"
        else:
            device_type = "desktop"

        browser = ua.browser.family or "Unknown"
        os_name = ua.os.family or "Unknown"
        name = f"{browser} sur {os_name}"

        device_data = {
            "name": name,
            "device_id": device_id,
            "device_type": device_type,
            "os": os_name,
            "os_version": ua.os.version_string or None,
            "browser": browser,
            "browser_version": ua.browser.version_string or None,
        }

        device, _ = DeviceService.register_device(
            user_id=user.id,
            device_data=device_data,
            ip_address=ip,
            user_agent=ua_string,
        )

        if device:
            device.last_used = datetime.now(timezone.utc)
            device.ip_address = ip
            db.session.commit()

    except Exception as e:
        logger.warning(f"Impossible d'enregistrer l'appareil: {e}")
