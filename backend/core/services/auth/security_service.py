"""
Service de gestion de la sécurité des utilisateurs.

Ce module gère la validation des mots de passe, le verrouillage des comptes
et d'autres fonctionnalités liées à la sécurité.
"""

import logging
import re
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .config import (
    ERROR_MESSAGES,
    LOGIN_ATTEMPTS_LIMIT,
    LOGIN_LOCKOUT_TIME,
    PASSWORD_COMPLEXITY,
)

logger = logging.getLogger(__name__)


class SecurityService:
    """Service de gestion de la sécurité des utilisateurs."""

    def __init__(self, db):
        """Initialise le service de sécurité.

        Args:
            db: Instance de la base de données SQLAlchemy
        """
        self.db = db

    def validate_password_strength(self, password):
        """Vérifie la force d'un mot de passe.

        Args:
            password (str): Le mot de passe à valider

        Returns:
            tuple: (bool, str) - (True, '') si valide, (False, message_erreur) sinon
        """
        if len(password) < PASSWORD_COMPLEXITY["min_length"]:
            return (
                False,
                f"Le mot de passe doit contenir au moins {PASSWORD_COMPLEXITY['min_length']} caractères",
            )

        if PASSWORD_COMPLEXITY["require_uppercase"] and not re.search(
            r"[A-Z]", password
        ):
            return False, "Le mot de passe doit contenir au moins une majuscule"

        if PASSWORD_COMPLEXITY["require_lowercase"] and not re.search(
            r"[a-z]", password
        ):
            return False, "Le mot de passe doit contenir au moins une minuscule"

        if PASSWORD_COMPLEXITY["require_digit"] and not re.search(r"\d", password):
            return False, "Le mot de passe doit contenir au moins un chiffre"

        if PASSWORD_COMPLEXITY["require_special_char"] and not any(
            char in PASSWORD_COMPLEXITY["special_chars"] for char in password
        ):
            return (
                False,
                f"Le mot de passe doit contenir au moins un caractère spécial parmi: {PASSWORD_COMPLEXITY['special_chars']}",
            )

        return True, ""

    def hash_password(self, password):
        """Hache un mot de passe.

        Args:
            password (str): Mot de passe en clair

        Returns:
            str: Mot de passe haché
        """
        return generate_password_hash(password)

    def check_password(self, password_hash, password):
        """Vérifie si un mot de passe correspond à son hash.

        Args:
            password_hash (str): Hash du mot de passe stocké
            password (str): Mot de passe en clair à vérifier

        Returns:
            bool: True si le mot de passe correspond, False sinon
        """
        return check_password_hash(password_hash, password)

    def _get_user(self, user_id):
        """Récupère un utilisateur par ID."""
        from core.models.user import User

        return self.db.session.get(User, user_id)

    def is_account_locked(self, user_id):
        """Vérifie si un compte est verrouillé (persistant en DB).

        Args:
            user_id (int): ID de l'utilisateur

        Returns:
            tuple: (bool, int) - (True, unlock_timestamp) si verrouillé, (False, 0) sinon
        """
        user = self._get_user(user_id)
        if not user:
            return False, 0

        if not user.is_locked:
            return False, 0

        # Calculer la fin du verrouillage à partir de updated_at
        lock_start = user.updated_at or datetime.now(timezone.utc)
        # S'assurer que lock_start est timezone-aware
        if lock_start.tzinfo is None:
            lock_start = lock_start.replace(tzinfo=timezone.utc)
        unlock_time = lock_start + LOGIN_LOCKOUT_TIME

        if datetime.now(timezone.utc) < unlock_time:
            return True, unlock_time.timestamp()

        # Période de verrouillage écoulée : déverrouiller
        user.is_locked = False
        user.login_attempts = 0
        self.db.session.commit()
        return False, 0

    def record_login_attempt(self, user_id, success):
        """Enregistre une tentative de connexion (persistant en DB).

        Args:
            user_id (int): ID de l'utilisateur
            success (bool): Si la tentative a réussi

        Returns:
            tuple: (bool, str) - (True, '') si le compte n'est pas verrouillé,
                  (False, message_erreur) sinon
        """
        user = self._get_user(user_id)
        if not user:
            return True, ""

        if success:
            user.login_attempts = 0
            user.is_locked = False
            self.db.session.commit()
            return True, ""

        # Incrémenter le compteur d'échecs
        user.login_attempts = (user.login_attempts or 0) + 1
        attempts = user.login_attempts

        if attempts >= LOGIN_ATTEMPTS_LIMIT:
            user.is_locked = True
            self.db.session.commit()
            logger.warning(
                f"Compte verrouillé après {attempts} tentatives échouées (user_id={user_id})"
            )
            return False, ERROR_MESSAGES["account_locked"]

        self.db.session.commit()
        remaining = LOGIN_ATTEMPTS_LIMIT - attempts
        return True, f"Identifiants invalides. Il vous reste {remaining} tentative(s)."


# Instance singleton du service de sécurité
security_service = None


def init_security_service(db):
    """Initialise le service de sécurité.

    Args:
        db: Instance de la base de données SQLAlchemy

    Returns:
        SecurityService: Instance du service de sécurité
    """
    global security_service
    if security_service is None:
        security_service = SecurityService(db)
    return security_service
