"""
Modèle pour les notifications utilisateur.
"""

from datetime import datetime, timezone

from core.extensions import db


class Notification(db.Model):
    """Modèle pour les notifications utilisateur"""

    __tablename__ = "notifications"
    __table_args__ = {"extend_existing": True}

    # États possibles pour une notification
    STATUS_PENDING = "pending"  # En attente d'envoi
    STATUS_SENT = "sent"  # Envoyée avec succès
    STATUS_FAILED = "failed"  # Échec de l'envoi
    STATUS_DELIVERED = "delivered"  # Livrée au destinataire
    STATUS_READ = "read"  # Lue par l'utilisateur

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(128), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default=STATUS_PENDING, nullable=False)
    notification_type = db.Column(
        db.String(50), nullable=False
    )  # Ex: 'info', 'warning', 'error', 'success'
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    read_at = db.Column(db.DateTime)
    notification_metadata = db.Column(
        "metadata", db.JSON
    )  # Pour stocker des données supplémentaires

    # Relations
    user = db.relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.id} - {self.title} ({self.status})>"

    def mark_as_read(self):
        """Marque la notification comme lue"""
        self.is_read = True
        self.status = self.STATUS_READ
        self.read_at = datetime.now(timezone.utc)

    def mark_as_sent(self):
        """Marque la notification comme envoyée"""
        self.status = self.STATUS_SENT

    def mark_as_delivered(self):
        """Marque la notification comme livrée"""
        self.status = self.STATUS_DELIVERED

    def mark_as_failed(self, error_message=None):
        """Marque la notification comme échouée"""
        self.status = self.STATUS_FAILED
        if error_message:
            if not self.notification_metadata:
                self.notification_metadata = {}
            self.notification_metadata["error"] = str(error_message)

    def to_dict(self):
        """Convertit la notification en dictionnaire pour la sérialisation."""
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "status": self.status,
            "type": self.notification_type,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "metadata": self.notification_metadata,
            "user_id": self.user_id,
        }
