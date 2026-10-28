"""
Modèle pour les événements de sécurité.
"""

from datetime import datetime, timezone

from ..extensions import db


class SecurityEvent(db.Model):
    """
    Modèle pour enregistrer les événements de sécurité.
    """

    __tablename__ = "security_events"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(
        db.Integer,
        db.ForeignKey("devices.id", ondelete="CASCADE", name="fk_se_device"),
        nullable=False,
    )
    event_type = db.Column(
        db.String(50), nullable=False
    )  # Ex: 'login_success', 'login_failed', 'device_blocked'
    description = db.Column(db.Text, nullable=False)
    user_agent = db.Column(db.Text, nullable=True)
    ip_address = db.Column(
        db.String(45), nullable=True
    )  # IPv6 peut faire jusqu'à 45 caractères
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL", name="fk_se_user"),
        nullable=True,
    )
    timestamp = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relations
    device = db.relationship("Device", backref=db.backref("security_events", lazy=True))
    user = db.relationship("User", backref=db.backref("security_events", lazy=True))

    def __repr__(self):
        return f"<SecurityEvent {self.event_type} - {self.timestamp}>"

    def to_dict(self):
        """Convertit l'objet en dictionnaire pour la sérialisation JSON."""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "event_type": self.event_type,
            "description": self.description,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
