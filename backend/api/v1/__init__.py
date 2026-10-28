"""
API REST v1 Blueprint.

Toutes les routes API sont regroupées sous le préfixe /api/v1/.
"""

import logging

from flask import Blueprint

logger = logging.getLogger(__name__)

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Import des modules de routes API (chaque import est protégé pour ne pas bloquer les autres)
_modules = [
    "categories",
    "accounts",
    "transactions",
    "budgets",
    "dashboard",
    "recurring",
    "reports",
    "auth",
    "profile",
    "admin",
    "users",
    "settings",
    "notifications",
    "devices",
    "openapi",
]

for _mod in _modules:
    try:
        __import__(f"{__name__}.{_mod}")
    except ImportError as e:
        logger.warning(f"Impossible de charger le module API v1 '{_mod}': {e}")
    except Exception as e:
        logger.error(
            f"Erreur lors du chargement du module API v1 '{_mod}': {e}", exc_info=True
        )
