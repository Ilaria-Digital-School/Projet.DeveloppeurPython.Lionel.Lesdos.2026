"""
Services métier pour le module principal de l'application.

Ce module contient les services pour gérer les fonctionnalités principales
comme la page d'accueil, les informations système et les statistiques générales.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from flask import current_app

logger = logging.getLogger(__name__)


class MainService:
    """Service principal pour les fonctionnalités de base de l'application."""

    def __init__(self):
        """Initialise le service principal."""
        self.logger = logger

    def get_welcome_data(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Récupère les données d'accueil pour l'utilisateur.

        Args:
            user_id: ID de l'utilisateur connecté (optionnel)

        Returns:
            Dict contenant les données d'accueil
        """
        try:
            welcome_data = {
                "title": "Bienvenue sur votre application de gestion budgétaire",
                "message": "Gérez vos finances personnelles en toute simplicité",
                "timestamp": datetime.now().isoformat(),
                "features": [
                    "Gestion des comptes bancaires",
                    "Suivi des transactions",
                    "Budgets personnalisés",
                    "Rapports détaillés",
                    "Catégorisation automatique",
                ],
            }

            if user_id:
                # Ajouter des données personnalisées pour l'utilisateur connecté
                welcome_data["personalized"] = True
                welcome_data["user_id"] = user_id
            else:
                welcome_data["personalized"] = False

            self.logger.info(
                f"Données d'accueil générées pour utilisateur {user_id or 'anonyme'}"
            )
            return welcome_data

        except Exception as e:
            self.logger.error(
                f"Erreur lors de la génération des données d'accueil: {str(e)}"
            )
            raise

    def get_system_status(self) -> Dict[str, Any]:
        """
        Récupère le statut du système.

        Returns:
            Dict contenant les informations de statut
        """
        try:
            status_data = {
                "status": "running",
                "environment": current_app.config.get(
                    "FLASK_ENV", os.environ.get("FLASK_ENV", "production")
                ),
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
                "database": "connected",
                "services": {"auth": "active", "api": "active", "web": "active"},
            }

            self.logger.debug("Statut système récupéré avec succès")
            return status_data

        except Exception as e:
            self.logger.error(
                f"Erreur lors de la récupération du statut système: {str(e)}"
            )
            raise

    def get_application_info(self) -> Dict[str, Any]:
        """
        Récupère les informations générales de l'application.

        Returns:
            Dict contenant les informations de l'application
        """
        try:
            app_info = {
                "name": "Appli Web Budget",
                "description": "Application de gestion budgétaire personnelle",
                "version": "1.0.0",
                "author": "Équipe de développement",
                "license": "MIT",
                "technologies": [
                    "Flask",
                    "SQLAlchemy",
                    "Flask-RESTx",
                    "JWT",
                    "Bootstrap",
                ],
                "features_count": 5,
                "last_updated": datetime.now().isoformat(),
            }

            self.logger.debug("Informations de l'application récupérées")
            return app_info

        except Exception as e:
            self.logger.error(
                f"Erreur lors de la récupération des informations de l'application: {str(e)}"
            )
            raise


# Instance unique du service principal
main_service = MainService()
