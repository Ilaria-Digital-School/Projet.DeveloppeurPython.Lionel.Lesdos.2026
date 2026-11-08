"""Budgets: report du reste, suppression de spent_amount

- budgets.report_actif : le non-depense de la periode precedente s'ajoute a
  la periode en cours. False par defaut : les budgets existants ne changent pas.
- budgets.spent_amount : jamais mise a jour (le depense est calcule a la volee
  par Budget.get_used_amount) ; la lire affichait 0 EUR depense sur le
  dashboard. Supprimee pour eviter toute nouvelle confusion.

Revision ID: budget_report_01
Revises: account_overdraft_01
Create Date: 2026-11-04

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "budget_report_01"
down_revision = "account_overdraft_01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "budgets",
        sa.Column(
            "report_actif",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.drop_column("budgets", "spent_amount")


def downgrade():
    op.add_column(
        "budgets",
        sa.Column(
            "spent_amount", sa.Numeric(10, 2), server_default="0", nullable=True
        ),
    )
    op.drop_column("budgets", "report_actif")
