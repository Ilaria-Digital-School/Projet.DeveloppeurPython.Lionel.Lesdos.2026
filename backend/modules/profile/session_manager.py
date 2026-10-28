"""
Gestion des sessions utilisateur et des jetons de rafraîchissement.
Implémente l'interface ISessionManager du core.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from flask import current_app, request

from core.extensions import db
from core.models.session import UserSession
from core.services.profile.profile_interface import ISessionManager

logger = logging.getLogger(__name__)


class SessionManager(ISessionManager):
    """Gestion des sessions utilisateur et des jetons de rafraîchissement."""

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialise l'extension avec l'application Flask."""
        self.app = app
        app.session_manager = self

        # Configuration par défaut
        app.config.setdefault("REFRESH_TOKEN_EXPIRES", 30)  # jours
        app.config.setdefault("SESSION_INACTIVITY_TIMEOUT", 60)  # minutes

    def create_session_token(self, user_id, user_agent=None, ip_address=None):
        """
        Crée un nouveau jeton de session pour un utilisateur.

        Args:
            user_id: ID de l'utilisateur
            user_agent: User-Agent du navigateur (optionnel)
            ip_address: Adresse IP de l'utilisateur (optionnel)

        Returns:
            Dict: Informations sur la session créée
        """
        session_id = secrets.token_urlsafe(32)
        expires_in = timedelta(
            minutes=current_app.config.get("SESSION_INACTIVITY_TIMEOUT", 60)
        )
        expires_at = datetime.now(timezone.utc) + expires_in

        # Création de la session en base de données
        session = UserSession(
            id=session_id,
            user_id=user_id,
            user_agent=user_agent or (request.user_agent.string if request else None),
            ip_address=ip_address or (request.remote_addr if request else None),
            expires_at=expires_at,
            is_active=True,
        )

        db.session.add(session)
        db.session.commit()

        return {
            "session_id": session_id,
            "expires_at": expires_at.isoformat(),
            "user_id": user_id,
        }

    def validate_session_token(self, session_id, user_id):
        """
        Valide un jeton de session pour un utilisateur.

        Args:
            session_id: ID de la session à valider
            user_id: ID de l'utilisateur

        Returns:
            bool: True si la session est valide, False sinon
        """
        if not session_id or not user_id:
            return False

        # Récupération de la session
        session = db.session.get(UserSession, session_id)

        # Vérification de la session
        if (
            not session
            or not session.is_active
            or session.user_id != user_id
            or session.is_expired
        ):
            return False

        # Mise à jour de la dernière activité
        expires_in = timedelta(
            minutes=current_app.config.get("SESSION_INACTIVITY_TIMEOUT", 60)
        )
        session.refresh(expires_in)
        db.session.commit()

        return True

    def revoke_session(self, session_id, user_id):
        """
        Révoque une session spécifique pour un utilisateur.

        Args:
            session_id: ID de la session à révoquer
            user_id: ID de l'utilisateur
        """
        session = UserSession.query.filter_by(id=session_id, user_id=user_id).first()

        if session:
            session.revoke()
            db.session.commit()

    def revoke_all_sessions(self, user_id, exclude_session_id=None):
        """
        Révoque toutes les sessions d'un utilisateur, sauf celle spécifiée.

        Args:
            user_id: ID de l'utilisateur
            exclude_session_id: ID de la session à exclure (optionnel)
        """
        query = UserSession.query.filter_by(user_id=user_id, is_active=True)

        if exclude_session_id:
            query = query.filter(UserSession.id != exclude_session_id)

        for session in query.all():
            session.revoke()

        db.session.commit()

    def get_active_sessions(self, user_id: int) -> List[Dict]:
        """
        Récupère les sessions actives d'un utilisateur.

        Args:
            user_id: ID de l'utilisateur

        Returns:
            List[Dict]: Liste des sessions actives avec leurs informations
        """
        current_session_id = getattr(request, "session_id", None) if request else None

        sessions = (
            UserSession.query.filter_by(user_id=user_id, is_active=True)
            .filter(UserSession.expires_at > datetime.now(timezone.utc))
            .order_by(UserSession.last_activity.desc())
            .all()
        )

        return [
            {**session.to_dict(), "is_current": session.id == current_session_id}
            for session in sessions
        ]

    def create_refresh_token(self, user_id):
        """Crée un jeton de rafraîchissement pour un utilisateur."""
        token = secrets.token_urlsafe(64)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=current_app.config.get("REFRESH_TOKEN_EXPIRES", 30)
        )

        return {"token": token, "expires_at": expires_at.isoformat()}

    def verify_refresh_token(self, token, user_id):
        """Vérifie la validité d'un jeton de rafraîchissement."""
        return True  # À implémenter avec la base de données

    def revoke_refresh_token(self, token):
        """Révoque un jeton de rafraîchissement."""
        pass  # À implémenter avec la base de données


# Instance du gestionnaire de sessions
session_manager = SessionManager()
