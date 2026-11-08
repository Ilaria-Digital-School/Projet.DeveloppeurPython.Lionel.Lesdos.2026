"""
API REST v1 — Transactions récurrentes.

Routes:
    GET    /api/v1/recurring              Liste des récurrences
    POST   /api/v1/recurring              Créer une récurrence
    GET    /api/v1/recurring/<id>         Détail d'une récurrence
    PUT    /api/v1/recurring/<id>         Modifier une récurrence
    DELETE /api/v1/recurring/<id>         Supprimer une récurrence
    POST   /api/v1/recurring/<id>/pause   Basculer pause/actif
"""

from flask import request
from flask_login import current_user, login_required

from core.services.recurring import RecurringTransactionService

from . import api_v1_bp
from .helpers import api_error, api_success


@api_v1_bp.route("/recurring", methods=["GET"])
@login_required
def list_recurring():
    """Liste des transactions récurrentes."""
    include_inactive = request.args.get("include_inactive", "false").lower() == "true"
    recurring_list = RecurringTransactionService.get_user_recurring(
        current_user.id, include_inactive=include_inactive
    )
    return api_success({"recurring": [r.to_dict() for r in recurring_list]})


@api_v1_bp.route("/recurring", methods=["POST"])
@login_required
def create_recurring():
    """Crée une nouvelle transaction récurrente."""
    data = request.get_json()
    if not data:
        return api_error("Données manquantes", 400)

    success, result, status_code = RecurringTransactionService.create_recurring(
        current_user.id, data
    )
    if success:
        return api_success({"recurring": result.to_dict()}, status_code=status_code)
    return api_error(result, status_code)


@api_v1_bp.route("/recurring/<int:recurring_id>", methods=["GET"])
@login_required
def get_recurring(recurring_id):
    """Récupère les détails d'une transaction récurrente."""
    recurring = RecurringTransactionService.get_recurring_by_id(
        recurring_id, current_user.id
    )
    if not recurring:
        return api_error("Transaction récurrente non trouvée", 404)
    return api_success({"recurring": recurring.to_dict()})


@api_v1_bp.route("/recurring/<int:recurring_id>", methods=["PUT"])
@login_required
def update_recurring(recurring_id):
    """Met à jour une transaction récurrente."""
    data = request.get_json()
    if not data:
        return api_error("Données manquantes", 400)

    success, result, status_code = RecurringTransactionService.update_recurring(
        recurring_id, current_user.id, data
    )
    if success:
        return api_success({"recurring": result.to_dict()}, status_code=status_code)
    return api_error(result, status_code)


@api_v1_bp.route("/recurring/<int:recurring_id>", methods=["DELETE"])
@login_required
def delete_recurring(recurring_id):
    """Supprime une transaction récurrente."""
    success, message, status_code = RecurringTransactionService.delete_recurring(
        recurring_id, current_user.id
    )
    if success:
        return api_success(message=message)
    return api_error(message, status_code)


@api_v1_bp.route("/recurring/<int:recurring_id>/pause", methods=["POST"])
@login_required
def toggle_pause_recurring(recurring_id):
    """Met en pause ou reprend une transaction récurrente."""
    recurring = RecurringTransactionService.get_recurring_by_id(
        recurring_id, current_user.id
    )
    if not recurring:
        return api_error("Transaction récurrente non trouvée", 404)

    if recurring.is_active:
        success, message, status_code = RecurringTransactionService.pause_recurring(
            recurring_id, current_user.id
        )
    else:
        success, message, status_code = RecurringTransactionService.resume_recurring(
            recurring_id, current_user.id
        )

    if success:
        return api_success(message=message)
    return api_error(message, status_code)
