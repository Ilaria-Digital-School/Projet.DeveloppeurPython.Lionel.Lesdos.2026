"""
Modèles pour la gestion des rôles et permissions.
"""

from datetime import datetime, timezone

from ..extensions import db

# Table de liaison entre rôles et permissions
role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
    db.Column(
        "permission_id", db.Integer, db.ForeignKey("permissions.id"), primary_key=True
    ),
    db.Column("assigned_at", db.DateTime, nullable=False, server_default=db.func.now()),
)


class Role(db.Model):
    """Modèle de rôle utilisateur."""

    __tablename__ = "roles"
    __table_args__ = {
        "extend_existing": True
    }  # Permet de redéfinir la table si elle existe déjà

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    is_system = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.false()
    )
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
    users = db.relationship("User", secondary="user_roles", back_populates="roles")
    permissions = db.relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )

    def __repr__(self):
        return f"<Role {self.name}>"

    def add_permission(self, permission):
        """Ajoute une permission à ce rôle."""
        if not self.has_permission(permission):
            self.permissions.append(permission)

    def remove_permission(self, permission):
        """Retire une permission de ce rôle."""
        if self.has_permission(permission):
            self.permissions.remove(permission)

    def has_permission(self, permission):
        """Vérifie si ce rôle a la permission spécifiée."""
        if isinstance(permission, str):
            return any(p.name == permission for p in self.permissions)
        return permission in self.permissions
