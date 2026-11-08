"""Add ComptesBancaires.solde_initial and normalize account-import transactions

solde_initial permet de verifier (flask accounts check-balances) que
solde_actuel = solde_initial + effet des transactions 'completed'.

1. Transactions creees par l'import de releve (POST /api/v1/comptes/import) :
   montant negatif pour les depenses et statut 'confirmee', alors que toute
   l'appli attend un montant positif et 'completed' (la suppression ne
   reajustait pas le solde, les rapports sommaient des montants de signes
   melanges). Leur effet etant deja dans solde_actuel, les normaliser ne
   change aucun solde.
2. solde_initial des comptes existants = solde_actuel - effet des
   transactions : le solde actuel sert de point de depart (l'historique ne
   permet pas de savoir s'il etait juste) ; tout ecart ulterieur sera detecte.

Les listes de types sont figees ici (TransactionType au 2026-10-28).

Revision ID: add_solde_initial_01
Revises: align_schema_models_01
Create Date: 2026-10-28

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_solde_initial_01"
down_revision = "align_schema_models_01"
branch_labels = None
depends_on = None

DEPENSES = "('achat', 'expense', 'loyer', 'facture', 'abonnement', 'prelevement', 'ACHAT')"
REVENUS = "('salaire', 'revenu_autre', 'remboursement', 'income', 'SALAIRE')"
VIREMENTS = "('virement', 'transfer')"


def upgrade():
    op.execute(
        "UPDATE transactions SET montant = abs(montant), statut = 'completed' "
        "WHERE statut = 'confirmee'"
    )

    op.add_column(
        "ComptesBancaires",
        sa.Column(
            "solde_initial",
            sa.Numeric(precision=12, scale=2),
            server_default="0",
            nullable=False,
        ),
    )

    op.execute(f"""
        WITH effets AS (
            SELECT account_id AS compte,
                CASE
                    WHEN type_transaction IN {DEPENSES}
                        THEN -(montant + COALESCE(frais_transaction, 0))
                    WHEN type_transaction IN {REVENUS}
                        THEN montant - COALESCE(frais_transaction, 0)
                    WHEN type_transaction IN {VIREMENTS}
                         AND destination_account_id IS NOT NULL
                         AND destination_account_id <> account_id
                        THEN -(montant + COALESCE(frais_transaction, 0))
                    ELSE 0
                END AS delta
            FROM transactions WHERE statut = 'completed'
            UNION ALL
            SELECT destination_account_id, montant
            FROM transactions
            WHERE statut = 'completed' AND type_transaction IN {VIREMENTS}
              AND destination_account_id IS NOT NULL
              AND destination_account_id <> account_id
        ),
        totaux AS (SELECT compte, SUM(delta) AS total FROM effets GROUP BY compte)
        UPDATE "ComptesBancaires" c
        SET solde_initial = c.solde_actuel - COALESCE(t.total, 0)
        FROM "ComptesBancaires" c2
        LEFT JOIN totaux t ON t.compte = c2.id_compte
        WHERE c.id_compte = c2.id_compte
    """)


def downgrade():
    # La normalisation des transactions importees n'est pas annulee : elle ne
    # change aucun solde et l'ancien format etait incoherent.
    op.drop_column("ComptesBancaires", "solde_initial")
