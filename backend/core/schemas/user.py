"""
Schémas de validation et de sérialisation pour les utilisateurs.

Ce module contient tous les schémas liés aux utilisateurs, y compris la création,
la mise à jour et la réponse API pour les utilisateurs et leurs rôles.

Refactorisé pour utiliser Pydantic au lieu de Marshmallow pour une cohérence
avec tous les autres schémas du projet.
"""

import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBaseSchema(BaseModel):
    """Schéma de base pour les utilisateurs."""

    id: Optional[int] = Field(None, description="ID unique de l'utilisateur")
    username: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Nom d'utilisateur (3-64 caractères)",
    )

    email: EmailStr = Field(..., description="Adresse email de l'utilisateur")

    first_name: Optional[str] = Field(None, max_length=50, description="Prénom")
    last_name: Optional[str] = Field(None, max_length=50, description="Nom de famille")
    phone: Optional[str] = Field(None, max_length=20, description="Numéro de téléphone")

    # Champs de statut
    is_active: Optional[bool] = Field(None, description="Compte actif")
    email_verified: Optional[bool] = Field(None, description="Email vérifié")
    is_locked: Optional[bool] = Field(None, description="Compte verrouillé")
    login_attempts: Optional[int] = Field(None, description="Tentatives de connexion")

    # Horodatages
    last_login: Optional[datetime] = Field(None, description="Dernière connexion")
    last_login_at: Optional[datetime] = Field(
        None, description="Dernière connexion (timestamp)"
    )
    current_login_at: Optional[datetime] = Field(None, description="Connexion actuelle")
    last_login_ip: Optional[str] = Field(None, description="Dernière IP de connexion")
    current_login_ip: Optional[str] = Field(
        None, description="IP de connexion actuelle"
    )
    login_count: Optional[int] = Field(None, description="Nombre de connexions")
    created_at: Optional[datetime] = Field(None, description="Date de création")
    updated_at: Optional[datetime] = Field(None, description="Dernière mise à jour")
    deactivated_at: Optional[datetime] = Field(
        None, description="Date de désactivation"
    )
    deactivation_reason: Optional[str] = Field(
        None, description="Raison de désactivation"
    )

    @field_validator("username")
    def validate_username(cls, v):
        """Valide le nom d'utilisateur."""
        if not re.match(r"^[a-zA-Z0-9_.-]+$", v):
            raise ValueError(
                "Le nom d'utilisateur ne peut contenir que des lettres, chiffres, points, tirets et underscores"
            )
        return v


class UserCreateSchema(UserBaseSchema):
    """Schéma pour la création d'un utilisateur."""

    password: str = Field(
        ..., min_length=8, max_length=128, description="Mot de passe (8-128 caractères)"
    )

    confirm_password: Optional[str] = Field(
        None, description="Confirmation du mot de passe"
    )

    @field_validator("password")
    def validate_password(cls, v):
        """Valide la complexité du mot de passe."""
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if not re.search(r"[a-z]", v):
            raise ValueError("Le mot de passe doit contenir au moins une minuscule")
        if not re.search(r"[0-9]", v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        return v


class UserUpdateSchema(BaseModel):
    """Schéma pour la mise à jour d'un utilisateur."""

    # Champs optionnels pour la mise à jour
    username: Optional[str] = Field(
        None, min_length=3, max_length=64, description="Nom d'utilisateur"
    )
    email: Optional[EmailStr] = Field(None, description="Adresse email")
    first_name: Optional[str] = Field(None, max_length=50, description="Prénom")
    last_name: Optional[str] = Field(None, max_length=50, description="Nom de famille")
    phone: Optional[str] = Field(None, max_length=20, description="Numéro de téléphone")

    # Champs pour changement de mot de passe
    current_password: Optional[str] = Field(None, description="Mot de passe actuel")
    new_password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=128,
        description="Nouveau mot de passe (8-128 caractères)",
    )

    @field_validator("new_password")
    def validate_new_password(cls, v):
        """Valide la complexité du nouveau mot de passe."""
        if v and len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        return v

    @field_validator("username")
    def validate_username(cls, v):
        """Valide le nom d'utilisateur."""
        if v and not re.match(r"^[a-zA-Z0-9_.-]+$", v):
            raise ValueError(
                "Le nom d'utilisateur ne peut contenir que des lettres, chiffres, points, tirets et underscores"
            )
        return v


class UserResponseSchema(UserBaseSchema):
    """Schéma pour la réponse API des utilisateurs."""

    # Rôles de l'utilisateur
    roles: Optional[List["RoleSchema"]] = Field(
        None, description="Rôles de l'utilisateur"
    )

    # URL de l'avatar si disponible
    avatar_url: Optional[str] = Field(None, description="URL de l'avatar")

    model_config = ConfigDict(from_attributes=True)


class RoleSchema(BaseModel):
    """Schéma pour les rôles utilisateur."""

    id: Optional[int] = Field(None, description="ID unique du rôle")
    name: str = Field(..., min_length=2, max_length=50, description="Nom du rôle")
    description: Optional[str] = Field(None, description="Description du rôle")
    created_at: Optional[datetime] = Field(None, description="Date de création")
    updated_at: Optional[datetime] = Field(None, description="Dernière mise à jour")

    # Permissions associées
    permissions: Optional[List["PermissionSchema"]] = Field(
        None, description="Permissions du rôle"
    )


class PermissionSchema(BaseModel):
    """Schéma pour les permissions."""

    id: Optional[int] = Field(None, description="ID unique de la permission")
    name: str = Field(
        ..., min_length=2, max_length=100, description="Nom de la permission"
    )
    description: Optional[str] = Field(None, description="Description de la permission")
    created_at: Optional[datetime] = Field(None, description="Date de création")


# Mise à jour des références forward pour les relations
UserResponseSchema.model_rebuild()
RoleSchema.model_rebuild()

# Exports pour compatibilité avec le code existant
__all__ = [
    "UserBaseSchema",
    "UserCreateSchema",
    "UserUpdateSchema",
    "UserResponseSchema",
    "RoleSchema",
    "PermissionSchema",
]
