"""
API REST v1 — Budgets.

Routes:
    GET    /api/v1/budgets              Liste des budgets (paginée)
    POST   /api/v1/budgets              Créer un budget
    GET    /api/v1/budgets/<id>         Détail d'un budget
    PUT    /api/v1/budgets/<id>         Modifier un budget
    DELETE /api/v1/budgets/<id>         Supprimer un budget
    GET    /api/v1/budgets/<id>/history Historique des modifications (paginé)
    GET    /api/v1/budgets/<id>/periods Prévu vs réel sur les dernières périodes
    GET    /api/v1/budgets/alerts       Alertes budgétaires
    GET    /api/v1/budgets/summary      Résumé des budgets (widget dashboard)
    GET    /api/v1/budgets/export       Exporter les budgets
    GET    /api/v1/budgets/threshold    Récupérer le seuil d'alerte par défaut
    POST   /api/v1/budgets/threshold    Sauvegarder le seuil d'alerte par défaut
"""

import json
import logging

from flask import Response, request
from flask_login import current_user, login_required

from core.extensions import db
from core.models.budget import Budget
from core.services.budgets.budget_services import (
    create_budget,
    delete_budget,
    export_budgets,
    get_budget_by_id,
    get_budget_history,
    get_user_budgets_with_expenses,
    update_budget,
)

from . import api_v1_bp
from .auth import auth_limiter
from .helpers import api_error, api_success

logger = logging.getLogger(__name__)


# ── LIST / CREATE ────────────────────────────────────────────────────────────


@api_v1_bp.route("/budgets", methods=["GET"])
@login_required
def v1_list_budgets():
    """Liste tous les budgets de l'utilisateur."""
    try:
        user_id = current_user.id
        page = int(request.args.get("page", 1))
        per_page = min(max(int(request.args.get("per_page", 10)), 1), 100)

        # Utiliser le service existant
        result = get_user_budgets_with_expenses(user_id, page, per_page)

        return api_success(
            {
                "budgets": result["items"],
                "pagination": {
                    "current_page": result["current_page"],
                    "total_pages": result["pages"],
                    "total_items": result["total"],
                    "per_page": result["per_page"],
                },
            }
        )

    except Exception as e:
        logger.error(f"Erreur liste budgets: {str(e)}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/budgets", methods=["POST"])
