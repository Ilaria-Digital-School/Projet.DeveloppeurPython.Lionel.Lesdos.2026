"""
Module de gestion des transactions financières.

Ce module fournit les fonctionnalités de gestion des transactions financières,
incluant la création, modification, suppression et consultation des transactions.

Architecture:
- Présentation: Routes Flask et formulaires WTForms pour l'interface utilisateur
- Logique métier: Services centralisés dans core.services.transactions
- Données: Modèles SQLAlchemy dans core.models.transactions

Conventions:
- Tous les imports utilisent des chemins absolus depuis 'core'
- La logique métier est déléguée aux services métier
- Gestion d'erreurs standardisée via backend.app.utils.errors
- Logging configuré pour chaque module
"""

import logging

from flask import Blueprint

# Imports pour gestion d'erreurs standardisée
from app.utils.errors import ValidationError, handle_api_error

# Imports depuis core pour cohérence architecturale
from core.extensions import db
from core.models.transactions import Transaction, TransactionType
from core.services.transactions import TransactionService

# Configuration du logger pour ce module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Création du blueprint pour les routes web
web_bp = Blueprint(
    "transactions", __name__, template_folder="templates", static_folder="static"
)

# Import des routes après la création du blueprint pour éviter les imports circulaires
from . import transaction_routes


# Commandes CLI pour les transactions
def transactions_cli():
    """Commandes CLI pour la gestion des transactions."""
    import click

    @click.group()
    def transactions():
        """Commandes de gestion des transactions financières."""

    @transactions.command()
    @click.argument("user_id", type=int)
    def summary(user_id):
        """Affiche un résumé des transactions d'un utilisateur."""
        try:
            service = TransactionService()
            result = service.get_transaction_summary(user_id)
            click.echo(
                f"Résumé des transactions pour l'utilisateur {user_id}: {result}"
            )
        except Exception as e:
            logger.error(
                f"Erreur lors de la génération du résumé pour l'utilisateur {user_id}: {e}"
            )
            click.echo(f"Erreur: {e}", err=True)

    return transactions


def init_app(app):
    """
    Initialise le module transactions avec l'application Flask.

    Args:
        app: Instance de l'application Flask
    """
    logger.info("Initialisation du module transactions")

    # Enregistrement du blueprint
    app.register_blueprint(web_bp)
    logger.info("Blueprint transactions enregistré")

    # Enregistrement des commandes CLI
    if app.config.get("ENABLE_CLI_COMMANDS", True):
        app.cli.add_command(transactions_cli())
        logger.info("Commandes CLI transactions enregistrées")


# Export des composants principaux
__all__ = [
    "web_bp",
    "transactions_cli",
    "Transaction",
    "TransactionType",
    "TransactionService",
    "handle_api_error",
    "ValidationError",
    "logger",
    "init_app",
]
