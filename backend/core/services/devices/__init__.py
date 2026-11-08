"""
Services pour la gestion des appareils des utilisateurs.

Ce module centralise tous les services liés à la gestion des appareils,
y compris l'enregistrement, la vérification et la gestion des sessions.
"""

from .device_services import DeviceService

# Instance globale du service
_device_service = None


def get_device_service() -> DeviceService:
    """
    Retourne l'instance du service des appareils.

    Returns:
        DeviceService: Instance du service des appareils
    """
    global _device_service
    if _device_service is None:
        _device_service = DeviceService()
    return _device_service


# Exports publics
__all__ = ["DeviceService", "get_device_service"]
