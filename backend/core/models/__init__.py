"""
Modèles de données de l'application.

Ce package contient tous les modèles de données de l'application.
"""

from .account import *
from .associations import user_roles
from .budget import Budget

# Formulaires déplacés vers modules/budgets/forms/
from .budget_history import BudgetHistory
from .category import *
from .device import *
from .email import *
from .import_export import *
from .notification import *
from .notification_preference import *
from .permission import Permission
from .recurring_transaction import RecurringTransaction
from .report import *
from .role import Role, role_permissions
from .security_event import SecurityEvent
from .session import UserSession
from .setting import *
from .token_blacklist import TokenBlacklist
from .transactions import *

# Cette importation est nécessaire pour que SQLAlchemy puisse découvrir les modèles
# Ne pas supprimer ces imports même s'ils semblent inutilisés
from .user import User

# Export explicite de tous les modèles disponibles
__all__ = [
    # Core models
    "User",
    "Role",
    "Permission",
    "role_permissions",
    "user_roles",
    # Business models
    "Account",
    "Budget",
    "BudgetHistory",
    "Category",
    "Transaction",
    # System models
    "Device",
    "DeviceLoginHistory",
    "Email",
    "EmailTemplate",
    "Notification",
    "NotificationPreference",
    "Report",
    "Setting",
    "UserSetting",
    # Recurring transactions
    "RecurringTransaction",
    # Import/Export models
    "ImportJob",
    "ExportJob",
    # Security models
    "SecurityEvent",
    "Session",
]
