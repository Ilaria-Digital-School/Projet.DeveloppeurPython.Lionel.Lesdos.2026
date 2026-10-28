"""
Modèle pour la gestion des permissions.

Ce module définit le modèle de base pour les permissions dans le système.
"""

from datetime import datetime, timezone

from ..extensions import db


class Permission(db.Model):
    """Modèle de permission.

    Une permission représente une action spécifique qu'un utilisateur peut effectuer.
    Les permissions sont généralement associées à des rôles plutôt qu'à des utilisateurs individuels.
    """

    __tablename__ = "permissions"
    __table_args__ = {
        "extend_existing": True
    }  # Permet de redéfinir la table si elle existe déjà

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=True)
    description = db.Column(db.String(255))
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relations
    roles = db.relationship(
        "Role", secondary="role_permissions", back_populates="permissions"
    )

    def __repr__(self):
        return f"<Permission {self.name}>"

    def to_dict(self):
        """Convertit la permission en dictionnaire."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
