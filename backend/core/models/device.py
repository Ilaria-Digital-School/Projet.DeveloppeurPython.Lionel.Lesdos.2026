"""
Modèles pour la gestion des appareils des utilisateurs.

Ce module définit les modèles pour le suivi des appareils et l'historique des connexions.
"""

import uuid
from datetime import datetime, timedelta, timezone

from flask import current_app, request
from itsdangerous import URLSafeTimedSerializer

from core.security.device_security import log_security_event

from ..extensions import db


# Configuration pour les jetons de sécurité
def get_token_serializer():
    """Retourne le sérialiseur de jetons configuré."""
    secret_key = current_app.config.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY non configurée. Impossible de générer des jetons de sécurité."
        )
    return URLSafeTimedSerializer(
        secret_key,
        salt=current_app.config.get(
            "SECURITY_PASSWORD_SALT", "device-verification-salt"
        ),
    )


class Device(db.Model):
    """
    Modèle représentant un appareil d'un utilisateur.

    Un appareil est un périphérique physique (téléphone, ordinateur, etc.)
    utilisé par un utilisateur pour accéder à l'application.
    """

    __tablename__ = "devices"

    # Identifiants
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
    )

    # Informations de base
    name = db.Column(db.String(100), nullable=False, index=True)
    device_id = db.Column(
        db.String(255), nullable=False, index=True
    )  # Identifiant unique de l'appareil

    # Informations techniques
    device_type = db.Column(
        db.String(50), nullable=False, index=True
    )  # mobile, tablet, desktop, etc.
    os = db.Column(db.String(50), index=True)  # Windows, iOS, Android, etc.
    os_version = db.Column(db.String(50))
    browser = db.Column(db.String(100), index=True)  # Chrome, Firefox, Safari, etc.
    browser_version = db.Column(db.String(50))

    # Informations réseau
    ip_address = db.Column(db.String(45))  # IPv6 peut faire jusqu'à 45 caractères
    user_agent = db.Column(db.Text)

    # Statut et sécurité
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_trusted = db.Column(
        db.Boolean, default=False, index=True
    )  # Si l'appareil est approuvé
    is_primary = db.Column(
        db.Boolean, default=False, index=True
    )  # Appareil principal de l'utilisateur

    # Authentification à deux facteurs
    two_factor_enabled = db.Column(db.Boolean, default=False, index=True)
    verification_token = db.Column(
        db.String(6), index=True
    )  # Code de vérification temporaire
    verification_token_expires = db.Column(db.DateTime, index=True)

    # Horodatages
    last_used = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )
    last_heartbeat = db.Column(db.DateTime, index=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )
    revoked_at = db.Column(db.DateTime, index=True, nullable=True)

    # Clé étrangère vers l'utilisateur
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user = db.relationship(
        "User",
        backref=db.backref("devices", lazy="dynamic", cascade="all, delete-orphan"),
    )

    # Relations
    login_history = db.relationship(
        "DeviceLoginHistory",
        backref="device",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="desc(DeviceLoginHistory.login_time)",
    )

    # Index composites pour les requêtes fréquentes
    __table_args__ = (
        db.Index("idx_device_user_active", "user_id", "is_active"),
        db.Index("idx_device_trusted", "user_id", "is_trusted"),
        db.Index("idx_device_user_heartbeat", "user_id", "last_heartbeat"),
    )

    def __init__(self, **kwargs):
        super(Device, self).__init__(**kwargs)
        # Générer un jeton de vérification pour les nouveaux appareils
        if not self.verification_token:
            self.generate_verification_token()

    def to_dict(self, include_sensitive=False):
        """
        Convertit l'objet en dictionnaire pour la sérialisation JSON.

        Args:
            include_sensitive (bool): Inclure les informations sensibles

        Returns:
            dict: Représentation sérialisable de l'appareil
        """
        data = {
            "id": self.public_id,
            "name": self.name,
            "device_type": self.device_type,
            "os": self.os,
            "os_version": self.os_version,
            "browser": self.browser,
            "browser_version": self.browser_version,
            "is_active": self.is_active,
            "is_trusted": self.is_trusted,
            "is_primary": self.is_primary,
            "two_factor_enabled": self.two_factor_enabled,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "last_heartbeat": (
                self.last_heartbeat.isoformat() if self.last_heartbeat else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "login_count": self.login_history.count(),
        }

        if include_sensitive:
            data.update(
                {
                    "device_id": self.device_id,
                    "ip_address": self.ip_address,
                    "user_agent": self.user_agent,
                    "verification_required": not self.is_trusted
                    and not self.two_factor_enabled,
                }
            )

        return data

    def generate_verification_token(self, expires_in=3600):
        """
        Génère un jeton de vérification pour l'appareil.

        Args:
            expires_in (int): Durée de validité en secondes (par défaut: 1h)

        Returns:
            str: Jeton de vérification
        """
        from core.security.device_security import generate_2fa_code

        self.verification_token = generate_2fa_code()
        self.verification_token_expires = datetime.now(timezone.utc) + timedelta(
            seconds=expires_in
        )
        return self.verification_token

    def verify_token(self, token):
        """
        Vérifie un jeton de vérification.

        Args:
            token (str): Jeton à vérifier

        Returns:
            bool: True si le jeton est valide, False sinon
        """
        from core.security.device_security import verify_2fa_code

        return verify_2fa_code(self, token)

    def log_login_attempt(
        self, ip_address=None, user_agent=None, was_successful=True, failure_reason=None
    ):
        """
        Enregistre une tentative de connexion pour cet appareil.

        Args:
            ip_address (str, optional): Adresse IP de la tentative
            user_agent (str, optional): User-Agent de la tentative
            was_successful (bool): Si la tentative a réussi
            failure_reason (str, optional): Raison de l'échec si applicable

        Returns:
            DeviceLoginHistory: L'entrée d'historique créée
        """
        from backend.utils.geoip import get_location_from_ip

        # Mettre à jour les informations de l'appareil
        self.last_used = datetime.now(timezone.utc)
        self.ip_address = ip_address or request.remote_addr if request else None

        # Créer une entrée d'historique
        login_entry = DeviceLoginHistory(
            device_id=self.id,
            user_id=self.user_id,
            ip_address=self.ip_address,
            user_agent=user_agent or (request.user_agent.string if request else None),
            was_successful=was_successful,
            failure_reason=failure_reason,
            location=get_location_from_ip(self.ip_address) if self.ip_address else None,
        )

        db.session.add(login_entry)
        db.session.commit()

        # Journaliser l'événement de sécurité
        log_security_event(
            user_id=self.user_id,
            event_type="login_attempt",
            ip_address=self.ip_address,
            device_id=self.id,
            was_successful=was_successful,
            failure_reason=failure_reason,
        )

        return login_entry

    def revoke(self):
        """Révoque l'accès de cet appareil."""
        self.is_active = False
        self.revoked_at = datetime.now(timezone.utc)

        # Journaliser l'événement de sécurité
        log_security_event(
            user_id=self.user_id,
            event_type="device_revoked",
            ip_address=request.remote_addr if request else None,
            device_id=self.id,
            details=f"Appareil révoqué: {self.name} ({self.device_type})",
        )

        db.session.commit()

    def __repr__(self):
        return f"<Device {self.public_id} - {self.name} ({self.device_type})>"


class DeviceLoginHistory(db.Model):
    """
    Historique des connexions pour un appareil.

    Cette table enregistre chaque tentative de connexion pour chaque appareil,
    y compris les tentatives échouées et les informations contextuelles.
    """

    __tablename__ = "device_login_history"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
    )

    # Références
    device_id = db.Column(
        db.Integer,
        db.ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Détails de la tentative
    login_time = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    ip_address = db.Column(db.String(45), index=True)
    user_agent = db.Column(db.Text)
    was_successful = db.Column(db.Boolean, default=True, index=True)
    failure_reason = db.Column(db.String(255), nullable=True)

    # Géolocalisation
    location = db.Column(db.String(255), nullable=True)  # Format: "Ville, Pays"
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    # Métadonnées
    device_metadata = db.Column(
        "metadata", db.JSON, nullable=True
    )  # Pour stocker des données supplémentaires

    # Clé étrangère vers l'utilisateur (redondante mais utile pour les requêtes)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Index pour les requêtes fréquentes
    __table_args__ = (
        db.Index("idx_login_history_user_time", "user_id", "login_time"),
        db.Index("idx_login_history_device_time", "device_id", "login_time"),
        db.Index(
            "idx_login_history_success", "user_id", "was_successful", "login_time"
        ),
    )

    def to_dict(self):
        """
        Convertit l'objet en dictionnaire pour la sérialisation JSON.

        Returns:
            dict: Représentation sérialisable de l'entrée d'historique
        """
        return {
            "id": self.public_id,
            "device_id": self.device.public_id if self.device else None,
            "login_time": self.login_time.isoformat() if self.login_time else None,
            "ip_address": self.ip_address,
            "location": self.location,
            "was_successful": self.was_successful,
            "failure_reason": self.failure_reason,
            "user_agent": self.user_agent,
            "metadata": self.device_metadata or {},
        }

    def to_audit_log(self):
        """
        Formatte les données pour un journal d'audit.

        Returns:
            dict: Données formatées pour le journal d'audit
        """
        from flask import request

        return {
            "timestamp": self.login_time.isoformat() if self.login_time else None,
            "event": "login_attempt",
            "status": "success" if self.was_successful else "failed",
            "device": {
                "id": self.device.public_id if self.device else None,
                "name": self.device.name if self.device else None,
                "type": self.device.device_type if self.device else None,
                "os": self.device.os if self.device else None,
                "browser": self.device.browser if self.device else None,
            },
            "ip_address": self.ip_address,
            "location": self.location,
            "user_agent": self.user_agent,
            "failure_reason": self.failure_reason,
            "request_id": request.headers.get("X-Request-ID") if request else None,
        }

    def __repr__(self):
        status = "success" if self.was_successful else "failed"
        return f"<DeviceLoginHistory {self.public_id} - {self.login_time} ({status})>"
