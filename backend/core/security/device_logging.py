"""
Module de sécurité des appareils pour la journalisation des événements de sécurité.
"""

import logging
from datetime import datetime, timezone

from ..extensions import db

logger = logging.getLogger(__name__)


def log_security_event(
    device_id, event_type, description, user_agent=None, ip_address=None, user_id=None
):
    """
    Journalise un événement de sécurité lié à un appareil.

    Args:
        device_id (int): ID de l'appareil concerné
        event_type (str): Type d'événement (ex: 'login_success', 'login_failed', 'device_blocked')
        description (str): Description détaillée de l'événement
        user_agent (str, optional): User-Agent du navigateur/application
        ip_address (str, optional): Adresse IP de la requête
        user_id (int, optional): ID de l'utilisateur concerné

    Returns:
        SecurityEvent: L'événement de sécurité créé
    """
    from .security_event import SecurityEvent  # Importation circulaire évitée

    event = SecurityEvent(
        device_id=device_id,
        event_type=event_type,
        description=description,
        user_agent=user_agent,
        ip_address=ip_address,
        user_id=user_id,
        timestamp=datetime.now(timezone.utc),
    )

    db.session.add(event)
    try:
        db.session.commit()
        return event
    except Exception as e:
        db.session.rollback()
        # Log l'erreur mais ne la propage pas pour ne pas interrompre le flux principal
        logger.error(
            f"Erreur lors de la journalisation de l'événement de sécurité: {e}"
        )
        return None
