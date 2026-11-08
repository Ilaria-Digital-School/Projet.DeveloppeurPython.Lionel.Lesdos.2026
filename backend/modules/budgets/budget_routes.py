"""Routes web du module budgets (HTML uniquement, l'API est dans api/v1)."""

from flask import render_template
from flask_login import login_required

from . import budgets_bp


@budgets_bp.route("/")
@login_required
def budgets_page():
    """Page de suivi des budgets."""
    return render_template("budgets.html")
