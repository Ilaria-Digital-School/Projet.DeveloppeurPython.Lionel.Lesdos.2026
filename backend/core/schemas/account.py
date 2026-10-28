"""
Schémas de validation pour le module accounts.

Ce module définit les modèles Pydantic pour la validation des données
d'entrée et de sortie des API du module accounts.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    constr,
    field_validator,
)

# Types personnalisés
AccountType = Literal[
    "checking", "savings", "credit_card", "cash", "investment", "loan", "other"
]
CurrencyCode = Literal["EUR", "USD", "GBP", "JPY", "CHF", "CAD", "AUD"]


class AccountBase(BaseModel):
    """Schéma de base pour un compte bancaire."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Compte Courant Principal",
                "account_type": "checking",
                "currency": "EUR",
                "is_active": True,
                "notes": "Compte courant principal pour les dépenses courantes",
            }
        }
    )

    name: constr(min_length=1, max_length=100) = Field(
        ..., description="Nom personnalisé du compte"
    )
    account_type: AccountType = Field(
        ..., description="Type de compte (checking, savings, etc.)"
    )
    currency: CurrencyCode = Field(
        "EUR", description="Code devise ISO 4217 (3 lettres)"
    )
    is_active: bool = Field(True, description="Indique si le compte est actif")
    notes: Optional[constr(max_length=1000)] = Field(
        None, description="Notes ou description optionnelle"
    )


class AccountCreate(AccountBase):
    """Schéma pour la création d'un compte."""

    initial_balance: Decimal = Field(
        Decimal("0.00"), ge=0, description="Solde initial du compte (toujours positif)"
    )
    bank_name: Optional[constr(max_length=100)] = Field(
        None, description="Nom de l'institution bancaire"
    )
    account_number: Optional[constr(max_length=34)] = Field(
        None, description="Numéro de compte bancaire"
    )
    iban: Optional[constr(max_length=34)] = Field(
        None, description="Numéro IBAN du compte"
    )
    bic_swift: Optional[constr(max_length=11)] = Field(
        None, description="Code BIC/SWIFT de la banque"
    )

    @field_validator("iban")
    def validate_iban(cls, v):
        if v is None:
            return v

        # Nettoyer l'IBAN
        iban = v.replace(" ", "").upper()

        # Vérifier le format de base
        if not iban.isalnum():
            raise ValueError("L'IBAN ne doit contenir que des lettres et des chiffres")

        if len(iban) < 15 or len(iban) > 34:
            raise ValueError("L'IBAN doit contenir entre 15 et 34 caractères")

        # Vérifier le code pays (2 premières lettres)
        if not iban[:2].isalpha():
            raise ValueError("L'IBAN doit commencer par un code pays à 2 lettres")

        # Vérifier la clé de contrôle (2 chiffres suivants)
        if not iban[2:4].isdigit():
            raise ValueError(
                "L'IBAN doit contenir une clé de contrôle à 2 chiffres après le code pays"
            )

        return iban

    @field_validator("bic_swift")
    def validate_bic_swift(cls, v):
        if v is None:
            return v

        # Nettoyer le BIC/SWIFT
        bic = v.replace(" ", "").upper()

        # Vérifier le format
        if not (8 <= len(bic) <= 11):
            raise ValueError("Le code BIC/SWIFT doit contenir entre 8 et 11 caractères")

        # Vérifier le format du code de la banque (4 lettres)
        if not bic[:4].isalpha():
            raise ValueError("Le code BIC/SWIFT doit commencer par 4 lettres")

        # Vérifier le code pays (2 lettres suivantes)
        if not bic[4:6].isalpha():
            raise ValueError(
                "Le code BIC/SWIFT doit contenir un code pays à 2 lettres après le code banque"
            )

        # Vérifier l'emplacement (2 caractères suivants, lettres ou chiffres)
        if not bic[6:8].isalnum():
            raise ValueError(
                "L'emplacement du BIC/SWIFT doit contenir 2 caractères alphanumériques"
            )

        # Vérifier le code filiale optionnel (3 caractères, lettres ou chiffres)
        if len(bic) > 8 and not bic[8:].isalnum():
            raise ValueError("Le code filiale du BIC/SWIFT doit être alphanumérique")

        return bic


class AccountUpdate(AccountBase):
    """Schéma pour la mise à jour d'un compte."""

    name: Optional[constr(min_length=1, max_length=100)] = None
    account_type: Optional[AccountType] = None
    currency: Optional[CurrencyCode] = None
    is_active: Optional[bool] = None

    # Champs bancaires pour les modifications (mêmes que AccountCreate)
    bank_name: Optional[constr(max_length=100)] = Field(
        None, description="Nom de l'institution bancaire"
    )
    account_number: Optional[constr(max_length=34)] = Field(
        None, description="Numéro de compte bancaire"
    )
    iban: Optional[constr(max_length=34)] = Field(
        None, description="Numéro IBAN du compte"
    )
    bic_swift: Optional[constr(max_length=11)] = Field(
        None, description="Code BIC/SWIFT de la banque"
    )
    balance: Optional[Decimal] = Field(
        None, ge=0, description="Nouveau solde du compte"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Nouveau nom du compte",
                "bank_name": "Nouvelle banque",
                "account_number": "123456789",
                "iban": "FR76 1234 5678 9012 3456 7890 123",
                "is_active": False,
            }
        }
    )


class AccountResponse(AccountBase):
    """Schéma de réponse pour un compte."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Compte Courant Principal",
                "account_type": "checking",
                "currency": "EUR",
                "current_balance": 1500.75,
                "is_active": True,
                "notes": "Compte courant principal",
                "created_at": "2023-01-15T10:30:00",
                "updated_at": "2023-06-20T14:45:00",
            }
        },
    )

    id: int = Field(..., description="Identifiant unique du compte")
    current_balance: Decimal = Field(..., description="Solde actuel du compte")
    created_at: datetime = Field(..., description="Date de création du compte")
    updated_at: datetime = Field(..., description="Dernière mise à jour du compte")


class AccountBalanceUpdate(BaseModel):
    """Schéma pour la mise à jour du solde d'un compte."""

    new_balance: Decimal = Field(
        ..., gt=0, description="Nouveau solde du compte (doit être positif)"
    )
    notes: Optional[constr(max_length=500)] = Field(
        None, description="Notes sur la raison de la mise à jour du solde"
    )


class AccountTransfer(BaseModel):
    """Schéma pour un transfert entre comptes."""

    source_account_id: int = Field(..., description="ID du compte source")
    destination_account_id: int = Field(..., description="ID du compte de destination")
    amount: Decimal = Field(
        ..., gt=0, description="Montant à transférer (toujours positif)"
    )
    currency: CurrencyCode = Field(
        "EUR",
        description="Devise du transfert (doit correspondre à la devise du compte source)",
    )
    description: Optional[constr(max_length=200)] = Field(
        None, description="Description du transfert"
    )

    @field_validator("destination_account_id")
    def validate_different_accounts(cls, v, info: ValidationInfo):
        """Valide que les comptes source et de destination sont différents."""
        source_id = info.data.get("source_account_id")
        if source_id is not None and v == source_id:
            raise ValueError(
                "Le compte source et le compte de destination doivent être différents"
            )
        return v


class AccountListResponse(BaseModel):
    """Schéma de réponse pour une liste de comptes."""

    accounts: List[AccountResponse]
    total: int = Field(..., description="Nombre total de comptes")
    page: int = Field(1, description="Numéro de page actuelle")
    page_size: int = Field(10, description="Nombre de résultats par page")
    total_pages: int = Field(..., description="Nombre total de pages")
