"""
Module web des budgets : page de suivi (projection, report du reste,
prévu vs réel). Les données passent par l'API REST v1 (/api/v1/budgets).
"""

from flask import Blueprint

budgets_bp = Blueprint("budgets", __name__)

from . import budget_routes  # noqa: E402,F401
