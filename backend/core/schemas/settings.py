"""
Schémas Pydantic pour la gestion des paramètres utilisateur.

Ce module contient les schémas utilisés pour valider les requêtes et réponses
des opérations liées aux paramètres utilisateur.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, constr, field_validator


class Language(str, Enum):
    """Langues supportées par l'application."""

    FRENCH = "fr"
    ENGLISH = "en"
    SPANISH = "es"
    GERMAN = "de"


class DateFormat(str, Enum):
    """Formats de date supportés."""

    DD_MM_YYYY = "DD/MM/YYYY"
    MM_DD_YYYY = "MM/DD/YYYY"
    ISO_8601 = "YYYY-MM-DD"


class Theme(str, Enum):
    """Thèmes d'interface supportés."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class SettingsBase(BaseModel):
    """Schéma de base pour les paramètres utilisateur."""

    language: Language = Field(
        default=Language.FRENCH, description="Langue de l'interface utilisateur"
    )
    currency: constr(pattern=r"^[A-Z]{3}$") = Field(
        default="EUR", description="Devise par défaut (code ISO 4217 à 3 lettres)"
    )
    date_format: DateFormat = Field(
        default=DateFormat.DD_MM_YYYY, description="Format de date préféré"
    )
    time_zone: str = Field(
        default="Europe/Paris", description="Fuseau horaire (format IANA Time Zone)"
    )
    theme: Theme = Field(default=Theme.LIGHT, description="Thème d'affichage préféré")
    notifications_enabled: bool = Field(
        default=True, description="Activer/désactiver toutes les notifications"
    )
    email_notifications: bool = Field(
        default=True, description="Activer/désactiver les notifications par email"
    )
    push_notifications: bool = Field(
        default=True, description="Activer/désactiver les notifications push"
    )
    monthly_report: bool = Field(
        default=True, description="Recevoir un rapport mensuel par email"
    )
    weekly_summary: bool = Field(
        default=False, description="Recevoir un résumé hebdomadaire"
    )
    budget_alerts: bool = Field(
        default=True, description="Activer les alertes de budget"
    )
    budget_alert_threshold: int = Field(
        default=90,
        ge=1,
        le=100,
        description="Seuil d'alerte de budget en pourcentage (1-100)",
    )
    default_account_id: Optional[int] = Field(
        None,
        gt=0,
        description="ID du compte par défaut pour les nouvelles transactions",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Métadonnées supplémentaires"
    )


class SettingsCreate(SettingsBase):
    """Schéma pour la création de nouveaux paramètres utilisateur."""

    user_id: int = Field(..., gt=0, description="ID de l'utilisateur associé")


class SettingsUpdate(BaseModel):
    """Schéma pour la mise à jour partielle des paramètres utilisateur."""

    language: Optional[Language] = None
    currency: Optional[constr(pattern=r"^[A-Z]{3}$")] = None
    date_format: Optional[DateFormat] = None
    time_zone: Optional[str] = None
    theme: Optional[Theme] = None
    notifications_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    monthly_report: Optional[bool] = None
    weekly_summary: Optional[bool] = None
    budget_alerts: Optional[bool] = None
    budget_alert_threshold: Optional[int] = Field(None, ge=1, le=100)
    default_account_id: Optional[int] = Field(None, gt=0)
    metadata: Optional[Dict[str, Any]] = None


class SettingsResponse(SettingsBase):
    """Schéma pour la réponse des paramètres utilisateur."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "user_id": 1,
                "language": "fr",
                "currency": "EUR",
                "date_format": "DD/MM/YYYY",
                "time_zone": "Europe/Paris",
                "theme": "light",
                "notifications_enabled": True,
                "email_notifications": True,
                "push_notifications": True,
                "monthly_report": True,
                "weekly_summary": False,
                "budget_alerts": True,
                "budget_alert_threshold": 90,
                "default_account_id": None,
                "created_at": "2023-01-15T14:30:00Z",
                "updated_at": "2023-01-15T14:30:00Z",
            }
        },
    )

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class SettingsListResponse(BaseModel):
    """Schéma pour la réponse de la liste des paramètres avec pagination."""

    items: list[SettingsResponse]
    total: int
    pages: int
    current_page: int
    per_page: int


class SettingsFilter(BaseModel):
    """Schéma pour le filtrage des paramètres utilisateur."""

    model_config = ConfigDict(use_enum_values=True)

    language: Optional[Language] = None
    theme: Optional[Theme] = None
    notifications_enabled: Optional[bool] = None
    date_format: Optional[DateFormat] = None


class SettingsBulkUpdate(BaseModel):
    """Schéma pour la mise à jour groupée de paramètres."""

    user_ids: list[int] = Field(
        ..., min_length=1, description="Liste des IDs des utilisateurs à mettre à jour"
    )
    settings: SettingsUpdate = Field(..., description="Paramètres à appliquer")

    @field_validator("user_ids")
    def validate_user_ids(cls, v):
        """Valide que la liste des IDs n'est pas vide."""
        if not v:
            raise ValueError("La liste des IDs d'utilisateurs ne peut pas être vide")
        return v
