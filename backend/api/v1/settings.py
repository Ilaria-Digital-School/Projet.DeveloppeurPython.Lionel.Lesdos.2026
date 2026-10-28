"""
API REST v1 — Settings (Paramètres).

Routes:
    GET    /api/v1/settings                 Récupérer tous les paramètres
    PUT    /api/v1/settings                 Mettre à jour les paramètres généraux
    POST   /api/v1/settings                 Mettre à jour les préférences de notification
    GET    /api/v1/settings/notifications   Récupérer les préférences de notification
    POST   /api/v1/settings/notifications   Mettre à jour les préférences de notification
    POST   /api/v1/settings/password        Changer le mot de passe
    GET    /api/v1/settings/export          Exporter les données utilisateur
    DELETE /api/v1/settings/account          Supprimer le compte utilisateur
"""

import logging
from io import BytesIO

from flask import request, send_file
from flask_login import current_user, login_required

from core.extensions import db
from core.models.notification_preference import NotificationPreference
from core.services.settings.setting_services import SettingService

from . import api_v1_bp
from .auth import auth_limiter
from .helpers import api_error, api_success

logger = logging.getLogger(__name__)


@api_v1_bp.route("/settings", methods=["GET"])
@login_required
def v1_get_all_settings():
    """Récupère tous les paramètres utilisateur."""
    try:
        service = SettingService()
        all_settings = service.get_user_settings(current_user.id)

        # Regrouper les paramètres par catégorie
        general = {}
        for key, value in all_settings.items():
            general[key] = value

        pref = NotificationPreference.query.filter_by(user_id=current_user.id).first()
        notifications = {
            "email_notifications": pref.email_notifications if pref else True,
            "push_notifications": pref.push_notifications if pref else True,
            "monthly_report": pref.monthly_report if pref else True,
            "budget_alerts": pref.budget_alerts if pref else True,
        }

        return api_success({"general": general, "notifications": notifications})

    except Exception as e:
        logger.error(f"Erreur récupération paramètres: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


ALLOWED_SETTINGS_KEYS = {
    "language",
    "currency",
    "theme",
    "date_format",
    "timezone",
    "number_format",
    "first_day_of_week",
    "default_account",
}


@api_v1_bp.route("/settings", methods=["PUT"])
@login_required
def v1_update_general_settings():
    """Met à jour les paramètres généraux."""
    try:
        data = request.get_json()
        if not data:
            return api_error("Données JSON requises", 400)

        service = SettingService()
        general = data.get("general", {})
        for key, value in general.items():
            if key not in ALLOWED_SETTINGS_KEYS:
                continue
            service.set_user_setting(current_user.id, key, value)

        db.session.commit()
        return api_success(message="Paramètres mis à jour avec succès")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur mise à jour paramètres: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/settings/password", methods=["POST"])
@login_required
@auth_limiter.limit("5 per hour")
def v1_change_password():
    """Change le mot de passe utilisateur."""
    try:
        data = request.get_json()
        if not data:
            return api_error("Données JSON requises", 400)

        current_password = data.get("current_password")
        new_password = data.get("new_password")

        if not current_password or not new_password:
            return api_error("Mot de passe actuel et nouveau requis", 400)

        # Valider la complexité du mot de passe (mêmes règles que l'inscription)
        from core.services.auth.security_service import SecurityService

        security_service = SecurityService(db)
        is_valid, error_msg = security_service.validate_password_strength(new_password)
        if not is_valid:
            return api_error(error_msg, 400)

        if not current_user.check_password(current_password):
            return api_error("Mot de passe actuel incorrect", 403)

        current_user.password = new_password
        db.session.commit()
        logger.info(f"Mot de passe mis à jour pour utilisateur {current_user.id}")
        return api_success(message="Mot de passe mis à jour avec succès")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur changement mot de passe: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/settings/export", methods=["GET"])
@login_required
def v1_export_user_data():
    """Exporte les données utilisateur au format JSON."""
    try:
        service = SettingService()
        result = service.export_user_data(
            current_user.id, export_format="json", include_attachments=False
        )

        if result:
            export_data, filename, mime_type = result
            return send_file(
                BytesIO(export_data.getvalue()),
                mimetype=mime_type,
                as_attachment=True,
                download_name=filename,
            )
        return api_error("Aucune donnée à exporter", 404)

    except Exception as e:
        logger.error(f"Erreur export données: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/settings/account", methods=["DELETE"])
@login_required
@auth_limiter.limit("3 per hour")
def v1_delete_account():
    """Planifie la suppression du compte avec un delai de grace de 7 jours."""
    try:
        data = request.get_json()
        if not data or not data.get("password"):
            return api_error("Mot de passe requis pour confirmer la suppression", 400)

        if not current_user.check_password(data["password"]):
            return api_error("Mot de passe incorrect", 403)

        from core.services.user.account_deletion import planifier_suppression

        # Sauvegarder l'ID avant logout
        user_id = current_user.id

        # Désactive le compte et planifie la purge définitive (7 jours de grâce).
        # Avant, la date n'était enregistrée nulle part et aucune purge n'existait.
        deletion_date = planifier_suppression(current_user._get_current_object())

        from flask_login import logout_user

        logout_user()

        logger.info(
            f"Suppression planifiée pour utilisateur {user_id} "
            f"(suppression definitive le {deletion_date.isoformat()})"
        )
        return api_success(
            message="Compte désactivé. La suppression définitive aura lieu dans 7 jours. "
            "Reconnectez-vous avant cette date pour annuler."
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur suppression compte: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/settings/notifications", methods=["GET"])
@login_required
def v1_get_notification_settings():
    """Récupère les préférences de notification."""
    try:
        prefs = NotificationPreference.query.filter_by(user_id=current_user.id).all()

        # Construire un dict type → préférences
        prefs_dict = {}
        for pref in prefs:
            prefs_dict[pref.notification_type] = {
                "email": pref.email,
                "push": pref.push,
                "sms": pref.sms,
                "frequency": pref.frequency,
            }

        # Valeurs par défaut pour les types courants
        defaults = {"email": True, "push": True, "sms": False, "frequency": "immediate"}

        return api_success(
            {
                "email_notifications": prefs_dict.get("email", defaults).get(
                    "email", True
                ),
                "push_notifications": prefs_dict.get("push", defaults).get(
                    "push", True
                ),
                "budget_alerts": prefs_dict.get("budget_alert", defaults).get(
                    "email", True
                ),
                "monthly_report": prefs_dict.get("monthly_report", defaults).get(
                    "email", True
                ),
                "preferences": prefs_dict,
            }
        )

    except Exception as e:
        logger.error(
            f"Erreur récupération préférences notifications: {e}", exc_info=True
        )
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/settings/notifications", methods=["POST"])
@login_required
def v1_update_notification_settings():
    """Met à jour les préférences de notification."""
    try:
        data = request.get_json()
        if not data:
            return api_error("Données JSON requises", 400)

        # Mapper les clés API vers les types de notification
        type_mapping = {
            "email_notifications": "email",
            "push_notifications": "push",
            "budget_alerts": "budget_alert",
            "monthly_report": "monthly_report",
            "transaction_notifications": "transaction",
        }

        for api_key, notif_type in type_mapping.items():
            if api_key in data:
                pref = NotificationPreference.query.filter_by(
                    user_id=current_user.id, notification_type=notif_type
                ).first()

                if not pref:
                    pref = NotificationPreference(
                        user_id=current_user.id,
                        notification_type=notif_type,
                        email=bool(data[api_key]),
                        push=bool(data[api_key]),
                    )
                    db.session.add(pref)
                else:
                    pref.email = bool(data[api_key])
                    pref.push = bool(data[api_key])

        db.session.commit()

        return api_success(
            message="Préférences de notification mises à jour avec succès"
        )

    except Exception as e:
        db.session.rollback()
        logger.error(
            f"Erreur mise à jour préférences notifications: {e}", exc_info=True
        )
        return api_error("Une erreur interne est survenue", 500)
