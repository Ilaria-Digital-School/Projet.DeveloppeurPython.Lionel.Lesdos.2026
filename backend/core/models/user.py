"""
Modèle utilisateur principal.

Ce module contient la définition complète du modèle utilisateur avec toutes les fonctionnalités
d'authentification, d'autorisation et de profil utilisateur.
"""

from datetime import datetime, timezone

from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash

from ..extensions import db
from .associations import user_roles  # noqa: F401  (enregistre la table d'association)
from .notification import Notification  # Import direct pour la relation
from .notification_preference import (  # Import direct pour la relation
    NotificationPreference,
)
from .report import Report  # Import direct pour la relation


class User(UserMixin, db.Model):
    """
    Modèle utilisateur principal.

    Gère l'authentification, l'autorisation et les informations de profil des utilisateurs.
    """

    __tablename__ = "users"
    # Informations de base
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)

    # Informations personnelles
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    language = db.Column(db.String(10), default="fr_FR", nullable=True)
    timezone = db.Column(db.String(50), default="Europe/Paris", nullable=True)
    avatar_url = db.Column(
        db.String(255), nullable=True
    )  # Chemin vers la photo de profil

    # État du compte
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_locked = db.Column(db.Boolean, default=False)
    login_attempts = db.Column(db.Integer, default=0)
    deactivated_at = db.Column(db.DateTime, nullable=True)
    deactivation_reason = db.Column(db.String(255), nullable=True)
    # Suppression demandée par l'utilisateur : purge définitive à cette date
    # (core/services/user/account_deletion.py) ; annulée s'il se reconnecte avant
    deletion_scheduled_at = db.Column(db.DateTime, nullable=True)

    # Vérification en deux étapes (2FA)
    two_factor_enabled = db.Column(db.Boolean, default=False, nullable=False)
    two_factor_secret = db.Column(
        db.String(32), nullable=True
    )  # Secret TOTP uniquement
    two_factor_backup_codes = db.Column(
        db.Text, nullable=True
    )  # JSON des codes de récupération
    two_factor_enabled_at = db.Column(db.DateTime, nullable=True)
    email_2fa_code = db.Column(
        db.String(100), nullable=True
    )  # Code email 2FA temporaire (format: "CODE|EXPIRY")

    # Reset mot de passe (token hashé en DB pour sécurité)
    reset_token = db.Column(db.String(256), nullable=True, index=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    # Dernier changement de mot de passe : les sessions et jetons JWT ouverts
    # avant sont refusés (cf. get_id, load_user et check_if_token_revoked)
    password_changed_at = db.Column(db.DateTime, nullable=True)

    # Suivi des connexions
    last_login = db.Column(db.DateTime, nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    current_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(50), nullable=True)
    current_login_ip = db.Column(db.String(50), nullable=True)
    login_count = db.Column(db.Integer, default=0, nullable=False)

    # Horodatages
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relations
    roles = db.relationship("Role", secondary="user_roles", back_populates="users")
    settings = db.relationship(
        "UserSetting", back_populates="user", cascade="all, delete-orphan"
    )
    budgets = db.relationship(
        "Budget", back_populates="user", cascade="all, delete-orphan"
    )
    reports = db.relationship(
        Report, back_populates="user", cascade="all, delete-orphan"
    )
    notifications = db.relationship(
        Notification, back_populates="user", cascade="all, delete-orphan"
    )
    notification_preferences = db.relationship(
        NotificationPreference, back_populates="user", cascade="all, delete-orphan"
    )

    # Index supplémentaires
    __table_args__ = (
        db.Index("idx_user_email_lower", db.func.lower(email)),
        db.Index("idx_user_username_lower", db.func.lower(username)),
        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<User {self.username}>"

    @property
    def password(self):
        """Empêche la lecture directe du mot de passe."""
        raise AttributeError("password is not a readable attribute")

    @password.setter
    def password(self, password):
        """Définit le mot de passe avec hachage sécurisé.

        Horodate le changement : toute session ou tout jeton antérieur devient
        invalide (passer par ce setter pour tout changement de mot de passe).
        """
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")
        self.password_changed_at = datetime.now(timezone.utc)

    def _empreinte_mot_de_passe(self):
        """Seconde du dernier changement de mot de passe (None si jamais changé)."""
        if self.password_changed_at is None:
            return None
        changed = self.password_changed_at
        if changed.tzinfo is None:
            changed = changed.replace(tzinfo=timezone.utc)
        return int(changed.timestamp())

    def get_id(self):
        """Identifiant stocké en session par Flask-Login : "<id>.<empreinte>".

        Une session ouverte avant un changement de mot de passe porte une autre
        empreinte et n'est plus reconnue par load_user.
        """
        empreinte = self._empreinte_mot_de_passe()
        return str(self.id) if empreinte is None else f"{self.id}.{empreinte}"

    @classmethod
    def depuis_identifiant_session(cls, identifiant):
        """Inverse de get_id : l'utilisateur, ou None si l'empreinte ne correspond plus."""
        try:
            user_id, _, empreinte = str(identifiant).partition(".")
            user = db.session.get(cls, int(user_id))
        except TypeError, ValueError:
            return None
        if user is None:
            return None
        attendue = user._empreinte_mot_de_passe()
        if attendue is not None and empreinte != str(attendue):
            return None
        return user

    def jeton_emis_avant_changement(self, iat):
        """True si un jeton émis à iat (secondes) précède le dernier changement."""
        empreinte = self._empreinte_mot_de_passe()
        return empreinte is not None and int(iat) < empreinte

    def check_password(self, password):
        """
        Vérifie si le mot de passe fourni correspond au hachage stocké.
        Gère plusieurs formats de hachage : bcrypt, scrypt, pbkdf2.
        """
        from werkzeug.security import check_password_hash as werkzeug_check_password

        from ..extensions import bcrypt

        # Si le hachage commence par $2b$ (bcrypt), utiliser Flask-Bcrypt
        if self.password_hash.startswith("$2b$"):
            try:
                # Vérifier si le mot de passe correspond au hachage bcrypt
                return bcrypt.check_password_hash(self.password_hash, password)
            except Exception as e:
                current_app.logger.error(
                    f"Erreur lors de la vérification bcrypt: {str(e)}"
                )
                return False
        # Si c'est un hachage scrypt ou pbkdf2, utiliser la méthode Werkzeug standard
        elif self.password_hash.startswith(("scrypt:", "pbkdf2:")):
            try:
                return werkzeug_check_password(self.password_hash, password)
            except Exception as e:
                current_app.logger.error(
                    f"Erreur lors de la vérification du hachage: {str(e)}"
                )
                return False
        # Pour les autres formats, essayer la méthode Werkzeug standard
        else:
            try:
                return werkzeug_check_password(self.password_hash, password)
            except Exception as e:
                current_app.logger.error(
                    f"Erreur lors de la vérification du mot de passe: {str(e)}"
                )
                return False

    def has_role(self, role_name):
        """Vérifie si l'utilisateur a le rôle spécifié."""
        return any(role.name == role_name for role in self.roles)

    def has_permission(self, permission_name):
        """Vérifie si l'utilisateur a la permission spécifiée via ses rôles."""
        return any(
            permission.name == permission_name
            for role in self.roles
            for permission in role.permissions
        )

    def full_name(self):
        """Retourne le nom complet de l'utilisateur."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username

    def to_dict(self):
        """Convertit l'utilisateur en dictionnaire pour la sérialisation JSON.

        Returns:
            dict: Représentation dictionnaire de l'utilisateur
        """
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "address": self.address,
            "city": self.city,
            "postal_code": self.postal_code,
            "country": self.country,
            "language": self.language,
            "timezone": self.timezone,
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": (
                self.last_login_at.isoformat() if self.last_login_at else None
            ),
            "roles": [role.name for role in self.roles] if self.roles else [],
        }

    @property
    def is_admin(self):
        """Vérifie si l'utilisateur a le rôle administrateur."""
        return self.has_role("admin")
