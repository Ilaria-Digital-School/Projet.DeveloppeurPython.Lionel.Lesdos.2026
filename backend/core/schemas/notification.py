"""
Schémas Pydantic pour la gestion des notifications.

Ce module contient les schémas utilisés pour valider les requêtes et réponses
des opérations liées aux notifications.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
)


class NotificationType(str, Enum):
    """Types de notifications disponibles."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class NotificationBase(BaseModel):
    """Schéma de base pour une notification."""

    title: str = Field(..., max_length=200, description="Titre de la notification")
    message: str = Field(..., description="Contenu du message de la notification")
    type: NotificationType = Field(..., description="Type de notification")
    action_url: Optional[HttpUrl] = Field(
        None, description="URL d'action associée à la notification (optionnel)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Métadonnées supplémentaires au format JSON (optionnel)",
    )


class NotificationCreate(NotificationBase):
    """Schéma pour la création d'une nouvelle notification."""

    user_id: int = Field(..., gt=0, description="ID de l'utilisateur destinataire")
    is_read: bool = Field(
        default=False, description="Définit si la notification est marquée comme lue"
    )


class NotificationUpdate(BaseModel):
    """Schéma pour la mise à jour d'une notification existante."""

    is_read: Optional[bool] = Field(
        None, description="Définit si la notification est marquée comme lue"
    )


class NotificationResponse(NotificationBase):
    """Schéma pour la réponse d'une notification."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Mise à jour disponible",
                "message": "Une nouvelle version de l'application est disponible.",
                "type": "info",
                "is_read": False,
                "created_at": "2023-01-15T14:30:00Z",
                "read_at": None,
                "action_url": "https://example.com/update",
                "metadata": {"version": "1.2.0"},
            }
        },
    )

    id: int
    user_id: int
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime]


class NotificationListResponse(BaseModel):
    """Schéma pour la réponse de la liste des notifications avec pagination."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": 1,
                        "title": "Bienvenue",
                        "message": "Bienvenue sur notre plateforme!",
                        "type": "info",
                        "is_read": True,
                        "created_at": "2023-01-10T09:15:00Z",
                        "read_at": "2023-01-10T10:30:00Z",
                        "action_url": "/dashboard",
                        "metadata": {},
                    },
                    {
                        "id": 2,
                        "title": "Mise à jour des CGU",
                        "message": "Nos conditions générales ont été mises à jour.",
                        "type": "warning",
                        "is_read": False,
                        "created_at": "2023-01-15T14:30:00Z",
                        "read_at": None,
                        "action_url": "/legal/terms",
                        "metadata": {"version": "2.0"},
                    },
                ],
                "total": 2,
                "pages": 1,
                "current_page": 1,
                "per_page": 20,
                "unread_count": 1,
            }
        }
    )

    items: List[NotificationResponse]
    total: int
    pages: int
    current_page: int
    per_page: int
    unread_count: int = Field(..., description="Nombre total de notifications non lues")
