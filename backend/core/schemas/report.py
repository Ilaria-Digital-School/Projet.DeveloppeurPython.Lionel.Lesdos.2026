"""
Schémas de validation pour les rapports.

Ce module définit les modèles Pydantic pour la validation des données
des rapports et des demandes de génération de rapports.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
)


# Types personnalisés
class ReportFormat(str, Enum):
    """Formats de sortie disponibles pour les rapports."""

    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"


class ReportType(str, Enum):
    """Types de rapports disponibles."""

    TRANSACTION_SUMMARY = "transaction_summary"
    INCOME_VS_EXPENSE = "income_vs_expense"
    CATEGORY_SPENDING = "category_spending"
    ACCOUNT_BALANCE = "account_balance"
    TAX = "tax"
    CUSTOM = "custom"


class ReportFrequency(str, Enum):
    """Fréquence des rapports récurrents."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class ReportBase(BaseModel):
    """Schéma de base pour un rapport."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Rapport mensuel des dépenses",
                "description": "Rapport détaillé des dépenses et revenus du mois",
                "report_type": "income_vs_expense",
                "format": "pdf",
                "is_recurring": True,
                "frequency": "monthly",
                "start_date": "2023-01-01",
                "end_date": "2023-01-31",
                "parameters": {"include_charts": True, "group_by": "category"},
            }
        }
    )

    name: str = Field(..., max_length=100, description="Nom du rapport")
    description: Optional[str] = Field(
        None, max_length=500, description="Description du rapport"
    )
    report_type: ReportType = Field(..., description="Type de rapport à générer")
    format: ReportFormat = Field(
        ReportFormat.PDF, description="Format de sortie du rapport"
    )
    is_recurring: bool = Field(False, description="Indique si le rapport est récurrent")
    frequency: Optional[ReportFrequency] = Field(
        None, description="Fréquence de génération (pour les rapports récurrents)"
    )
    start_date: Optional[date] = Field(
        None, description="Date de début pour la génération du rapport"
    )
    end_date: Optional[date] = Field(
        None, description="Date de fin pour la génération du rapport"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Paramètres spécifiques au type de rapport"
    )

    @field_validator("end_date")
    def validate_dates(cls, v, info: ValidationInfo):
        """Valide que la date de fin est postérieure ou égale à la date de début."""
        start_date = info.data.get("start_date")
        if start_date and v:
            if v < start_date:
                raise ValueError(
                    "La date de fin doit être postérieure ou égale à la date de début"
                )
        return v

    @field_validator("frequency")
    def validate_frequency(cls, v, info: ValidationInfo):
        """Valide que la fréquence est spécifiée pour les rapports récurrents."""
        if info.data.get("is_recurring") and not v:
            raise ValueError(
                "La fréquence est obligatoire pour les rapports récurrents"
            )
        return v


class ReportCreate(ReportBase):
    """Schéma pour la création d'un rapport."""


class ReportUpdate(BaseModel):
    """Schéma pour la mise à jour d'un rapport."""

    name: Optional[str] = Field(
        None, max_length=100, description="Nouveau nom du rapport"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Nouvelle description"
    )
    is_active: Optional[bool] = Field(
        None, description="Activer/désactiver le rapport récurrent"
    )
    frequency: Optional[ReportFrequency] = Field(
        None, description="Nouvelle fréquence de génération"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Nouveaux paramètres du rapport"
    )


class ReportResponse(ReportBase):
    """Schéma de réponse pour un rapport."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                **ReportBase.model_config["json_schema_extra"]["example"],
                "id": 1,
                "created_by": 1,
                "is_active": True,
                "last_generated": "2023-01-31T23:59:59",
                "next_generation": "2023-02-28T23:59:59",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
            }
        },
    )

    id: int = Field(..., description="ID unique du rapport")
    created_by: int = Field(
        ..., description="ID de l'utilisateur ayant créé le rapport"
    )
    is_active: bool = Field(True, description="Indique si le rapport est actif")
    last_generated: Optional[datetime] = Field(
        None, description="Date de dernière génération du rapport"
    )
    next_generation: Optional[datetime] = Field(
        None,
        description="Date de la prochaine génération (pour les rapports récurrents)",
    )
    created_at: datetime = Field(..., description="Date de création du rapport")
    updated_at: datetime = Field(..., description="Date de dernière mise à jour")


class ReportListResponse(BaseModel):
    """Schéma de réponse pour une liste de rapports."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [ReportResponse.model_config["json_schema_extra"]["example"]],
                "total": 1,
                "page": 1,
                "page_size": 10,
                "total_pages": 1,
            }
        }
    )

    items: List[ReportResponse] = Field(..., description="Liste des rapports")
    total: int = Field(..., description="Nombre total de rapports")
    page: int = Field(1, description="Numéro de page actuelle")
    page_size: int = Field(10, description="Nombre de résultats par page")
    total_pages: int = Field(..., description="Nombre total de pages")


class ReportFilter(BaseModel):
    """Filtres pour la recherche de rapports."""

    report_type: Optional[ReportType] = Field(
        None, description="Filtrer par type de rapport"
    )
    is_recurring: Optional[bool] = Field(
        None, description="Filtrer les rapports récurrents"
    )
    is_active: Optional[bool] = Field(
        None, description="Filtrer les rapports actifs/inactifs"
    )
    created_by: Optional[int] = Field(
        None, description="Filtrer par créateur du rapport"
    )
    created_after: Optional[date] = Field(
        None, description="Filtrer les rapports créés après cette date"
    )
    created_before: Optional[date] = Field(
        None, description="Filtrer les rapports créés avant cette date"
    )
    search: Optional[str] = Field(
        None, description="Terme de recherche dans le nom et la description"
    )


class ReportGenerationRequest(BaseModel):
    """Schéma pour une demande de génération de rapport."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "report_type": "income_vs_expense",
                "format": "pdf",
                "start_date": "2023-01-01",
                "end_date": "2023-01-31",
                "parameters": {"include_charts": True, "group_by": "category"},
                "email_notification": True,
                "email_recipients": ["utilisateur@example.com"],
            }
        }
    )

    report_type: ReportType = Field(..., description="Type de rapport à générer")
    format: ReportFormat = Field(
        ReportFormat.PDF, description="Format de sortie du rapport"
    )
    start_date: Optional[date] = Field(
        None, description="Date de début pour le rapport"
    )
    end_date: Optional[date] = Field(None, description="Date de fin pour le rapport")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Paramètres spécifiques au type de rapport"
    )
    email_notification: Optional[bool] = Field(
        False, description="Envoyer le rapport par email une fois généré"
    )
    email_recipients: Optional[List[str]] = Field(
        None,
        description="Liste des adresses email des destinataires (si différent de l'utilisateur courant)",
    )

    @field_validator("end_date")
    def validate_dates(cls, v, info: ValidationInfo):
        """Valide que la date de fin est postérieure ou égale à la date de début."""
        start_date = info.data.get("start_date")
        if start_date and v:
            if v < start_date:
                raise ValueError(
                    "La date de fin doit être postérieure ou égale à la date de début"
                )
        return v

    @field_validator("email_recipients")
    def validate_emails(cls, v):
        """Valide le format des adresses email."""
        if v is None:
            return v
        import re

        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        for email in v:
            if not email_pattern.match(email):
                raise ValueError(f"Adresse email invalide: {email}")
        return v
