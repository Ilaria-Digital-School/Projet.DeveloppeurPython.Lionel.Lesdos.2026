"""
Schémas de validation pour les transactions financières.

Ce module définit les modèles Pydantic pour la validation des données
des transactions financières (dépenses, revenus, transferts).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

# Types personnalisés
TransactionType = Literal["income", "expense", "transfer"]
TransactionStatus = Literal["pending", "cleared", "reconciled", "void"]


class TransactionBase(BaseModel):
    """Schéma de base pour une transaction."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "amount": 99.99,
                "transaction_date": "2023-01-15",
                "description": "Course chez l'épicier",
                "notes": "Courses de la semaine",
                "status": "cleared",
            }
        }
    )

    amount: Decimal = Field(
        ..., gt=0, description="Montant de la transaction (toujours positif)"
    )
    transaction_date: date = Field(
        default_factory=date.today,
        description="Date de la transaction (par défaut: aujourd'hui)",
    )
    description: str = Field(
        ..., max_length=200, description="Description de la transaction"
    )
    notes: Optional[str] = Field(
        None, max_length=1000, description="Notes supplémentaires sur la transaction"
    )
    status: TransactionStatus = Field("cleared", description="Statut de la transaction")


class TransactionCreate(TransactionBase):
    """Schéma pour la création d'une transaction."""

    model_config = ConfigDict(
        json_schema_extra={
            **TransactionBase.model_config["json_schema_extra"]["example"],
            "account_id": 1,
            "category_id": 5,
            "transaction_type": "expense",
        }
    )

    account_id: int = Field(..., description="ID du compte associé à la transaction")
    category_id: Optional[int] = Field(
        None, description="ID de la catégorie de la transaction"
    )
    payee_id: Optional[int] = Field(
        None, description="ID du bénéficiaire (payee) de la transaction"
    )
    transaction_type: TransactionType = Field(
        ..., description="Type de transaction (income, expense, transfer)"
    )
    # Pour les transferts uniquement
    destination_account_id: Optional[int] = Field(
        None, description="ID du compte de destination (uniquement pour les transferts)"
    )

    @field_validator("destination_account_id")
    def validate_transfer_accounts(cls, v, info: ValidationInfo):
        """Valide que pour un transfert, le compte de destination est spécifié et différent du compte source."""
        if info.data.get("transaction_type") == "transfer":
            if v is None:
                raise ValueError(
                    "Le compte de destination est requis pour un transfert"
                )
            account_id = info.data.get("account_id")
            if account_id is not None and v == account_id:
                raise ValueError(
                    "Le compte source et le compte de destination doivent être différents"
                )
        return v


class TransactionUpdate(BaseModel):
    """Schéma pour la mise à jour d'une transaction."""

    amount: Optional[Decimal] = Field(
        None, gt=0, description="Nouveau montant de la transaction"
    )
    transaction_date: Optional[date] = Field(
        None, description="Nouvelle date de la transaction"
    )
    description: Optional[str] = Field(
        None, max_length=200, description="Nouvelle description"
    )
    notes: Optional[str] = Field(None, max_length=1000, description="Nouvelles notes")
    status: Optional[TransactionStatus] = Field(None, description="Nouveau statut")
    category_id: Optional[int] = Field(None, description="Nouvelle catégorie")
    payee_id: Optional[int] = Field(None, description="Nouveau bénéficiaire")


class TransactionResponse(TransactionBase):
    """Schéma de réponse pour une transaction."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                **TransactionBase.model_config["json_schema_extra"]["example"],
                "id": 1,
                "account_id": 1,
                "category_id": 5,
                "transaction_type": "expense",
                "created_at": "2023-01-15T14:30:00",
                "updated_at": "2023-01-15T14:30:00",
            }
        },
    )

    id: int = Field(..., description="ID unique de la transaction")
    account_id: int = Field(..., description="ID du compte associé")
    category_id: Optional[int] = Field(None, description="ID de la catégorie")
    payee_id: Optional[int] = Field(None, description="ID du bénéficiaire")
    transaction_type: TransactionType = Field(..., description="Type de transaction")
    destination_account_id: Optional[int] = Field(
        None, description="ID du compte de destination (pour les transferts)"
    )
    created_at: datetime = Field(..., description="Date de création")
    updated_at: datetime = Field(..., description="Dernière mise à jour")


class TransactionListResponse(BaseModel):
    """Schéma de réponse pour une liste de transactions."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    TransactionResponse.model_config["json_schema_extra"]["example"]
                ],
                "total": 1,
                "page": 1,
                "page_size": 10,
                "total_pages": 1,
            }
        }
    )

    items: List[TransactionResponse] = Field(..., description="Liste des transactions")
    total: int = Field(..., description="Nombre total de transactions")
    page: int = Field(1, description="Numéro de page actuelle")
    page_size: int = Field(10, description="Nombre de résultats par page")
    total_pages: int = Field(..., description="Nombre total de pages")


class TransactionFilter(BaseModel):
    """Filtres pour la recherche de transactions."""

    start_date: Optional[date] = Field(
        None, description="Date de début pour filtrer les transactions"
    )
    end_date: Optional[date] = Field(
        None, description="Date de fin pour filtrer les transactions"
    )
    min_amount: Optional[Decimal] = Field(
        None, gt=0, description="Montant minimum des transactions"
    )
    max_amount: Optional[Decimal] = Field(
        None, gt=0, description="Montant maximum des transactions"
    )
    transaction_type: Optional[TransactionType] = Field(
        None, description="Type de transaction à filtrer"
    )
    status: Optional[TransactionStatus] = Field(
        None, description="Statut des transactions à filtrer"
    )
    category_id: Optional[int] = Field(
        None, description="ID de la catégorie pour filtrer les transactions"
    )
    account_id: Optional[int] = Field(
        None, description="ID du compte pour filtrer les transactions"
    )
    description: Optional[str] = Field(
        None, description="Terme de recherche dans la description"
    )


class TransactionSummary(BaseModel):
    """Résumé des transactions pour une période donnée."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_income": 2500.00,
                "total_expenses": 1500.00,
                "net_balance": 1000.00,
                "start_date": "2023-01-01",
                "end_date": "2023-01-31",
                "by_category": [
                    {
                        "category_id": 1,
                        "name": "Nourriture",
                        "amount": 500.00,
                        "type": "expense",
                    },
                    {
                        "category_id": 2,
                        "name": "Salaire",
                        "amount": 2500.00,
                        "type": "income",
                    },
                ],
                "by_account": [
                    {"account_id": 1, "name": "Compte Courant", "balance": 1000.00}
                ],
            }
        }
    )

    total_income: Decimal = Field(
        Decimal("0.00"), description="Total des revenus pour la période"
    )
    total_expenses: Decimal = Field(
        Decimal("0.00"), description="Total des dépenses pour la période"
    )
    net_balance: Decimal = Field(
        Decimal("0.00"), description="Solde net (revenus - dépenses) pour la période"
    )
    start_date: Optional[date] = Field(None, description="Date de début de la période")
    end_date: Optional[date] = Field(None, description="Date de fin de la période")
    by_category: List[dict] = Field(
        default_factory=list, description="Récapitulatif par catégorie"
    )
    by_account: List[dict] = Field(
        default_factory=list, description="Récapitulatif par compte"
    )
