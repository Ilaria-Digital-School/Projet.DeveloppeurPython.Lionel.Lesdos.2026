"""
Services pour la gestion des notifications.

Ce package contient tous les services métier liés à la gestion des notifications,
incluant l'envoi, la réception, les préférences et les gestionnaires d'événements.
"""

# Import du service principal
from .notification_service import NotificationService

# Exports pour faciliter l'accès
__all__ = ["NotificationService"]
