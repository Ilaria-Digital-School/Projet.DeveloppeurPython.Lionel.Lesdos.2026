"""
Module principal du tableau de bord

Ce module fournit les services et les routes pour le tableau de bord de l'application.
Il est organisé en plusieurs services spécialisés :
- dashboard_main_service: Service principal qui agrège les données
- dashboard_transaction_service: Gestion des transactions
- dashboard_budget_service: Gestion des budgets
- dashboard_analytics_service: Analyses et statistiques
- dashboard_account_service: Gestion des comptes
"""

from flask import Blueprint
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import current_user

# Initialisation du cache
cache = Cache(config={"CACHE_TYPE": "flask_caching.backends.SimpleCache"})

# Initialisation du rate limiter (limites augmentées pour le développement)
limiter = Limiter(
    key_func=lambda: f"{current_user.id if hasattr(current_user, 'id') else 'anonymous'}",
    default_limits=["2000 per day", "500 per hour"],  # Limites plus hautes pour dev
)

# Création du blueprint
dashboard_bp = Blueprint("dashboard_bp", __name__, template_folder="templates")

from core.services.dashboard.dashboard_account_service import DashboardAccountService
from core.services.dashboard.dashboard_analytics_service import (
    DashboardAnalyticsService,
)
from core.services.dashboard.dashboard_budget_service import DashboardBudgetService

# Import des services principaux (imports relatifs corrigés)
from core.services.dashboard.dashboard_main_service import DashboardService
from core.services.dashboard.dashboard_transaction_service import (
    DashboardTransactionService,
)

# Export des services pour une utilisation externe
__all__ = [
    "DashboardService",
    "DashboardTransactionService",
    "DashboardBudgetService",
    "DashboardAnalyticsService",
    "DashboardAccountService",
]


def init_app(app):
    """
    Initialise l'application avec le module dashboard

    Args:
        app: L'application Flask

    Returns:
        L'application configurée
    """
    # Initialisation des extensions
    cache.init_app(app)
    limiter.init_app(app)

    # Enregistrement des routes
    from . import dashboard_routes

    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")

    # Import des modèles pour s'assurer qu'ils sont enregistrés avec SQLAlchemy
    # Les modèles dashboard sont dans core.models.dashboard

    return app
