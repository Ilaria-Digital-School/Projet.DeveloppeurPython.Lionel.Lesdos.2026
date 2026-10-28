"""
Module de gestion des appareils pour l'application.

Ce package fournit des fonctionnalités pour gérer les appareils des utilisateurs,
y compris l'enregistrement, la vérification et le suivi des connexions.
"""

import logging
import os

from flask import current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from itsdangerous import URLSafeTimedSerializer

# Configuration du rate limiter (limites développement)
device_limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["2000 per day", "500 per hour"],  # Limites plus hautes pour dev
    storage_uri="memory://",
)


# Configuration du sérialiseur de jetons
def get_token_serializer():
    """Retourne une instance de URLSafeTimedSerializer configurée."""
    secret_key = current_app.config.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY non configurée. Impossible de générer des jetons de sécurité."
        )
    return URLSafeTimedSerializer(secret_key, salt="device-verification-salt")


# Configuration du logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Création du formateur
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Création du gestionnaire pour la console
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def init_app(app):
    """
    Initialise le module des appareils avec l'application Flask.

    Args:
        app: Instance de l'application Flask
    """
    # Configuration du logger
    global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Suppression des gestionnaires existants pour éviter les doublons
    if logger.hasHandlers():
        logger.handlers.clear()

    # Ajout du gestionnaire de console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Ajout du gestionnaire de fichier
    log_file = os.path.join(app.root_path, "logs", "devices.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Initialisation du rate limiter
    device_limiter.init_app(app)

    logger.info("Module de gestion des appareils initialisé avec succès")
    return app


# Export des éléments principaux
__all__ = ["device_limiter", "get_token_serializer", "init_app", "logger"]
