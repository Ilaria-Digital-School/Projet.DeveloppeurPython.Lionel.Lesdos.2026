"""
Routes pour la gestion des transactions récurrentes.
"""

import logging

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from core.models.account import Account
from core.models.category import Category
from core.services.recurring import RecurringTransactionService

logger = logging.getLogger(__name__)

recurring_bp = Blueprint("recurring", __name__, template_folder="templates")


@recurring_bp.route("/recurring")
@login_required
def recurring_page():
    """Page de gestion des transactions récurrentes."""
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    categories = (
        Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    )
    recurring_list = RecurringTransactionService.get_user_recurring(
        current_user.id, include_inactive=True
    )
    return render_template(
        "recurring_transactions.html",
        recurring_list=recurring_list,
        accounts=accounts,
        categories=categories,
    )
