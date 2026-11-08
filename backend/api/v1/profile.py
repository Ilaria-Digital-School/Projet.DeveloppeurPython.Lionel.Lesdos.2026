"""
API REST v1 — Profil utilisateur.

Routes:
    POST   /api/v1/profil/picture                 Upload avatar
    POST   /api/v1/profil/notifications            Préférences de notification
    POST   /api/v1/profil/2fa/enable               Activer 2FA
    POST   /api/v1/profil/2fa/verify               Vérifier code 2FA
    POST   /api/v1/profil/2fa/disable              Désactiver 2FA
    GET    /api/v1/profil/2fa/backup-codes         Codes de récupération
    POST   /api/v1/profil/2fa/regenerate-backup-codes  Régénérer codes de récupération
    GET    /api/v1/profil/2fa/status               Statut 2FA
    POST   /api/v1/profil/email-2fa/send-code      Envoyer code 2FA email
    POST   /api/v1/profil/email-2fa/verify-code    Vérifier code 2FA email
    POST   /api/v1/profil/email-2fa/disable        Désactiver 2FA email
"""

import hashlib
import json
import logging
import os

from flask import current_app, request
from flask_login import current_user, login_required
from PIL import Image, UnidentifiedImageError

from core.extensions import db

from . import api_v1_bp
from .auth import auth_limiter
from .helpers import api_error, api_success

logger = logging.getLogger(__name__)


@api_v1_bp.route("/profil/picture", methods=["POST"])
@login_required
def api_profil_picture():
    """Upload de la photo de profil."""
    try:
        if "profile_picture" not in request.files:
            return api_error("Aucun fichier envoyé", 400)

        file = request.files["profile_picture"]
        if file.filename == "":
            return api_error("Aucun fichier sélectionné", 400)

        allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in allowed_extensions:
            return api_error("Format de fichier non supporté", 400)

        # Vérifier la taille du fichier (max 5 MB)
        max_size = 5 * 1024 * 1024
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        if file_size > max_size:
            return api_error("Le fichier est trop volumineux (maximum 5 Mo)", 400)

        # Vérifier les magic bytes pour valider le type réel du fichier
        header = file.read(16)
        file.seek(0)
        valid_signatures = {
            "png": [b"\x89PNG\r\n\x1a\n"],
            "jpg": [b"\xff\xd8\xff"],
            "jpeg": [b"\xff\xd8\xff"],
            "gif": [b"GIF87a", b"GIF89a"],
            "webp": [b"RIFF"],
        }
        signatures = valid_signatures.get(ext, [])
        if not any(header.startswith(sig) for sig in signatures):
            return api_error(
                "Le contenu du fichier ne correspond pas à son extension", 400
            )

        # Ré-encoder l'image avec Pillow : neutralise les fichiers polyglottes
        # (ex: GIF/JavaScript) et supprime les métadonnées (EXIF, GPS...)
        try:
            img = Image.open(file.stream)
            img.load()
        except UnidentifiedImageError, Image.DecompressionBombError, OSError:
            return api_error("Image invalide ou corrompue", 400)

        upload_folder = os.path.join(
            current_app.static_folder or "static", "uploads", "avatars"
        )
        os.makedirs(upload_folder, exist_ok=True)

        filename = f"user_{current_user.id}.{ext}"
        filepath = os.path.join(upload_folder, filename)

        pil_format = {
            "png": "PNG",
            "jpg": "JPEG",
            "jpeg": "JPEG",
            "gif": "GIF",
            "webp": "WEBP",
        }[ext]
        save_kwargs = {}
        if pil_format == "JPEG" and img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        if getattr(img, "is_animated", False):
            save_kwargs["save_all"] = True  # préserver les GIF/WebP animés
        img.save(filepath, format=pil_format, **save_kwargs)

        current_user.avatar_url = f"/static/uploads/avatars/{filename}"
        db.session.commit()

        return api_success(
            {
                "picture_url": current_user.avatar_url,
            },
            message="Photo de profil mise à jour",
        )

    except Exception as e:
        logger.error(f"Erreur upload photo profil: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/profil/notifications", methods=["POST"])
