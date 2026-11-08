"""
Module principal de l'application.

Ce module contient les routes et les vues principales de l'application.
Il est organisé selon l'architecture modulaire du projet avec séparation
claire entre présentation et logique métier.

Architecture :
- Routes web Flask : Interface utilisateur pour les pages principales
- Services métier : Importés depuis core/services/main/
- Gestion d'erreurs : Standardisée via backend.app.utils.errors
- Logging : Configuration appropriée pour le module

Fonctionnalités principales :
- Page d'accueil de l'application
- Informations système et statut
- Routes de base et navigation
"""

import logging

from flask import Blueprint

# Configuration du logger
logger = logging.getLogger(__name__)

# Import des éléments principaux pour faciliter l'accès
try:
    # Services métier - importés depuis le core
    # Gestion d'erreurs standardisée
    from app.utils.errors import (
        APIError,
        ConflictError,
        DatabaseError,
        NotFoundError,
        UnauthorizedError,
        ValidationError,
        handle_api_error,
        handle_conflict_error,
        handle_database_error,
        handle_not_found_error,
        handle_unauthorized_error,
        handle_validation_error,
    )
    from core.services.main import MainService, main_service

    logger.info("Module main initialisé avec succès")

except ImportError as e:
    logger.error(f"Erreur lors de l'import des dépendances du module main: {e}")
    raise

# Création du Blueprint principal
main_bp = Blueprint("main", __name__)

# Exports pour faciliter l'accès
__all__ = [
    "main_bp",
    "MainService",
    "main_service",
    "handle_validation_error",
    "handle_not_found_error",
    "handle_unauthorized_error",
    "handle_database_error",
    "handle_conflict_error",
    "handle_api_error",
]
