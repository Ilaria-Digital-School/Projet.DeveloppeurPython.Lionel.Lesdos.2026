"""
Schémas de validation pour les catégories de transactions.

Ce module définit les modèles Pydantic pour la validation des données
des catégories utilisées pour classer les transactions.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, constr, field_validator

# Types personnalisés
CategoryType = Literal["income", "expense", "both"]


class CategoryBase(BaseModel):
    """Schéma de base pour une catégorie."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Alimentation",
                "description": "Dépenses liées à l'alimentation et aux courses",
                "icon": "utensils",
                "color": "#4CAF50",
                "is_default": False,
                "transaction_type": "expense",
            }
        }
    )

    name: constr(min_length=1, max_length=50) = Field(
        ..., description="Nom de la catégorie"
    )
    description: Optional[constr(max_length=200)] = Field(
        None, description="Description de la catégorie"
    )
    icon: str = Field(
        "shopping-cart",
        description="Icône associée à la catégorie (nom de l'icône Font Awesome)",
    )
    color: str = Field(
        "#4CAF50", description="Couleur associée à la catégorie (format hexadécimal)"
    )
    is_default: bool = Field(
        False, description="Indique si c'est une catégorie par défaut du système"
    )
    transaction_type: CategoryType = Field(
        ...,
        description="Type de transaction pour cette catégorie (income, expense, both)",
    )

    @field_validator("color")
    def validate_color_format(cls, v):
        """Valide que la couleur est au format hexadécimal."""
        if not v.startswith("#"):
            raise ValueError("La couleur doit commencer par #")
        if len(v) not in [4, 7]:  # #RGB ou #RRGGBB
            raise ValueError("Format de couleur invalide. Utilisez #RGB ou #RRGGBB")
        # Vérifie que les caractères restants sont des chiffres hexadécimaux
        hex_digits = v[1:]
        if not all(c in "0123456789ABCDEFabcdef" for c in hex_digits):
            raise ValueError("La couleur doit être au format hexadécimal valide")
        return v.upper()  # Standardise en majuscules


class CategoryCreate(CategoryBase):
    """Schéma pour la création d'une catégorie."""

    parent_id: Optional[int] = Field(
        None, description="ID de la catégorie parente (pour les sous-catégories)"
    )


class CategoryUpdate(BaseModel):
    """Schéma pour la mise à jour d'une catégorie."""

    name: Optional[constr(min_length=1, max_length=50)] = Field(
        None, description="Nouveau nom de la catégorie"
    )
    description: Optional[constr(max_length=200)] = Field(
        None, description="Nouvelle description"
    )
    icon: Optional[str] = Field(None, description="Nouvelle icône")
    color: Optional[str] = Field(
        None, description="Nouvelle couleur (format hexadécimal)"
    )
    is_default: Optional[bool] = Field(
        None, description="Définir comme catégorie par défaut"
    )
    transaction_type: Optional[CategoryType] = Field(
        None, description="Nouveau type de transaction"
    )
    parent_id: Optional[int] = Field(
        None,
        description="Nouvelle catégorie parente (mettre 0 pour enlever la relation parente)",
    )

    @field_validator("color")
    def validate_color_format(cls, v):
        """Valide que la couleur est au format hexadécimal si elle est fournie."""
        if v is None:
            return v
        if not v.startswith("#"):
            raise ValueError("La couleur doit commencer par #")
        if len(v) not in [4, 7]:  # #RGB ou #RRGGBB
            raise ValueError("Format de couleur invalide. Utilisez #RGB ou #RRGGBB")
        # Vérifie que les caractères restants sont des chiffres hexadécimaux
        hex_digits = v[1:]
        if not all(c in "0123456789ABCDEFabcdef" for c in hex_digits):
            raise ValueError("La couleur doit être au format hexadécimal valide")
        return v.upper()  # Standardise en majuscules


class CategoryResponse(CategoryBase):
    """Schéma de réponse pour une catégorie."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                **CategoryBase.model_config["json_schema_extra"]["example"],
                "id": 1,
                "parent_id": None,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
            }
        },
    )

    id: int = Field(..., description="ID unique de la catégorie")
    parent_id: Optional[int] = Field(
        None, description="ID de la catégorie parente (si c'est une sous-catégorie)"
    )
    created_at: str = Field(..., description="Date de création de la catégorie")
    updated_at: str = Field(..., description="Date de dernière mise à jour")


class CategoryTreeItem(CategoryResponse):
    """Élément d'arborescence de catégories avec sous-catégories imbriquées."""

    model_config = ConfigDict(from_attributes=True)

    subcategories: List["CategoryTreeItem"] = Field(
        default_factory=list, description="Liste des sous-catégories"
    )


# Pour le typage récursif
CategoryTreeItem.model_rebuild()


class CategoryListResponse(BaseModel):
    """Schéma de réponse pour une liste de catégories."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    CategoryResponse.model_config["json_schema_extra"]["example"]
                ],
                "total": 1,
                "page": 1,
                "page_size": 10,
                "total_pages": 1,
            }
        }
    )

    items: List[CategoryResponse] = Field(..., description="Liste des catégories")
    total: int = Field(..., description="Nombre total de catégories")
    page: int = Field(1, description="Numéro de page actuelle")
    page_size: int = Field(10, description="Nombre de résultats par page")
    total_pages: int = Field(..., description="Nombre total de pages")
