"""
Modèle pour les préférences de notification des utilisateurs.
"""

from datetime import datetime, timezone

from core.extensions import db


class NotificationPreference(db.Model):
    """Préférences de notification par type"""

    __tablename__ = "notification_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notification_type = db.Column(db.String(50), nullable=False)  # Type de notification
    email = db.Column(
        db.Boolean, default=True, nullable=False
    )  # Notification par email
    push = db.Column(db.Boolean, default=True, nullable=False)  # Notification push
    sms = db.Column(db.Boolean, default=False, nullable=False)  # Notification SMS
    frequency = db.Column(
        db.String(20), default="immediate", nullable=False
    )  # Fréquence d'envoi
    min_amount = db.Column(db.Float, nullable=True)  # Montant minimum pour notification
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Contraintes
    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "notification_type", name="_user_notification_type_uc"
        ),
        {"extend_existing": True},
    )

    # Relations
    user = db.relationship("User", back_populates="notification_preferences")

    def __repr__(self):
        return f"<NotificationPreference {self.user_id} - {self.notification_type}>"

    def to_dict(self):
        """Convertit les préférences en dictionnaire"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "notification_type": self.notification_type,
            "email": self.email,
            "push": self.push,
            "sms": self.sms,
            "frequency": self.frequency,
            "min_amount": float(self.min_amount) if self.min_amount else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
