"""
Service de gestion des notifications utilisateur.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from flask import current_app

from core.extensions import db
from core.models.notification import Notification
from core.models.notification_preference import NotificationPreference
from core.models.user import User

# Supprimé : service boitemail supprimé

logger = logging.getLogger(__name__)


class NotificationService:
    """Service de gestion des notifications"""

    @staticmethod
    def create_notification(
        user_id: int,
        title: str,
        message: str,
        notification_type: str = "info",
        action_url: str = None,
        metadata: Dict = None,
    ) -> Notification:
        """Crée une nouvelle notification pour un utilisateur"""
        # Préparer les métadonnées
        notification_metadata = metadata or {}
        if action_url:
            notification_metadata["action_url"] = action_url

        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            notification_metadata=notification_metadata,
        )
        db.session.add(notification)
        db.session.commit()
        return notification

    @staticmethod
    def get_user_notifications(
        user_id: int, unread_only: bool = False, limit: int = 50, offset: int = 0
    ) -> List[Notification]:
        """Récupère les notifications d'un utilisateur"""
        query = Notification.query.filter_by(user_id=user_id)

        if unread_only:
            query = query.filter_by(is_read=False)

        return (
            query.order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def mark_as_read(notification_id: int, user_id: int) -> bool:
        """Marque une notification comme lue"""
        notification = Notification.query.filter_by(
            id=notification_id, user_id=user_id
        ).first()

        if notification and not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            db.session.commit()
            return True
        return False

    @staticmethod
    def mark_all_as_read(user_id: int) -> int:
        """Marque toutes les notifications non lues comme lues"""
        count = Notification.query.filter_by(user_id=user_id, is_read=False).update(
            {"is_read": True, "read_at": datetime.now(timezone.utc)}
        )

        if count > 0:
            db.session.commit()

        return count

    @staticmethod
    def get_notification_preferences(user_id: int) -> Dict[str, Any]:
        """Récupère les préférences de notification d'un utilisateur"""
        preferences = {}
        for pref in NotificationPreference.query.filter_by(user_id=user_id):
            preferences[pref.notification_type] = {
                "email": pref.email,
                "push": pref.push,
                "sms": pref.sms,
                "frequency": pref.frequency,
                "min_amount": float(pref.min_amount) if pref.min_amount else None,
            }
        return preferences

    @staticmethod
    def update_notification_preferences(
        user_id: int,
        notification_type: str,
        email: bool = None,
        push: bool = None,
        sms: bool = None,
        frequency: str = None,
        min_amount: float = None,
    ) -> NotificationPreference:
        """Met à jour les préférences de notification"""
        pref = NotificationPreference.query.filter_by(
            user_id=user_id, notification_type=notification_type
        ).first()

        if not pref:
            pref = NotificationPreference(
                user_id=user_id, notification_type=notification_type
            )
            db.session.add(pref)

        if email is not None:
            pref.email = email
        if push is not None:
            pref.push = push
        if sms is not None:
            pref.sms = sms
        if frequency is not None:
            pref.frequency = frequency
        if min_amount is not None:
            pref.min_amount = min_amount

        db.session.commit()
        return pref

    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """Compte le nombre de notifications non lues pour un utilisateur"""
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()

    @staticmethod
    def send_notification(
        user_id: int,
        title: str,
        message: str,
        notification_type: str = "info",
        action_url: str = None,
        metadata: Dict = None,
        force_send: bool = False,
        send_email: bool = None,
    ) -> Notification:
        """
        Envoie une notification en respectant les préférences utilisateur

        Args:
            user_id: ID de l'utilisateur
            title: Titre de la notification
            message: Contenu du message
            notification_type: Type de notification (info, warning, error, success)
            action_url: URL d'action optionnelle
            metadata: Métadonnées supplémentaires
            force_send: Ignorer les préférences utilisateur

        Returns:
            Notification: L'objet notification créé
        """
        # Crée la notification dans la base de données
        notification = NotificationService.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            action_url=action_url,
            metadata=metadata or {},
        )

        # Récupérer les préférences utilisateur
        pref = None
        user = db.session.get(User, user_id)

        # Si force_send est True, on envoie la notification immédiatement
        # Sinon, on respecte les préférences utilisateur
        if not force_send:
            pref = NotificationPreference.query.filter_by(
                user_id=user_id, notification_type=notification_type
            ).first()

            # Si aucune préférence n'existe pour ce type de notification,
            # on utilise les paramètres par défaut
            if not pref:
                pref = NotificationPreference(
                    user_id=user_id,
                    notification_type=notification_type,
                    email=True,  # Par défaut, on envoie par email
                    push=True,  # et par notification push
                    sms=False,  # Pas par SMS par défaut
                    frequency="immediate",
                )
                db.session.add(pref)
                db.session.commit()

            # Vérifier si on doit envoyer la notification
            # selon les préférences utilisateur
            if not any([pref.email, pref.push, pref.sms]):
                # L'utilisateur a désactivé toutes les notifications pour ce type
                return notification

        # Récupérer l'action_url depuis les métadonnées
        action_url_meta = (
            notification.notification_metadata.get("action_url")
            if notification.notification_metadata
            else action_url
        )

        # Envoyer les notifications selon les préférences
        try:
            # Envoyer par email si demandé
            if (send_email or (pref and pref.email)) and user.email:
                from app.utils.email import send_email as send_mail

                # Préparer le contenu de l'email
                subject = f"Notification : {title}"

                sender = current_app.config.get("MAIL_DEFAULT_SENDER")
                recipients = [user.email]
                logger.info(
                    f"📧 Configuration email: sender={sender}, recipient={recipients[0]}"
                )

                # Corps du message en texte brut
                text_body = f"""
Bonjour,

{message}

{f'Action disponible : {action_url_meta}' if action_url_meta else ''}

Cordialement,
L'équipe Budget App
                """.strip()

                # Corps du message en HTML
                action_link = (
                    f'<p><a href="{action_url_meta}">Cliquez ici pour accéder à l\'action</a></p>'
                    if action_url_meta
                    else ""
                )
                html_body = f"""
<html>
<body>
    <h2>{title}</h2>
    <p>{message}</p>
    {action_link}
    <p>Cordialement,<br>L'équipe Budget App</p>
</body>
</html>
                """.strip()

                try:
                    send_mail(subject, sender, recipients, text_body, html_body)
                    logger.info(
                        f"📧 Notification email envoyée à {user.email} (type: {notification_type})"
                    )
                except Exception as email_error:
                    logger.error(
                        f"💥 Échec envoi notification email à {user.email}: {email_error}"
                    )

        except Exception as e:
            logger.error(f"Erreur lors de l'envoi des notifications: {str(e)}")
            # On continue même en cas d'erreur pour ne pas bloquer le flux

        return notification
