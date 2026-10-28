"""
Services pour la gestion des appareils des utilisateurs.

Ce module fournit des services pour gérer les appareils des utilisateurs,
y compris l'enregistrement, la vérification et la gestion des sessions.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from itsdangerous import BadSignature, SignatureExpired
from sqlalchemy.exc import SQLAlchemyError

from core.extensions import db
from core.models.device import Device, DeviceLoginHistory
from modules.devices import get_token_serializer

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
    def verify_device(device_id: int, token: str) -> bool:
        """
        Vérifie un appareil avec le jeton fourni.

        Args:
            device_id: ID de l'appareil à vérifier
            token: Jeton de vérification

        Returns:
            bool: True si la vérification a réussi, False sinon
        """
        device = db.session.get(Device, device_id)
        if not device:
            logger.warning(
                "Tentative de vérification d'un appareil inexistant",
                extra={"device_id": device_id},
            )
            return False

        if device.verify_token(token):
            device.is_trusted = True
            device.verification_token = None
            device.verified_at = datetime.now(timezone.utc)

            db.session.commit()

            logger.info(
                "Appareil vérifié avec succès",
                extra={"device_id": device_id, "user_id": device.user_id},
            )
            return True

        logger.warning(
            "Échec de la vérification de l'appareil: jeton invalide",
            extra={"device_id": device_id, "user_id": device.user_id},
        )
        return False

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
    def update_device(
        device_id: int, user_id: int, update_data: Dict
    ) -> Optional[Device]:
        """
        Met à jour les informations d'un appareil.

        Args:
            device_id: ID de l'appareil à mettre à jour
            user_id: ID de l'utilisateur propriétaire
            update_data: Données à mettre à jour

        Returns:
            Optional[Device]: L'appareil mis à jour ou None si non trouvé
        """
        device = Device.query.filter_by(id=device_id, user_id=user_id).first()
        if not device:
            return None

        try:
            for key, value in update_data.items():
                if hasattr(device, key):
                    setattr(device, key, value)

            device.updated_at = datetime.now(timezone.utc)
            db.session.commit()

            logger.info(
                "Appareil mis à jour",
                extra={
                    "device_id": device_id,
                    "user_id": user_id,
                    "updated_fields": list(update_data.keys()),
                },
            )

            return device

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                "Erreur lors de la mise à jour de l'appareil",
                exc_info=True,
                extra={"device_id": device_id, "user_id": user_id, "error": str(e)},
            )
            raise

    @staticmethod
    def delete_device(device_id: int, user_id: int) -> bool:
        """
        Supprime un appareil.

        Args:
            device_id: ID de l'appareil à supprimer
            user_id: ID de l'utilisateur propriétaire

        Returns:
            bool: True si la suppression a réussi, False sinon
        """
        device = Device.query.filter_by(id=device_id, user_id=user_id).first()
        if not device:
            return False

        try:
            db.session.delete(device)
            db.session.commit()

            logger.info(
                "Appareil supprimé", extra={"device_id": device_id, "user_id": user_id}
            )

            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                "Erreur lors de la suppression de l'appareil",
                exc_info=True,
                extra={"device_id": device_id, "user_id": user_id, "error": str(e)},
            )
            raise

    @staticmethod
    def log_device_login(
        device_id: int,
        user_id: int,
        ip_address: str,
        user_agent: str = None,
        was_successful: bool = True,
        failure_reason: str = None,
        location: str = None,
        metadata: dict = None,
    ) -> DeviceLoginHistory:
        """
        Enregistre une tentative de connexion pour un appareil.

        Args:
            device_id: ID de l'appareil
            user_id: ID de l'utilisateur
            ip_address: Adresse IP de la tentative
            user_agent: User-Agent de la requête
            was_successful: Si la tentative a réussi
            failure_reason: Raison de l'échec (si échec)
            location: Localisation géographique
            metadata: Métadonnées supplémentaires

        Returns:
            DeviceLoginHistory: L'entrée d'historique créée
        """
        try:
            login_entry = DeviceLoginHistory(
                device_id=device_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                was_successful=was_successful,
                failure_reason=failure_reason,
                location=location,
                metadata=metadata or {},
            )

            db.session.add(login_entry)

            # Mettre à jour la date de dernière connexion de l'appareil
            device = db.session.get(Device, device_id)
            if device:
                device.last_seen = datetime.now(timezone.utc)

            db.session.commit()

            logger.info(
                "Tentative de connexion enregistrée",
                extra={
                    "device_id": device_id,
                    "user_id": user_id,
                    "was_successful": was_successful,
                    "ip_address": ip_address,
                },
            )

            return login_entry

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                "Erreur lors de l'enregistrement de la tentative de connexion",
                exc_info=True,
                extra={"device_id": device_id, "user_id": user_id, "error": str(e)},
            )
            raise

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

    @staticmethod
    def generate_device_token(device: Device) -> str:
        """
        Génère un jeton d'authentification pour un appareil.

        Args:
            device: L'appareil pour lequel générer le jeton

        Returns:
            str: Jeton d'authentification
        """
        if not device.is_trusted:
            logger.warning(
                "Tentative de génération de jeton pour un appareil non vérifié",
                extra={"device_id": device.id, "user_id": device.user_id},
            )
            raise ValueError("L'appareil doit être vérifié avant de générer un jeton")

        # Créer une charge utile pour le jeton
        payload = {
            "device_id": str(device.public_id),
            "user_id": str(device.user_id),
            "exp": datetime.now(timezone.utc)
            + timedelta(days=30),  # Expiration dans 30 jours
        }

        # Générer le jeton
        serializer = get_token_serializer()
        return serializer.dumps(payload)

    @staticmethod
    def verify_device_token(token: str) -> Optional[Device]:
        """
        Vérifie un jeton d'appareil et renvoie l'appareil correspondant.

        Args:
            token: Jeton à vérifier

        Returns:
            Optional[Device]: L'appareil si le jeton est valide, None sinon
        """
        if not token:
            return None

        serializer = get_token_serializer()

        try:
            # Vérifier et décoder le jeton
            payload = serializer.loads(
                token, max_age=30 * 24 * 3600  # 30 jours en secondes
            )

            # Récupérer l'appareil
            device = Device.query.filter_by(
                public_id=payload.get("device_id"),
                user_id=payload.get("user_id"),
                is_active=True,
                is_trusted=True,
            ).first()

            if device:
                # Mettre à jour la date de dernière activité
                device.last_seen = datetime.now(timezone.utc)
                db.session.commit()

                return device

        except (BadSignature, SignatureExpired) as e:
            logger.warning(
                "Échec de la vérification du jeton d'appareil",
                extra={"error": str(e), "token": token[:10] + "..." if token else None},
            )

        return None
