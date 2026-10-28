"""
Modèle pour la blacklist des tokens JWT.

Stocke les JTI (JWT ID) des tokens révoqués pour empêcher leur réutilisation après logout.
"""

from datetime import datetime, timezone

from ..extensions import db


class TokenBlacklist(db.Model):
    """Token JWT révoqué."""

    __tablename__ = "token_blacklist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    expires_at = db.Column(db.DateTime, nullable=False)

    @classmethod
    def is_token_revoked(cls, jti):
        """Vérifie si un token est dans la blacklist."""
        return cls.query.filter_by(jti=jti).first() is not None

    @classmethod
    def revoke_token(cls, jti, expires_at):
        """Ajoute un token à la blacklist."""
        entry = cls(jti=jti, expires_at=expires_at)
        db.session.add(entry)
        db.session.commit()

    @classmethod
    def cleanup_expired(cls):
        """Supprime les tokens expirés de la blacklist."""
        cls.query.filter(cls.expires_at < datetime.now(timezone.utc)).delete()
        db.session.commit()
