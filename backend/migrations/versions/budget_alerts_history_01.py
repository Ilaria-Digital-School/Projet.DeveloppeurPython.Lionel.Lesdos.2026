"""Budgets: derniere_alerte, and keep budget history when a budget is deleted

- budgets.derniere_alerte : derniere alerte envoyee ("<debut de periode>:<niveau>").
  Remplace l'usage de notification_sent, mis a vrai a la premiere alerte et
  jamais remis a faux (plus aucune alerte ensuite, ni les mois suivants).
- budget_history.budget_id : nullable + ON DELETE SET NULL. NOT NULL sans
  ON DELETE faisait echouer la suppression de tout budget ayant un historique
  (tous ceux crees ou modifies depuis l'interface).

Revision ID: budget_alerts_history_01
Revises: add_solde_initial_01
Create Date: 2026-10-28

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "budget_alerts_history_01"
down_revision = "add_solde_initial_01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "budgets", sa.Column("derniere_alerte", sa.String(length=32), nullable=True)
    )
    op.alter_column("budget_history", "budget_id", nullable=True)
    op.execute(
        "ALTER TABLE budget_history DROP CONSTRAINT IF EXISTS budget_history_budget_id_fkey"
    )
    op.execute(
        "ALTER TABLE budget_history ADD CONSTRAINT budget_history_budget_id_fkey "
        "FOREIGN KEY (budget_id) REFERENCES budgets(id) ON DELETE SET NULL"
    )


def downgrade():
    op.execute(
        "ALTER TABLE budget_history DROP CONSTRAINT IF EXISTS budget_history_budget_id_fkey"
    )
    # Les historiques de budgets supprimes (budget_id NULL) ne peuvent pas
    # revenir sous NOT NULL
    op.execute("DELETE FROM budget_history WHERE budget_id IS NULL")
    op.execute(
        "ALTER TABLE budget_history ADD CONSTRAINT budget_history_budget_id_fkey "
        "FOREIGN KEY (budget_id) REFERENCES budgets(id)"
    )
    op.alter_column("budget_history", "budget_id", nullable=False)
    op.drop_column("budgets", "derniere_alerte")
