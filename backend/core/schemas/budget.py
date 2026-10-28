"""
Schémas Pydantic pour la validation des données des budgets.
"""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class BudgetPeriod(str, Enum):
    """Énumération des périodes de budget possibles."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class BudgetBase(BaseModel):
    """Schéma de base pour un budget."""

    name: str = Field(..., min_length=1, max_length=100, description="Nom du budget")
    category_id: int = Field(..., gt=0, description="ID de la catégorie associée")
    amount: float = Field(..., gt=0, description="Montant du budget")
    period: BudgetPeriod = Field(..., description="Période du budget")
    start_date: date = Field(..., description="Date de début du budget")
    end_date: Optional[date] = Field(
        None, description="Date de fin (requise si period='custom')"
    )
    notification_threshold: int = Field(
        default=90,
        ge=1,
        le=100,
        description="Seuil de notification en pourcentage (1-100)",
    )
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Notes supplémentaires sur le budget (500 caractères max)",
    )

    @field_validator("end_date")
    def validate_end_date(cls, v, info: ValidationInfo):
        """Valide que la date de fin est postérieure à la date de début si period='custom'."""
        if info.data.get("period") == "custom" and v is None:
            raise ValueError("end_date est requis lorsque period='custom'")

        start_date = info.data.get("start_date")
        if start_date is not None and v is not None and v <= start_date:
            raise ValueError("La date de fin doit être postérieure à la date de début")

        return v


class BudgetCreate(BudgetBase):
    """Schéma pour la création d'un nouveau budget."""


class BudgetUpdate(BaseModel):
    """Schéma pour la mise à jour d'un budget existant."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Nouveau nom du budget"
    )
    category_id: Optional[int] = Field(None, gt=0, description="Nouvel ID de catégorie")
    amount: Optional[float] = Field(None, gt=0, description="Nouveau montant du budget")
    period: Optional[BudgetPeriod] = Field(
        None, description="Nouvelle période du budget"
    )
    start_date: Optional[date] = Field(None, description="Nouvelle date de début")
    end_date: Optional[date] = Field(None, description="Nouvelle date de fin")
    notification_threshold: Optional[int] = Field(
        None, ge=1, le=100, description="Nouveau seuil de notification en pourcentage"
    )
    notes: Optional[str] = Field(
        None, max_length=500, description="Nouvelles notes (500 caractères max)"
    )


class BudgetResponse(BudgetBase):
    """Schéma pour la réponse d'un budget."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class BudgetListResponse(BaseModel):
    """Schéma pour la réponse de la liste des budgets avec pagination."""

    items: List[BudgetResponse]
    total: int
    pages: int
    current_page: int
    per_page: int
