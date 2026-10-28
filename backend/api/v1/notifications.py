"""
API REST v1 — Notifications.

Routes:
    GET    /api/v1/notifications                    Liste paginée des notifications
    GET    /api/v1/notifications/unread-count        Nombre de notifications non lues
    POST   /api/v1/notifications/mark-as-read/<id>   Marquer une notification comme lue
    POST   /api/v1/notifications/mark-all-read       Marquer toutes comme lues
"""

import logging

from flask import request
from flask_login import current_user, login_required

from core.services.notifications import NotificationService

from . import api_v1_bp
from .helpers import api_error, api_success

logger = logging.getLogger(__name__)


@api_v1_bp.route("/notifications", methods=["GET"])
@login_required
def v1_list_notifications():
    """Liste paginée des notifications de l'utilisateur."""
    try:
        unread_only = request.args.get("unread_only", "false").lower() == "true"
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)

        notifications = NotificationService.get_user_notifications(
            user_id=current_user.id,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )

        return api_success(
            {
                "notifications": [n.to_dict() for n in notifications],
                "count": len(notifications),
                "limit": limit,
                "offset": offset,
            }
        )
    except Exception as e:
        logger.error(f"Erreur liste notifications: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/notifications/unread-count", methods=["GET"])
@login_required
def v1_unread_notifications_count():
    """Retourne le nombre de notifications non lues."""
    try:
        notifications = NotificationService.get_user_notifications(
            user_id=current_user.id, unread_only=True
        )
        count = len(notifications)
        return api_success({"success": True, "unread_count": count})
    except Exception as e:
        logger.error(f"Erreur comptage notifications non lues: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/notifications/mark-as-read/<int:notification_id>", methods=["POST"])
@login_required
def v1_mark_notification_read(notification_id):
    """Marque une notification comme lue."""
    try:
        success = NotificationService.mark_as_read(
            notification_id=notification_id, user_id=current_user.id
        )
        if success:
            return api_success(
                {"success": True}, message="Notification marquée comme lue."
            )
        return api_error("Notification non trouvée.", 404)
    except Exception as e:
        logger.error(
            f"Erreur marquage notification {notification_id}: {e}", exc_info=True
        )
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/notifications/mark-all-read", methods=["POST"])
@login_required
def v1_mark_all_notifications_read():
    """Marque toutes les notifications comme lues."""
    try:
        updated = NotificationService.mark_all_as_read(user_id=current_user.id)
        logger.info(
            f"Marquage de {updated} notifications comme lues pour utilisateur {current_user.id}"
        )
        return api_success(
            {"success": True},
            message=f"{updated} notification(s) marquée(s) comme lue(s).",
        )
    except Exception as e:
        logger.error(f"Erreur marquage notifications comme lues: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)
