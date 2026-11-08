"""
Fichier pour les tables d'association entre les modèles.

Ce fichier contient les définitions des tables d'association qui lient les modèles entre eux.
"""

from ..extensions import db

# Table de liaison entre utilisateurs et rôles
user_roles = db.Table(
    "user_roles",
    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
    info={
        "description": "Table de liaison entre les utilisateurs et leurs rôles",
        "bind_key": "auth",  # Optionnel : pour le support multi-bases de données
    },
    extend_existing=True,  # Permet de redéfinir la table si elle existe déjà
)
