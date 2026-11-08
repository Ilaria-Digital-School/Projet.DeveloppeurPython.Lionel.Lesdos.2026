"""
Modèles liés à la gestion des emails.
"""

from datetime import datetime, timezone
from enum import Enum

from . import db


class EmailStatus(Enum):
    """Statuts possibles d'un email"""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


class EmailTemplate(db.Model):
    """Modèle pour les templates d'emails"""

    __tablename__ = "email_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    template_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<EmailTemplate {self.name}>"


class EmailQueue(db.Model):
    """File d'attente des emails à envoyer"""

    __tablename__ = "email_queue"

    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    template_name = db.Column(db.String(100), nullable=False)
    template_data = db.Column(db.JSON)
    status = db.Column(
        db.Enum(EmailStatus, native_enum=False, length=8),
        default=EmailStatus.PENDING,
    )
    retry_count = db.Column(db.Integer, default=0)
    last_attempt = db.Column(db.DateTime)
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<EmailQueue {self.id} - {self.recipient} - {self.status.value}>"
