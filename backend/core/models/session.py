"""
Modèle pour la gestion des sessions utilisateur.
"""

from datetime import datetime, timezone

from ..extensions import db


class UserSession(db.Model):
    """
    Modèle représentant une session utilisateur active.
    """

    __tablename__ = "user_sessions"

    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE", name="fk_sessions_user"),
        nullable=False,
    )
    user_agent = db.Column(db.Text)
    ip_address = db.Column(db.String(45))  # IPv6 peut faire jusqu'à 45 caractères
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_activity = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relation
    user = db.relationship("User", backref=db.backref("sessions", lazy="dynamic"))

    @property
    def is_expired(self):
        """Vérifie si la session a expiré."""
        expires_at = self.expires_at
        # PostgreSQL renvoie un datetime naif (colonne sans fuseau) : on le
        # considere en UTC pour pouvoir le comparer a un datetime aware.
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires_at

    def refresh(self, expires_in):
        """Rafraîchit la durée de vie de la session."""
        self.last_activity = datetime.now(timezone.utc)
        self.expires_at = self.last_activity + expires_in
        return self

    def revoke(self):
        """Révoque la session."""
        self.is_active = False
        return self

    def to_dict(self):
        """Convertit la session en dictionnaire."""
        return {
            "id": self.id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_current": False,  # Sera mis à jour si nécessaire
        }
