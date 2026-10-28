from datetime import datetime, timezone
from functools import wraps
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

# from ...validators.forms import PhoneValidator, ZipCodeValidator
# from ...validators.core import ValidationError
# from ...utils.security import hash_password, verify_password
from werkzeug.security import check_password_hash

from ...extensions import db
from ...models.user import User
from .profile_interface import IProfileService

# Import du cache de l'application
try:
    from ...extensions import cache
except ImportError:
    # Fallback si le cache n'est pas disponible
    cache = None


def cache_profile_data(expires_in=300):
    """
    Décorateur pour mettre en cache les résultats des méthodes du service de profil.

    Args:
        expires_in: Durée de validité du cache en secondes (par défaut: 5 minutes)
    """

    def decorator(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            # Créer une clé de cache unique basée sur la fonction et ses arguments
            cache_key = f"profile_{f.__name__}_{'_'.join(str(arg) for arg in args)}_{'_'.join(f'{k}_{v}' for k, v in kwargs.items())}"

            # Vérifier si le résultat est en cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Si non en cache, exécuter la fonction
            result = f(self, *args, **kwargs)

            # Mettre en cache le résultat
            cache.set(cache_key, result, timeout=expires_in)
            return result

        return wrapper

    return decorator


class ProfileService(IProfileService):
    """
    Implémentation concrète du service de gestion des profils avec mise en cache.

    Cette classe fournit des méthodes pour gérer les profils utilisateurs avec une couche
    de mise en cache pour améliorer les performances des lectures fréquentes.
    """

    def __init__(self, db_session: Session = None):
        """
        Initialise le service de profil avec une session de base de données.

        Args:
            db_session: Session SQLAlchemy pour l'accès à la base de données
        """
        self.db = db_session or db.session
        # self.phone_validator = PhoneValidator()
        # self.zip_validator = ZipCodeValidator()

        # Initialiser le cache s'il n'est pas déjà initialisé
        if not hasattr(self, "cache"):
            self.cache = cache

    @cache_profile_data(expires_in=3600)  # Mise en cache pour 1 heure
    def get_user_profile(self, user_id: int) -> Optional[User]:
        """
        Récupère le profil d'un utilisateur depuis le cache ou la base de données.

        Args:
            user_id: ID de l'utilisateur

        Returns:
            User: L'utilisateur correspondant ou None si non trouvé
        """
        cache_key = f"user_profile_{user_id}"
        user = self.cache.get(cache_key)

        if user is None:
            user = User.query.filter_by(id=user_id).first()
            if user:
                # Mettre en cache pendant 1 heure
                self.cache.set(cache_key, user, timeout=3600)

        return user

    def invalidate_profile_cache(self, user_id: int):
        """
        Invalide le cache pour un profil utilisateur.

        Args:
            user_id: ID de l'utilisateur
        """
        cache_key = f"user_profile_{user_id}"
        if self.cache:
            self.cache.delete(cache_key)

    def update_profile(self, user_id: int, profile_data: Dict) -> Tuple[bool, str, int]:
        """
        Met à jour le profil d'un utilisateur.

        Args:
            user_id: ID de l'utilisateur
            profile_data: Dictionnaire des données à mettre à jour

        Returns:
            Tuple[bool, str, int]: (succès, message, code_statut)
        """
        try:
            # Récupérer l'utilisateur directement sans cache pour éviter les données obsolètes
            user = User.query.filter_by(id=user_id).first()
            if not user:
                return False, "Utilisateur non trouvé", 404

            # Sauvegarder les anciennes valeurs pour la notification
            old_email = user.email
            old_phone = user.phone

            # Validation et mise à jour des champs
            if (
                "email" in profile_data
                and profile_data["email"].strip().lower() != user.email.strip().lower()
            ):
                if self._email_exists(
                    profile_data["email"].strip(), exclude_user_id=user_id
                ):
                    return False, "Cet email est déjà utilisé", 400
                user.email = profile_data["email"].strip()

            if "phone" in profile_data:
                # Validation simple du téléphone
                import re

                phone = profile_data["phone"]
                if phone and not re.match(r"^\+?[\d\s\-\(\)]+$", phone):
                    return False, "Format de numéro de téléphone invalide", 400
                user.phone = profile_data["phone"]

            # Mise à jour des champs de base
            for field in [
                "first_name",
                "last_name",
                "address",
                "city",
                "postal_code",
                "country",
                "language",
                "timezone",
            ]:
                if field in profile_data:
                    setattr(user, field, profile_data[field])

            # Mise à jour de la date de modification
            user.updated_at = datetime.now(timezone.utc)

            db.session.commit()

            # Invalider le cache pour cet utilisateur
            self.invalidate_profile_cache(user_id)

            # Invalider également les caches liés aux listes d'utilisateurs
            if self.cache:
                self.cache.delete("all_users_list")

            # 📧 Notification de modification de profil
            try:
                from core.services.notifications import NotificationService

                changes = []

                # Détection détaillée des changements
                if "email" in profile_data and profile_data["email"] != old_email:
                    changes.append(f"email: {old_email} → {user.email}")
                if "phone" in profile_data and profile_data["phone"] != old_phone:
                    changes.append(
                        f"téléphone: {old_phone or 'non renseigné'} → {user.phone or 'non renseigné'}"
                    )

                # Autres champs modifiés
                field_labels = {
                    "first_name": "prénom",
                    "last_name": "nom",
                    "address": "adresse",
                    "city": "ville",
                    "postal_code": "code postal",
                    "country": "pays",
                    "language": "langue",
                    "timezone": "fuseau horaire",
                }

                for field, label in field_labels.items():
                    if field in profile_data:
                        changes.append(f"{label} mis à jour")

                # Toujours envoyer une notification de modification
                # car l'utilisateur a effectué une action de modification
                NotificationService.send_notification(
                    user_id=user_id,
                    title="Profil modifié",
                    message=f"Votre profil a été modifié"
                    + (f": {', '.join(changes)}" if changes else " avec succès"),
                    notification_type="profile_updated",
                    action_url="/profile/",
                    send_email=True,
                    metadata={
                        "user_id": user_id,
                        "changes": changes,
                        "updated_fields": list(profile_data.keys()),
                    },
                )
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Erreur envoi notification modification profil: {e}")

            return True, "Profil mis à jour avec succès", 200

        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la mise à jour du profil: {str(e)}", 500

    def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> Tuple[bool, str, int]:
        """
        Change le mot de passe d'un utilisateur.

        Args:
            user_id: ID de l'utilisateur
            current_password: Mot de passe actuel
            new_password: Nouveau mot de passe

        Returns:
            Tuple[bool, str, int]: (succès, message, code_statut)
        """
        try:
            user = self.get_user_profile(user_id)
            if not user:
                return False, "Utilisateur non trouvé", 404

            # Vérifier l'ancien mot de passe
            if not check_password_hash(user.password_hash, current_password):
                return False, "Mot de passe actuel incorrect", 400

            # Valider le nouveau mot de passe : mêmes règles que l'inscription
            from core.services.auth.security_service import SecurityService

            valide, erreur = SecurityService(db).validate_password_strength(
                new_password
            )
            if not valide:
                return False, erreur, 400

            # Mettre à jour le mot de passe (le setter horodate le changement :
            # les autres sessions et les jetons de l'utilisateur sont coupés)
            user.password = new_password
            user.updated_at = datetime.now(timezone.utc)

            # Invalider toutes les sessions existantes (si la table existe)
            # db.session.execute(text("""
            #     DELETE FROM user_sessions
            #     WHERE user_id = :user_id
            # """), {'user_id': user_id})

            db.session.commit()

            # Invalider le cache de l'utilisateur
            self.invalidate_profile_cache(user_id)

            # 📧 Notification de changement de mot de passe (sécurité)
            try:
                from core.services.notifications import NotificationService

                NotificationService.send_notification(
                    user_id=user_id,
                    title="Mot de passe modifié",
                    message="Votre mot de passe a été modifié avec succès. Si ce n'était pas vous, contactez immédiatement le support.",
                    notification_type="security_alert",
                    action_url="/profile/",
                    send_email=True,
                    force_send=True,  # Toujours envoyer pour les alertes de sécurité
                    metadata={
                        "user_id": user_id,
                        "event_type": "password_changed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Erreur envoi notification changement mot de passe: {e}"
                )

            return True, "Mot de passe mis à jour avec succès", 200

        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors du changement de mot de passe: {str(e)}", 500

    def _email_exists(self, email: str, exclude_user_id: int = None) -> bool:
        """
        Vérifie si un email existe déjà dans la base de données.

        Args:
            email: Adresse email à vérifier
            exclude_user_id: ID de l'utilisateur à exclure de la vérification

        Returns:
            bool: True si l'email existe déjà, False sinon
        """
        query = User.query.filter(db.func.lower(User.email) == email.lower())
        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)
        return query.first() is not None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Récupère un utilisateur par son adresse email avec mise en cache.

        Args:
            email: Adresse email de l'utilisateur

        Returns:
            User: L'utilisateur correspondant ou None si non trouvé
        """
        cache_key = f"user_by_email_{email}"
        user = self.cache.get(cache_key)

        if user is None:
            user = User.query.filter_by(email=email).first()
            if user:
                # Mettre en cache pendant 1 heure
                self.cache.set(cache_key, user, timeout=3600)

                # Mettre également en cache par ID pour cohérence
                self.cache.set(f"user_profile_{user.id}", user, timeout=3600)

        return user

    def get_user_profile_data(self, user_id: int) -> Dict[str, Any]:
        """
        Récupère les données de profil d'un utilisateur sous forme de dictionnaire.

        Args:
            user_id: ID de l'utilisateur

        Returns:
            Dict: Dictionnaire contenant les données du profil
        """
        cache_key = f"user_profile_data_{user_id}"
        profile_data = self.cache.get(cache_key)

        if profile_data is None:
            user = self.get_user_profile(user_id)
            if not user:
                return {}

            # Convertir l'utilisateur en dictionnaire
            profile_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "address": user.address,
                "city": user.city,
                "postal_code": user.postal_code,
                "country": user.country,
                "language": user.language,
                "timezone": user.timezone,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            }

            # Mettre en cache pendant 30 minutes
            self.cache.set(cache_key, profile_data, timeout=1800)

        return profile_data
