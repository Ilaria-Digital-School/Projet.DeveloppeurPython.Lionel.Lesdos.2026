"""
Schémas de validation et de sérialisation.

Ce module expose tous les schémas de validation et de sérialisation
des modèles de l'application.
"""

# Import des schémas de comptes
from .account import (
    AccountBalanceUpdate,
    AccountBase,
    AccountCreate,
    AccountListResponse,
    AccountResponse,
    AccountTransfer,
    AccountUpdate,
)

# Import des schémas de budget
from .budget import (
    BudgetBase,
    BudgetCreate,
    BudgetListResponse,
    BudgetResponse,
    BudgetUpdate,
)

# Import des schémas de catégorie
from .category import (
    CategoryBase,
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
)

# Import des schémas de notification
from .notification import (
    NotificationBase,
    NotificationCreate,
    NotificationListResponse,
    NotificationResponse,
    NotificationUpdate,
)

# Import des schémas de rapport
from .report import ReportBase, ReportCreate, ReportListResponse, ReportResponse

# Import des schémas de paramètres
from .settings import SettingsBase, SettingsResponse, SettingsUpdate

# Import des schémas de transaction
from .transaction import (
    TransactionBase,
    TransactionCreate,
    TransactionFilter,
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdate,
)

# Import des schémas utilisateur (Pydantic)
from .user import (
    PermissionSchema,
    RoleSchema,
    UserBaseSchema,
    UserCreateSchema,
    UserResponseSchema,
    UserUpdateSchema,
)

# Export des symboles
__all__ = [
    # Schémas utilisateur
    "UserBaseSchema",
    "UserCreateSchema",
    "UserUpdateSchema",
    "UserResponseSchema",
    "RoleSchema",
    "PermissionSchema",
    # Schémas de comptes
    "AccountBase",
    "AccountCreate",
    "AccountUpdate",
    "AccountResponse",
    "AccountBalanceUpdate",
    "AccountTransfer",
    "AccountListResponse",
    # Schémas de budget
    "BudgetBase",
    "BudgetCreate",
    "BudgetUpdate",
    "BudgetResponse",
    "BudgetListResponse",
    # Schémas de catégorie
    "CategoryBase",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "CategoryListResponse",
    # Schémas de transaction
    "TransactionBase",
    "TransactionCreate",
    "TransactionUpdate",
    "TransactionResponse",
    "TransactionListResponse",
    "TransactionFilter",
    # Schémas de notification
    "NotificationBase",
    "NotificationCreate",
    "NotificationUpdate",
    "NotificationResponse",
    "NotificationListResponse",
    # Schémas de paramètres
    "SettingsBase",
    "SettingsUpdate",
    "SettingsResponse",
    # Schémas de rapport
    "ReportBase",
    "ReportCreate",
    "ReportResponse",
    "ReportListResponse",
]
