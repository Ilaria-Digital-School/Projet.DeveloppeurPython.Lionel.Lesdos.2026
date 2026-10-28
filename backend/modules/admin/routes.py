"""
Routes du module d'administration
Gère les endpoints liés à l'administration du système
"""

import logging

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from core.decorators import admin_required
from core.services.admin.admin_services import AdminService
from core.services.admin.monitoring_service import MonitoringService

logger = logging.getLogger(__name__)

bp = Blueprint("admin", __name__, url_prefix="/admin")

# ==================== ROUTES WEB ====================


@bp.route("/")
@login_required
@admin_required
def admin_root():
    """Redirection de /admin/ vers /admin/dashboard"""
    return redirect(url_for("admin.dashboard"))


@bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    """Dashboard principal d'administration avec métriques système"""
    try:
        # Métriques existantes
        stats = AdminService.get_dashboard_stats()
        financial_summary = AdminService.get_financial_summary()

        # Nouvelles métriques système
        system_summary = MonitoringService.get_dashboard_summary()

        return render_template(
            "admin/dashboard.html",
            stats=stats,
            financial_summary=financial_summary,
            system_summary=system_summary,
        )
    except Exception as e:
        flash(f"Erreur lors du chargement du dashboard: {str(e)}", "error")
        return render_template(
            "admin/dashboard.html", stats={}, financial_summary={}, system_summary={}
        )


@bp.route("/users-management")
@login_required
@admin_required
def users_management():
    """Page de gestion des utilisateurs avec sessions actives"""
    try:
        # Log pour debug
        current_app.logger.info(
            f"🚀 Route /admin/users-management appelée par {current_user.username}"
        )

        # Récupérer les utilisateurs
        users = AdminService.get_all_users()

        # Sessions actives et logs d'authentification
        sessions = MonitoringService.get_active_sessions()
        auth_logs = MonitoringService.get_application_logs(limit=50, level="AUTH")

        # Log du résultat
        current_app.logger.info(
            f"📋 Retour du service: {len(users)} utilisateurs, {sessions.get('active_users', 0)} actifs"
        )

        return render_template(
            "admin/users.html", users=users, sessions=sessions, auth_logs=auth_logs
        )
    except Exception as e:
        current_app.logger.error(
            f"❌ Erreur lors du chargement des utilisateurs: {str(e)}"
        )
        flash(f"Erreur lors du chargement des utilisateurs: {str(e)}", "error")
        return render_template("admin/users.html", users=[], sessions={}, auth_logs=[])


@bp.route("/user/<int:user_id>")
@login_required
@admin_required
def user_details(user_id):
    """Détails d'un utilisateur"""
    user_details = AdminService.get_user_details(user_id)
    if not user_details:
        flash("Utilisateur non trouvé", "error")
        return redirect(url_for("admin.users_management"))

    return render_template("admin/user_details.html", user=user_details)


@bp.route("/monitoring")
@login_required
@admin_required
def monitoring():
    """Page de monitoring technique approfondi"""
    empty_metrics = {
        "cpu": {"percent": 0, "count": 0, "per_core": [], "load_average": [0, 0, 0]},
        "memory": {
            "total": 0,
            "available": 0,
            "percent": 0,
            "used": 0,
            "free": 0,
            "cached": 0,
            "buffers": 0,
        },
        "swap": {"total": 0, "used": 0, "free": 0, "percent": 0},
        "disk": {
            "total": 0,
            "used": 0,
            "free": 0,
            "percent": 0,
            "read_bytes": 0,
            "write_bytes": 0,
            "read_count": 0,
            "write_count": 0,
        },
        "network": {
            "bytes_sent": 0,
            "bytes_recv": 0,
            "packets_sent": 0,
            "packets_recv": 0,
            "errin": 0,
            "errout": 0,
            "dropin": 0,
            "dropout": 0,
        },
        "process": {"count": 0},
        "uptime": {
            "boot_time": "",
            "days": 0,
            "hours": 0,
            "minutes": 0,
            "total_seconds": 0,
        },
    }

    try:
        system_metrics = MonitoringService.get_system_metrics() or empty_metrics
    except Exception as e:
        logger.error(f"Erreur system_metrics: {e}", exc_info=True)
        system_metrics = empty_metrics

    # Garantir que toutes les clés attendues existent
    for key in empty_metrics:
        if key not in system_metrics:
            system_metrics[key] = empty_metrics[key]

    try:
        database_metrics = MonitoringService.get_database_metrics()
    except Exception as e:
        logger.error(f"Erreur database_metrics: {e}", exc_info=True)
        database_metrics = {}

    try:
        api_metrics = MonitoringService.get_api_metrics()
    except Exception as e:
        logger.error(f"Erreur api_metrics: {e}", exc_info=True)
        api_metrics = {}

    try:
        system_logs = MonitoringService.get_application_logs(limit=100)
    except Exception as e:
        logger.error(f"Erreur system_logs: {e}", exc_info=True)
        system_logs = []

    try:
        error_logs = MonitoringService.get_application_logs(limit=50, level="ERROR")
    except Exception as e:
        logger.error(f"Erreur error_logs: {e}", exc_info=True)
        error_logs = []

    try:
        alerts = MonitoringService.get_alerts()
    except Exception as e:
        logger.error(f"Erreur alerts: {e}", exc_info=True)
        alerts = []

    return render_template(
        "admin/monitoring.html",
        system_metrics=system_metrics,
        database_metrics=database_metrics,
        api_metrics=api_metrics,
        system_logs=system_logs,
        error_logs=error_logs,
        alerts=alerts,
    )