@login_required
@auth_limiter.limit("20 per minute")
def v1_create_budget():
    """Cree un nouveau budget."""
    try:
        user_id = current_user.id
        data = request.get_json()

        if not data:
            return api_error("Donnees manquantes", 400)

        # Utiliser le service existant
        success, result, status_code = create_budget(
            user_id, form_data=data, ip_address=request.remote_addr
        )

        if success:
            return api_success(
                {
                    "budget": {
                        "id": result.id,
                        "amount": float(result.amount),
                        "category_id": result.category_id,
                        "period": result.period,
                    }
                },
                message="Budget cree avec succes",
                status_code=status_code,
            )
        else:
            return api_error(result, status_code)

    except Exception as e:
        logger.error(f"Erreur creation budget: {str(e)}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


# ── DETAIL / UPDATE / DELETE ─────────────────────────────────────────────────


@api_v1_bp.route("/budgets/<int:budget_id>", methods=["GET"])
@login_required
def v1_get_budget(budget_id):
    """Recupere un budget specifique."""
    try:
        user_id = current_user.id
        budget = get_budget_by_id(budget_id, user_id)

        if not budget:
            return api_error("Budget non trouve", 404)

        return api_success(
            {
                "budget": {
                    **budget.indicateurs(),
                    "id": budget.id,
                    "name": budget.category.name if budget.category else None,
                    "category_name": budget.category.name if budget.category else None,
                    "amount": float(budget.amount),
                    "category_id": budget.category_id,
                    "period": budget.period,
                    "start_date": (
                        budget.start_date.isoformat() if budget.start_date else None
                    ),
                    "end_date": (
                        budget.end_date.isoformat() if budget.end_date else None
                    ),
                    "notification_threshold": budget.notification_threshold,
                    "report_actif": bool(budget.report_actif),
                }
            }
        )

    except Exception as e:
        logger.error(f"Erreur recuperation budget: {str(e)}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/budgets/<int:budget_id>", methods=["PUT"])
@login_required
def v1_update_budget(budget_id):
    """Met a jour un budget."""
    try:
        user_id = current_user.id
        data = request.get_json()

        if not data:
            return api_error("Donnees manquantes", 400)

        # Utiliser le service existant
        success, result, status_code = update_budget(
            budget_id, user_id, form_data=data, ip_address=request.remote_addr
        )

        if success:
            return api_success(
                {
                    "budget": {
                        "id": result.id,
                        "name": result.category.name if result.category else None,
                        "amount": float(result.amount),
                        "category_id": result.category_id,
                    }
                },
                message="Budget mis a jour avec succes",
                status_code=status_code,
            )
        else:
            return api_error(result, status_code)

    except Exception as e:
        logger.error(f"Erreur mise a jour budget: {str(e)}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/budgets/<int:budget_id>", methods=["DELETE"])
@login_required
def v1_delete_budget(budget_id):
    """Supprime un budget."""
    try:
        user_id = current_user.id
        logger.info(f"DELETE budget: budget_id={budget_id}, user_id={user_id}")

        # Utiliser le service existant
        success, message, status_code = delete_budget(
            budget_id, user_id, ip_address=request.remote_addr
        )

        if success:
            return api_success(message=message)
        else:
            return api_error(message, status_code)

    except Exception as e:
        logger.error(f"Erreur suppression budget: {str(e)}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


# ── HISTORY / PERIODS ────────────────────────────────────────────────────────


@api_v1_bp.route("/budgets/<int:budget_id>/history", methods=["GET"])
@login_required
def v1_budget_history(budget_id):
    """Historique des modifications d'un budget (le plus récent en premier)."""
    try:
        if not get_budget_by_id(budget_id, current_user.id):
            return api_error("Budget non trouve", 404)
        page = max(request.args.get("page", 1, type=int), 1)
        per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)
        entries, total, pages = get_budget_history(
            budget_id, current_user.id, page, per_page
        )
        return api_success(
            {
                "history": entries,
                "pagination": {
                    "current_page": page,
                    "total_pages": pages,
                    "total_items": total,
                    "per_page": per_page,
                },
            }
        )
    except Exception as e:
        logger.error(f"Erreur historique budget: {str(e)}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/budgets/<int:budget_id>/periods", methods=["GET"])
@login_required
def v1_budget_periods(budget_id):
    """Prévu vs réel sur les N dernières périodes (6 par défaut, 24 max)."""
    try:
        budget = get_budget_by_id(budget_id, current_user.id)
        if not budget:
            return api_error("Budget non trouve", 404)
        count = min(max(request.args.get("count", 6, type=int), 1), 24)
        return api_success(
            {
                "budget_id": budget.id,
                "period": budget.period,
                "periods": budget.historique_periodes(count),
            }
        )
    except Exception as e:
        logger.error(f"Erreur periodes budget: {str(e)}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


# ── ALERTS ───────────────────────────────────────────────────────────────────


@api_v1_bp.route("/budgets/alerts", methods=["GET"])
@login_required
def v1_budget_alerts():
    """Recupere les alertes budgetaires stockees en base."""
    try:
        user_id = current_user.id

        # Recuperer les notifications d'alertes budgetaires non lues
        from core.models.notification import Notification

        notifications = (
            db.session.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.notification_type == "budget_alert",
                Notification.is_read == False,
            )
            .order_by(Notification.created_at.desc())
            .all()
        )

        alerts = []
        for notif in notifications:
            try:
                # Parser les metadonnees pour recuperer les infos du budget
                metadata = json.loads(notif.metadata) if notif.metadata else {}

                # Recuperer le nom de la categorie si disponible
                category_name = metadata.get("budget_name", "Budget")
                if "budget_id" in metadata and not category_name:
                    budget = db.session.get(Budget, metadata["budget_id"])
                    if budget and budget.category:
                        category_name = budget.category.name

                alerts.append(
                    {
                        "id": notif.id,
                        "category_name": category_name,
                        "message": notif.message,
                        "created_at": notif.created_at.isoformat(),
                        "percentage": metadata.get("percentage", 0),
                        "current_amount": metadata.get("current_amount", 0),
                        "budget_limit": metadata.get("budget_limit", 0),
                        "threshold": metadata.get("threshold", 90),
                    }
                )
            except Exception as e:
                logger.warning(f"Erreur parsing notification {notif.id}: {e}")
                # Fallback - utiliser les donnees de base
                alerts.append(
                    {
                        "id": notif.id,
                        "category_name": "Budget",
                        "message": notif.message,
                        "created_at": notif.created_at.isoformat(),
                    }
                )

        return api_success({"alerts": alerts})

    except Exception as e:
        logger.error(f"Erreur alertes budget: {str(e)}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


# ── SUMMARY ──────────────────────────────────────────────────────────────────


@api_v1_bp.route("/budgets/summary", methods=["GET"])
@login_required
def v1_budget_summary():
    """Recupere le resume des budgets pour le widget dashboard."""
    try:
        user_id = current_user.id

        # Recuperer TOUS les budgets (per_page eleve)
        result = get_user_budgets_with_expenses(user_id, page=1, per_page=100)
        budgets = result["items"]

        # Calculer les statistiques globales
        # Les indicateurs (jours, rythme, projection...) sont calculés par
        # Budget.indicateurs ; seuls les budgets actifs comptent dans le total
        actifs = [b for b in budgets if b["active"]]
        total_budget = sum(b["available_amount"] for b in actifs)
        total_spent = sum(b["spent_amount"] for b in actifs)
        total_projected = sum(b["projected_amount"] for b in actifs)
        critical_budgets = [b for b in actifs if b["spent_percentage"] >= 90]

        return api_success(
            {
                "summary": {
                    "total_budgets": len(actifs),
                    "total_budget_amount": total_budget,
                    "total_spent": total_spent,
                    "total_remaining": total_budget - total_spent,
                    "total_projected": total_projected,
                    "critical_count": len(critical_budgets),
                },
                "budgets": budgets,
                "critical_budgets": critical_budgets,
            }
        )

    except Exception as e:
        logger.error(f"Erreur resume budget: {str(e)}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


# ── EXPORT ───────────────────────────────────────────────────────────────────


@api_v1_bp.route("/budgets/export", methods=["GET"])
@login_required
def v1_budget_export():
    """Exporte les budgets."""
    try:
        user_id = current_user.id
        format_type = request.args.get("format", "csv")

        # Utiliser le service existant
        data, filename, mime_type = export_budgets(user_id, format_type)

        return Response(
            data,
            mimetype=mime_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        logger.error(f"Erreur export budget: {str(e)}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


# ── THRESHOLD ────────────────────────────────────────────────────────────────


@api_v1_bp.route("/budgets/threshold", methods=["GET"])
@login_required
def v1_get_budget_threshold():
    """Recupere le seuil d'alerte par defaut."""
    try:
        user_id = current_user.id

        # Recuperer le seuil par defaut des budgets existants
        from sqlalchemy import func

        # Prendre le seuil le plus commun dans les budgets de l'utilisateur
        common_threshold = (
            db.session.query(
                Budget.notification_threshold,
                func.count(Budget.notification_threshold).label("count"),
            )
            .filter(
                Budget.user_id == user_id, Budget.notification_threshold.isnot(None)
            )
            .group_by(Budget.notification_threshold)
            .order_by(func.count(Budget.notification_threshold).desc())
            .first()
        )

        threshold = common_threshold[0] if common_threshold else 90

        return api_success({"default_threshold": threshold})

    except Exception as e:
        logger.error(f"Erreur recuperation seuil: {str(e)}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/budgets/threshold", methods=["POST"])
@login_required
def v1_save_budget_threshold():
    """Sauvegarde le seuil d'alerte par defaut."""
    try:
        data = request.get_json()

        if not data or "default_threshold" not in data:
            return api_error("Seuil d'alerte requis", 400)

        threshold = data["default_threshold"]

        # Valider le seuil (entre 1 et 100)
        if not isinstance(threshold, int) or threshold < 1 or threshold > 100:
            return api_error("Le seuil doit etre un entier entre 1 et 100", 400)

        user_id = current_user.id

        from core.models.user import User

        user = db.session.get(User, user_id)
        if not user:
            return api_error("Utilisateur non trouve", 404)

        logger.info(
            f"Seuil par defaut sauvegarde: {threshold}% pour utilisateur {user_id}"
        )

        # Option: Mettre a jour tous les budgets existants avec le nouveau seuil
        update_existing = data.get("update_existing", True)

        if update_existing:
            # Mettre a jour TOUS les budgets de l'utilisateur
            budgets_updated = Budget.query.filter(Budget.user_id == user_id).update(
                {"notification_threshold": threshold}
            )
            message_detail = "tous les budgets existants mis a jour"
        else:
            # Mettre a jour seulement les budgets sans seuil defini
            budgets_updated = Budget.query.filter(
                Budget.user_id == user_id, Budget.notification_threshold.is_(None)
            ).update({"notification_threshold": threshold})
            message_detail = "nouveaux budgets uniquement"

        db.session.commit()

        return api_success(
            {
                "budgets_updated": budgets_updated,
                "threshold": threshold,
                "update_existing": update_existing,
            },
            message=f"Seuil par defaut sauvegarde a {threshold}% ({message_detail})",
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur sauvegarde seuil: {str(e)}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)
