"""
Commandes CLI pour les transactions récurrentes.

Usage:
    flask recurring process   - Traite les transactions récurrentes dues
"""

import click
from flask.cli import AppGroup

recurring_cli = AppGroup("recurring", help="Gestion des transactions récurrentes")


@recurring_cli.command("process")
def process_recurring():
    """Traite toutes les transactions récurrentes dues."""
    from core.services.recurring import RecurringTransactionService

    click.echo("Traitement des transactions récurrentes...")
    count = RecurringTransactionService.process_due_transactions()
    click.echo(f"Terminé : {count} transaction(s) créée(s).")
