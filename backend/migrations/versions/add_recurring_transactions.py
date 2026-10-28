"""Add recurring_transactions table

Revision ID: add_recurring_tx_01
Revises: email_2fa_code_01
Create Date: 2026-02-16

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_recurring_tx_01"
down_revision = "email_2fa_code_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recurring_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        # Références de compte
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("ComptesBancaires.id_compte"),
            nullable=False,
        ),
        sa.Column(
            "destination_account_id",
            sa.Integer(),
            sa.ForeignKey("ComptesBancaires.id_compte"),
            nullable=True,
        ),
        sa.Column(
            "category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True
        ),
        # Template de la transaction
        sa.Column("montant", sa.Numeric(10, 2), nullable=False),
        sa.Column("type_transaction", sa.String(50), nullable=False),
        sa.Column("libelle", sa.String(200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("devise", sa.String(3), server_default="EUR"),
        # Paramètres de récurrence
        sa.Column("frequency", sa.String(20), nullable=False),
        sa.Column("interval", sa.Integer(), server_default="1", nullable=False),
        sa.Column("day_of_month", sa.Integer(), nullable=True),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        # Dates de contrôle
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("next_execution_date", sa.Date(), nullable=False),
        sa.Column("last_executed_date", sa.Date(), nullable=True),
        # État
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        # Audit
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
    )

    # Index composite pour le job de processing
    op.create_index(
        "ix_recurring_tx_active_next",
        "recurring_transactions",
        ["is_active", "next_execution_date"],
    )


def downgrade():
    op.drop_index("ix_recurring_tx_active_next", table_name="recurring_transactions")
    op.drop_table("recurring_transactions")
