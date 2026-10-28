"""
Module pour la gestion des comptes bancaires de l'application.

Ce module contient les formulaires et les routes web pour la gestion des comptes bancaires.
Les modèles et services sont centralisés dans backend/core/.

Architecture :
- Formulaires WTForms : Validation et rendu des formulaires HTML
- Routes web Flask : Interface utilisateur pour la gestion des comptes
- Modèles : Importés depuis core/models/account.py
- Services métier : Importés depuis core/services/accounts/

Fonctionnalités principales :
- Interface web pour la création, modification et suppression de comptes
- Formulaires de validation avec support IBAN/BIC
- Intégration avec les services métier centralisés
- Gestion d'erreurs standardisée
"""

import logging

# Configuration du logger
logger = logging.getLogger(__name__)

# Import des éléments principaux pour faciliter l'accès
try:
    # Modèle principal - importé depuis le core
    from core.models.account import Account

    # Formulaires
    from .account_forms import (
        AddAccountForm,
        EditAccountForm,
        validate_bic,
        validate_iban,
    )

    # Routes - version complète
    from .account_routes import accounts_bp

    # Version du module
    __version__ = "1.0.0"

    # Export des éléments principaux

    __all__ = [
        # Modèles
        "Account",
        # Formulaires
        "AddAccountForm",
        "EditAccountForm",
        "validate_iban",
        "validate_bic",
        # Routes (uniquement le blueprint web)
        "accounts_bp",
    ]

except ImportError as e:
    logger.error(f"Erreur lors de l'import des modules accounts: {e}", exc_info=True)
    raise
