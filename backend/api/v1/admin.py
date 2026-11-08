"""
API REST v1 — Administration.

Routes:
    GET    /api/v1/admin/dashboard-stats     Statistiques dashboard admin
    GET    /api/v1/admin/system-metrics       Métriques système
    GET    /api/v1/admin/database-metrics     Métriques base de données
    GET    /api/v1/admin/active-sessions      Sessions actives
    GET    /api/v1/admin/system-logs          Logs système
    GET    /api/v1/admin/alerts               Alertes
    GET    /api/v1/admin/monitoring-summary   Résumé monitoring
    GET    /api/v1/admin/users                Liste des utilisateurs
    GET    /api/v1/admin/users/<id>/activity      Activité récente d'un utilisateur
    GET    /api/v1/admin/users/<id>/accounts      Comptes d'un utilisateur
    GET    /api/v1/admin/users/<id>/transactions  Transactions paginées d'un utilisateur
    POST   /api/v1/admin/users/<id>/toggle    Activer/désactiver un utilisateur
    POST   /api/v1/admin/users/<id>/reset-2fa Réinitialiser la 2FA
    POST   /api/v1/admin/users/<id>/reset-password  Réinitialiser le mot de passe
"""

import logging

from flask import request
from flask_login import login_required

from core.decorators import admin_required
from core.services.admin.admin_services import AdminService
from core.services.admin.monitoring_service import MonitoringService

from . import api_v1_bp
from .auth import auth_limiter
from .helpers import api_error, api_paginated, api_success

logger = logging.getLogger(__name__)


@api_v1_bp.route("/admin/dashboard-stats", methods=["GET"])
@login_required
@admin_required
def v1_admin_dashboard_stats():
    """Statistiques du dashboard admin."""
    try:
        stats = AdminService.get_dashboard_stats()
        return api_success(stats)
    except Exception as e:
        logger.error(f"Erreur stats admin: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/admin/system-metrics", methods=["GET"])
@login_required
@admin_required
def v1_admin_system_metrics():
    """Métriques système."""
    try:
        metrics = MonitoringService.get_system_metrics()
        return api_success(metrics)
    except Exception as e:
        logger.error(f"Erreur métriques système: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/admin/database-metrics", methods=["GET"])
@login_required
@admin_required
def v1_admin_database_metrics():
    """Métriques base de données."""
    try:
        metrics = MonitoringService.get_database_metrics()
        return api_success(metrics)
    except Exception as e:
        logger.error(f"Erreur métriques BDD: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/admin/active-sessions", methods=["GET"])
@login_required
@admin_required
def v1_admin_active_sessions():
    """Sessions actives."""
    try:
        sessions = MonitoringService.get_active_sessions()
        return api_success({"sessions": sessions})
    except Exception as e:
        logger.error(f"Erreur sessions actives: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/admin/system-logs", methods=["GET"])
@login_required
@admin_required
def v1_admin_system_logs():
    """Logs système."""
    try:
        limit = request.args.get("limit", 100, type=int)
        level = request.args.get("level", None)
        logs = MonitoringService.get_application_logs(limit=limit, level=level)
        return api_success({"logs": logs})
    except Exception as e:
        logger.error(f"Erreur logs système: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/admin/alerts", methods=["GET"])
@login_required
@admin_required
def v1_admin_alerts():
    """Alertes système."""
    try:
        alerts = MonitoringService.get_alerts()
        return api_success({"alerts": alerts})
    except Exception as e:
        logger.error(f"Erreur alertes: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/admin/monitoring-summary", methods=["GET"])
@login_required
@admin_required
def v1_admin_monitoring_summary():
    """Résumé du monitoring."""
    try:
        summary = MonitoringService.get_dashboard_summary()
        return api_success(summary)
    except Exception as e:
        logger.error(f"Erreur résumé monitoring: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/admin/users", methods=["GET"])
@login_required
@admin_required
def v1_admin_list_users():
    """Liste tous les utilisateurs."""
    try:
        users = AdminService.get_all_users()
        return api_success({"users": users})
    except Exception as e:
        logger.error(f"Erreur liste utilisateurs: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/admin/users/<int:user_id>/activity", methods=["GET"])
@login_required
@admin_required
def v1_admin_user_activity(user_id):
    """Activité récente d'un utilisateur (connexions, transactions, notifications)."""
    try:
        limit = request.args.get("limit", 20, type=int)
        limit = max(1, min(limit, 50))
        activity = AdminService.get_user_activity(user_id, limit=limit)
        if activity is None:
            return api_error("Utilisateur non trouvé", 404)
        return api_success({"activity": activity})
    except Exception as e:
        logger.error(f"Erreur activité utilisateur: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/admin/users/<int:user_id>/accounts", methods=["GET"])
@login_required
@admin_required
def v1_admin_user_accounts(user_id):
    """Comptes d'un utilisateur (données minimisées, lecture seule)."""
    try:
        accounts = AdminService.get_user_accounts(user_id)
        if accounts is None:
            return api_error("Utilisateur non trouvé", 404)
        return api_success({"accounts": accounts})
    except Exception as e:
        logger.error(f"Erreur comptes utilisateur: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/admin/users/<int:user_id>/transactions", methods=["GET"])
@login_required
@admin_required
def v1_admin_user_transactions(user_id):
    """Transactions paginées d'un utilisateur (lecture seule)."""
    try:
        page = max(1, request.args.get("page", 1, type=int))
        per_page = request.args.get("per_page", 20, type=int)
        per_page = max(1, min(per_page, 100))
        result = AdminService.get_user_transactions(
            user_id, page=page, per_page=per_page
        )
        if result is None:
            return api_error("Utilisateur non trouvé", 404)
        items, total = result
        return api_paginated(items, total, page, per_page)
    except Exception as e:
        logger.error(f"Erreur transactions utilisateur: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
@auth_limiter.limit("10 per hour")
def v1_admin_toggle_user(user_id):
    """Active ou désactive un utilisateur."""
    try:
        success, message = AdminService.toggle_user_status(user_id)
        if not success:
            return api_error(message, 404)
        return api_success(message=message)
    except Exception as e:
        logger.error(f"Erreur toggle utilisateur: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/admin/users/<int:user_id>/reset-2fa", methods=["POST"])
@login_required
@admin_required
@auth_limiter.limit("10 per hour")
def v1_admin_reset_user_2fa(user_id):
    """Réinitialise la 2FA d'un utilisateur."""
    try:
        success, message, secret = AdminService.reset_user_2fa(user_id)
        if not success:
            return api_error(message, 404)
        return api_success(
            message="2FA réinitialisée. L'utilisateur devra reconfigurer sa 2FA."
        )
    except Exception as e:
        logger.error(f"Erreur reset 2FA: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
@login_required
@admin_required
@auth_limiter.limit("10 per hour")
def v1_admin_reset_user_password(user_id):
    """Réinitialise le mot de passe d'un utilisateur."""
    try:
        success, message, new_password = AdminService.reset_user_password(user_id)
        if not success:
            return api_error(message, 404)
        # Le mot de passe temporaire devrait etre envoye par email a l'utilisateur
        logger.info(f"Mot de passe reinitialise pour utilisateur {user_id}")
        return api_success(
            message="Mot de passe réinitialisé. L'utilisateur recevra un email avec les instructions."
        )
    except Exception as e:
        logger.error(f"Erreur reset mot de passe: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)
