"""
Services pour la gestion des appareils des utilisateurs.

Ce module fournit des services pour gérer les appareils des utilisateurs,
y compris l'enregistrement, la vérification et la gestion des sessions.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from sqlalchemy.exc import SQLAlchemyError

from core.extensions import db
from core.models.device import Device, DeviceLoginHistory

# Configuration du logger
logger = logging.getLogger(__name__)


class DeviceService:
    """Service pour la gestion des appareils des utilisateurs."""

    @staticmethod
    def register_device(
        user_id: int, device_data: Dict, ip_address: str = None, user_agent: str = None
    ) -> Tuple[Device, str]:
        """
        Enregistre un nouvel appareil pour un utilisateur.

        Args:
            user_id: ID de l'utilisateur
            device_data: Données de l'appareil (nom, type, etc.)
            ip_address: Adresse IP de l'appareil
            user_agent: User-Agent de la requête

        Returns:
            Tuple[Device, str]: L'appareil créé et un jeton de vérification

        Raises:
            ValueError: Si les données de l'appareil sont invalides
            SQLAlchemyError: En cas d'erreur de base de données
        """
        try:
            # Validation des données requises
            required_fields = ["name", "device_id", "device_type"]
            for field in required_fields:
                if field not in device_data:
                    raise ValueError(f"Le champ '{field}' est requis")

            # Vérifier si l'appareil existe déjà pour cet utilisateur
            existing_device = Device.query.filter_by(
                user_id=user_id, device_id=device_data["device_id"]
            ).first()

            if existing_device:
                # Réactiver l'appareil s'il avait été révoqué
                if not existing_device.is_active:
                    existing_device.is_active = True
                    existing_device.revoked_at = None
                    db.session.commit()
                logger.info(
                    "Appareil existant mis à jour",
                    extra={
                        "user_id": user_id,
                        "device_id": existing_device.id,
                        "device_name": device_data["name"],
                    },
                )
                return existing_device, None

            # Créer un nouvel appareil
            device = Device(
                user_id=user_id,
                name=device_data["name"],
                device_id=device_data["device_id"],
                device_type=device_data["device_type"],
                os=device_data.get("os"),
                os_version=device_data.get("os_version"),
                browser=device_data.get("browser"),
                browser_version=device_data.get("browser_version"),
                ip_address=ip_address,
                user_agent=user_agent,
                is_trusted=False,
                last_used=datetime.now(timezone.utc),
            )

            # Générer un jeton de vérification
            token = device.generate_verification_token()

            db.session.add(device)
            db.session.commit()

            logger.info(
                "Nouvel appareil enregistré",
                extra={
                    "user_id": user_id,
                    "device_id": device.id,
                    "device_name": device.name,
                },
            )

            return device, token

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                "Erreur lors de l'enregistrement de l'appareil",
                exc_info=True,
                extra={"user_id": user_id, "error": str(e)},
            )
            raise

    @staticmethod
    def get_user_devices(user_id: int) -> List[Device]:
        """
        Récupère la liste des appareils d'un utilisateur.

        Args:
            user_id: ID de l'utilisateur

        Returns:
            List[Device]: Liste des appareils de l'utilisateur
        """
        return Device.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_device_login_history(
        user_id: int, device_id: int = None, limit: int = 50, offset: int = 0
    ) -> Tuple[List[DeviceLoginHistory], int]:
        """
        Récupère l'historique des connexions pour un utilisateur et éventuellement un appareil spécifique.

        Args:
            user_id: ID de l'utilisateur
            device_id: ID de l'appareil (optionnel)
            limit: Nombre maximum d'entrées à retourner
            offset: Décalage pour la pagination

        Returns:
            Tuple[List[DeviceLoginHistory], int]: Liste des entrées d'historique et nombre total
        """
        query = DeviceLoginHistory.query.filter_by(user_id=user_id)

        if device_id:
            query = query.filter_by(device_id=device_id)

        total = query.count()
        entries = (
            query.order_by(DeviceLoginHistory.login_time.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return entries, total
