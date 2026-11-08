"""
Commandes CLI pour les comptes.

Usage:
    flask accounts check-balances         - Liste les soldes incohérents
    flask accounts check-balances --fix   - Les ramène au solde attendu
    flask accounts purge-deleted          - Purge les comptes à supprimer (J+7)
"""

import click
from flask.cli import AppGroup

accounts_cli = AppGroup("accounts", help="Gestion des comptes bancaires")


@accounts_cli.command("purge-deleted")
def purge_deleted():
    """Supprime définitivement les comptes dont la suppression est échue."""
    from core.services.user.account_deletion import purger_comptes_a_supprimer

    click.echo(f"{purger_comptes_a_supprimer()} compte(s) supprimé(s).")


@accounts_cli.command("check-balances")
@click.option("--fix", is_flag=True, help="Corrige les soldes incohérents.")
def check_balances(fix):
    """Vérifie que chaque solde = solde initial + transactions."""
    from core.services.accounts.balance_check import (
        corriger_soldes,
        soldes_incoherents,
    )

    incoherents = soldes_incoherents()
    if not incoherents:
        click.echo("Tous les soldes sont cohérents.")
        return

    click.echo(f"{len(incoherents)} compte(s) incohérent(s) :")
    for s in incoherents:
        click.echo(
            f"  compte {s['account_id']} '{s['name']}' (utilisateur {s['user_id']}) : "
            f"solde {s['balance']}, attendu {s['expected_balance']} (écart {s['ecart']})"
        )

    if fix:
        corriger_soldes()
        click.echo("Soldes corrigés.")
    else:
        click.echo("Relancer avec --fix pour les corriger.")
        raise SystemExit(1)
