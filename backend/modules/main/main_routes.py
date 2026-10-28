"""
Routes principales de l'application.

Ce module contient les routes web pour les pages principales de l'application.
Il utilise les services métier centralisés et suit les bonnes pratiques
d'architecture Flask avec gestion d'erreurs standardisée.
"""

import logging

from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required

# Import des services métier
from api.v1.auth import auth_limiter

# Import de la gestion d'erreurs standardisée
from app.utils.errors import (
    APIError,
    handle_api_error,
)
from core.services.main import main_service

# Configuration du logger
logger = logging.getLogger(__name__)

# Création du Blueprint
main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Route racine de l'application."""
    try:
        # Récupérer les données d'accueil via le service métier
        user_id = current_user.id if current_user.is_authenticated else None
        welcome_data = main_service.get_welcome_data(user_id)

        logger.info(f"Page d'accueil demandée par utilisateur {user_id or 'anonyme'}")

        # Afficher le template avec les données du service
        return render_template(
            "index.html",
            title=welcome_data.get("title", "Accueil"),
            message=welcome_data.get("message"),
            features=welcome_data.get("features", []),
            personalized=welcome_data.get("personalized", False),
        )

    except Exception as e:
        logger.error(f"Erreur dans la route d'accueil: {str(e)}")
        return handle_api_error(
            APIError(f"Erreur lors du chargement de la page d'accueil: {str(e)}")
        )


@main_bp.route("/healthz")
@auth_limiter.exempt
def healthz():
    """Sonde de santé pour Docker (healthcheck) et la supervision.

    Publique et minimale : vérifie que l'app répond et que la base est
    joignable, sans aucun détail (contrairement à /status, réservé aux
    utilisateurs connectés). Exemptée de la limite de requêtes.
    """
    from core.extensions import db

    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Healthcheck : base injoignable ({e})")
        return jsonify({"status": "error"}), 503


@main_bp.route("/status")
@login_required
def status():
    """Route de statut de l'application."""
    try:
        # Récupérer le statut via le service métier
        status_data = main_service.get_system_status()

        logger.debug("Statut système demandé")
        return jsonify(status_data), 200

    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {str(e)}")
        return handle_api_error(
            APIError(f"Erreur lors de la récupération du statut: {str(e)}")
        )


@main_bp.route("/info")
@login_required
def application_info():
    """Route d'informations sur l'application."""
    try:
        # Récupérer les informations via le service métier
        app_info = main_service.get_application_info()

        logger.debug("Informations de l'application demandées")
        return jsonify(app_info), 200

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des informations: {str(e)}")
        return handle_api_error(
            APIError(f"Erreur lors de la récupération des informations: {str(e)}")
        )