@login_required
def api_profil_notifications():
    """Met à jour les préférences de notification du profil."""
    try:
        data = request.get_json()
        if not data:
            return api_error("Données JSON requises", 400)

        from core.models.notification_preference import NotificationPreference

        pref = NotificationPreference.query.filter_by(user_id=current_user.id).first()
        if not pref:
            pref = NotificationPreference(user_id=current_user.id)
            db.session.add(pref)

        for key in [
            "email_notifications",
            "push_notifications",
            "monthly_report",
            "budget_alerts",
        ]:
            if key in data:
                setattr(pref, key, data[key])

        db.session.commit()
        return api_success(message="Préférences de notification mises à jour")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur préférences notification profil: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


# ── 2FA TOTP ─────────────────────────────────────────────────────────────────


@api_v1_bp.route("/profil/2fa/enable", methods=["POST"])
@login_required
def api_profil_2fa_enable():
    """Active la 2FA TOTP pour l'utilisateur."""
    try:
        from core.security.security_2fa import TwoFactorAuth

        secret = TwoFactorAuth.generate_secret()
        qr_uri = TwoFactorAuth.get_provisioning_uri(secret, current_user.email)

        current_user.two_factor_secret = secret
        db.session.commit()

        return api_success(
            {
                "secret": secret,
                "qr_uri": qr_uri,
            },
            message="Scannez le QR code avec votre application 2FA",
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur activation 2FA: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/profil/2fa/verify", methods=["POST"])
@login_required
def api_profil_2fa_verify():
    """Vérifie un code 2FA et finalise l'activation."""
    try:
        from core.security.security_2fa import TwoFactorAuth

        data = request.get_json() or {}
        code = data.get("code", "").strip()

        if not code:
            return api_error("Code de vérification requis", 400)

        if not current_user.two_factor_secret:
            return api_error("2FA non initialisée. Appelez /enable d'abord.", 400)

        is_valid, error_msg = TwoFactorAuth.verify_code(
            current_user.two_factor_secret, code
        )
        if not is_valid:
            return api_error(f"Code invalide: {error_msg}", 400)

        # Générer les codes de récupération
        backup_codes = TwoFactorAuth.generate_backup_codes()
        hashed_codes = [hashlib.sha256(c.encode()).hexdigest() for c in backup_codes]

        current_user.two_factor_enabled = True
        current_user.two_factor_backup_codes = json.dumps(hashed_codes)
        db.session.commit()

        logger.info(f"2FA activée pour {current_user.email}")

        return api_success(
            {
                "backup_codes": backup_codes,
            },
            message="2FA activée avec succès. Conservez vos codes de récupération.",
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur vérification 2FA: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


def _alerter_desactivation_2fa(user):
    """E-mail de sécurité : prévient le titulaire si quelqu'un d'autre l'a fait."""
    try:
        from core.services.notifications import NotificationService

        NotificationService.send_notification(
            user_id=user.id,
            title="Double authentification désactivée",
            message=(
                "La double authentification de votre compte vient d'être désactivée. "
                "Si vous n'êtes pas à l'origine de ce changement, changez votre mot "
                "de passe immédiatement."
            ),
            notification_type="security_alert",
            action_url="/profile/",
            send_email=True,
            force_send=True,
        )
    except Exception as e:
        logger.warning(f"Alerte de désactivation 2FA non envoyée: {e}")


@api_v1_bp.route("/profil/2fa/disable", methods=["POST"])
@login_required
@auth_limiter.limit("5 per hour")
def api_profil_2fa_disable():
    """Désactive la 2FA TOTP."""
    try:
        data = request.get_json() or {}
        password = data.get("password", "")

        if not password:
            return api_error("Mot de passe requis pour désactiver la 2FA", 400)

        if not current_user.check_password(password):
            return api_error("Mot de passe incorrect", 401)

        current_user.two_factor_enabled = False
        current_user.two_factor_secret = None
        current_user.two_factor_backup_codes = None
        db.session.commit()
        _alerter_desactivation_2fa(current_user)

        logger.info(f"2FA désactivée pour {current_user.email}")
        return api_success(message="2FA désactivée avec succès")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur désactivation 2FA: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/profil/2fa/backup-codes", methods=["GET"])
@login_required
def api_profil_2fa_backup_codes():
    """Récupère le nombre de codes de récupération restants."""
    try:
        if not current_user.two_factor_enabled:
            return api_error("2FA non activée", 400)

        backup_codes = json.loads(current_user.two_factor_backup_codes or "[]")
        return api_success({"remaining_codes": len(backup_codes)})

    except Exception as e:
        logger.error(f"Erreur récupération codes backup: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/profil/2fa/regenerate-backup-codes", methods=["POST"])
@login_required
def api_profil_2fa_regenerate_backup_codes():
    """Régénère les codes de récupération 2FA."""
    try:
        from core.security.security_2fa import TwoFactorAuth

        if not current_user.two_factor_enabled:
            return api_error("2FA non activée", 400)

        data = request.get_json() or {}
        password = data.get("password", "")

        if not password or not current_user.check_password(password):
            return api_error("Mot de passe incorrect", 401)

        backup_codes = TwoFactorAuth.generate_backup_codes()
        hashed_codes = [hashlib.sha256(c.encode()).hexdigest() for c in backup_codes]
        current_user.two_factor_backup_codes = json.dumps(hashed_codes)
        db.session.commit()

        logger.info(f"Codes de récupération 2FA régénérés pour {current_user.email}")

        return api_success(
            {
                "backup_codes": backup_codes,
            },
            message="Codes de récupération régénérés.",
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur régénération codes backup: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/profil/2fa/status", methods=["GET"])
@login_required
def api_profil_2fa_status():
    """Retourne le statut 2FA de l'utilisateur."""
    try:
        has_totp = bool(
            current_user.two_factor_secret and current_user.two_factor_enabled
        )
        has_email_2fa = False

        if (
            hasattr(current_user, "two_factor_secret")
            and current_user.two_factor_secret
        ):
            if "|" in str(current_user.two_factor_secret):
                has_email_2fa = True
                has_totp = False

        return api_success(
            {
                "two_factor_enabled": (
                    current_user.two_factor_enabled
                    if hasattr(current_user, "two_factor_enabled")
                    else False
                ),
                "totp_enabled": has_totp,
                "email_2fa_enabled": has_email_2fa,
                "backup_codes_count": len(
                    json.loads(current_user.two_factor_backup_codes or "[]")
                ),
            }
        )

    except Exception as e:
        logger.error(f"Erreur statut 2FA: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


# ── 2FA Email ────────────────────────────────────────────────────────────────


@api_v1_bp.route("/profil/email-2fa/send-code", methods=["POST"])
@login_required
def api_profil_email_2fa_send_code():
    """Envoie un code 2FA par email pour activer la 2FA email."""
    try:
        from core.security.email_2fa import EmailTwoFactorAuth

        email_2fa = EmailTwoFactorAuth()
        code = email_2fa.generate_email_code()

        if not email_2fa.store_email_2fa_code(current_user, code):
            return api_error("Erreur lors de la génération du code", 500)

        if not email_2fa.send_2fa_email(current_user.email, code):
            return api_error("Erreur lors de l'envoi de l'email", 500)

        logger.info(f"Code 2FA email envoyé à {current_user.email}")
        return api_success(
            message=f"Code envoyé à {current_user.email}. Il expire dans 15 minutes."
        )

    except Exception as e:
        logger.error(f"Erreur envoi code 2FA email: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/profil/email-2fa/verify-code", methods=["POST"])
@login_required
def api_profil_email_2fa_verify_code():
    """Vérifie le code 2FA email et active la 2FA email."""
    try:
        from core.security.email_2fa import EmailTwoFactorAuth

        data = request.get_json() or {}
        code = data.get("code", "").strip()

        if not code:
            return api_error("Code requis", 400)

        email_2fa = EmailTwoFactorAuth()
        is_valid, error_msg = email_2fa.verify_email_2fa_code(current_user, code)

        if not is_valid:
            return api_error(f"Code invalide: {error_msg}", 400)

        current_user.two_factor_enabled = True
        db.session.commit()

        logger.info(f"2FA email activée pour {current_user.email}")
        return api_success(message="2FA par email activée avec succès")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur vérification code 2FA email: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/profil/email-2fa/disable", methods=["POST"])
@login_required
@auth_limiter.limit("5 per hour")
def api_profil_email_2fa_disable():
    """Désactive la 2FA par email."""
    try:
        data = request.get_json() or {}
        password = data.get("password", "")

        if not password or not current_user.check_password(password):
            return api_error("Mot de passe incorrect", 401)

        current_user.two_factor_enabled = False
        current_user.two_factor_secret = None
        db.session.commit()
        _alerter_desactivation_2fa(current_user)

        logger.info(f"2FA email désactivée pour {current_user.email}")
        return api_success(message="2FA par email désactivée avec succès")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur désactivation 2FA email: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)
