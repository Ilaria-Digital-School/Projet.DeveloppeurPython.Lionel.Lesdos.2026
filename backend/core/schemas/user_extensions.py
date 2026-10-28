"""
Schémas spécifiques au module utilisateur.

Ces schémas étendent les schémas de base pour ajouter des fonctionnalités
spécifiques au module utilisateur.

Refactorisé pour utiliser Pydantic au lieu de Marshmallow pour une cohérence
avec tous les autres schémas du projet.
"""

from typing import Optional

from pydantic import ConfigDict, Field, ValidationInfo, field_validator

from .user import UserCreateSchema as BaseUserCreateSchema
from .user import UserResponseSchema as BaseUserResponseSchema
from .user import UserUpdateSchema as BaseUserUpdateSchema


class UserCreateSchema(BaseUserCreateSchema):
    """Schéma pour la création d'utilisateur avec des validations spécifiques."""

    # Champ spécifique au module
    terms_accepted: bool = Field(
        ..., description="Acceptation des conditions d'utilisation (obligatoire)"
    )

    @field_validator("terms_accepted")
    def validate_terms_accepted(cls, v):
        """Valide l'acceptation des conditions d'utilisation."""
        if not v:
            raise ValueError("Vous devez accepter les conditions d'utilisation")
        return v

    @field_validator("username", mode="before")
    def clean_username(cls, v):
        """Nettoie les espaces superflus du nom d'utilisateur."""
        if isinstance(v, str):
            return v.strip()
        return v


class UserUpdateSchema(BaseUserUpdateSchema):
    """Schéma pour la mise à jour d'utilisateur avec des validations spécifiques."""

    # Champ spécifique au module pour validation de mot de passe
    current_password: Optional[str] = Field(
        None,
        min_length=8,
        description="Mot de passe actuel (requis pour changer le mot de passe)",
    )

    @field_validator("new_password")
    def validate_password_change(cls, v, info: ValidationInfo):
        """Valide que le mot de passe actuel est fourni pour changer le mot de passe."""
        if v and "current_password" not in info.data:
            raise ValueError(
                "Le mot de passe actuel est requis pour modifier le mot de passe"
            )
        return v


class UserResponseSchema(BaseUserResponseSchema):
    """Schéma pour la réponse API avec des champs spécifiques au module."""

    model_config = ConfigDict(populate_by_name=True)

    # Champ calculé pour le nom complet
    full_name: Optional[str] = Field(None, description="Nom complet de l'utilisateur")

    # Liens HATEOAS
    links: Optional[dict] = Field(
        None, alias="_links", description="Liens HATEOAS pour navigation API"
    )

    def model_dump(self, **kwargs):
        """Surcharge pour ajouter les champs calculés."""
        kwargs.setdefault("by_alias", True)
        data = super().model_dump(**kwargs)

        # Calculer le nom complet
        if self.first_name and self.last_name:
            data["full_name"] = f"{self.first_name} {self.last_name}"
        elif hasattr(self, "username"):
            data["full_name"] = self.username

        # Ajouter les liens HATEOAS
        if self.id:
            data["_links"] = {
                "self": f"/api/users/{self.id}",
                "collection": "/api/users",
            }

        return data


# Instances des schémas pour une utilisation facile
# Exports pour compatibilité avec le code existant
__all__ = ["UserCreateSchema", "UserUpdateSchema", "UserResponseSchema"]
