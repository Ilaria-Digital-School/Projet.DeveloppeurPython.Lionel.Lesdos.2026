"""
Module utilitaires pour l'application Appli_Web_Budget.

Ce module fournit des utilitaires transversaux utilisés dans l'application :
- forms_utils : Utilitaires pour les formulaires WTForms
- email_utils : Utilitaires pour les notifications et emails
"""

from .forms_utils import get_budget_form

__all__ = [
    # Form utilities
    "get_budget_form"
]
