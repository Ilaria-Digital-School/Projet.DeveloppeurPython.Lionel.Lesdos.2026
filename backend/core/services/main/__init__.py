"""
Services pour le module principal de l'application.

Ce package contient les services métier pour les fonctionnalités principales
de l'application comme la page d'accueil et les informations système.
"""

from .main_services import MainService, main_service

# Exports pour faciliter l'accès
__all__ = ["MainService", "main_service"]
