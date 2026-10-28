"""Recurring transactions: track consecutive failures

echecs_consecutifs / derniere_erreur : un echec (solde insuffisant...) etait
seulement journalise et retente chaque nuit sans fin, sans prevenir
l'utilisateur. Le scheduler previent desormais au premier echec et met la
recurrence en pause apres 3 echecs consecutifs.

Revision ID: recurring_failures_01
Revises: budget_alerts_history_01
Create Date: 2026-10-28

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "recurring_failures_01"
down_revision = "budget_alerts_history_01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "recurring_transactions",
        sa.Column("echecs_consecutifs", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "recurring_transactions",
        sa.Column("derniere_erreur", sa.String(length=255), nullable=True),
    )


def downgrade():
    op.drop_column("recurring_transactions", "derniere_erreur")
    op.drop_column("recurring_transactions", "echecs_consecutifs")
