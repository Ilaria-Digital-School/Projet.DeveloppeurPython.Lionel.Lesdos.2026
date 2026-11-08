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

# Une erreur dans un module arrête le démarrage : sinon ses routes
# disparaissaient en silence (404) avec un simple avertissement dans les logs
for _mod in _modules:
    __import__(f"{__name__}.{_mod}")
