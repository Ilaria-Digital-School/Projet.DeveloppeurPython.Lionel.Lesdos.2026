"""Users: suppression de la colonne morte last_login

- users.last_login : jamais ecrite (seul last_login_at est mis a jour par
  AuthService). Toujours NULL, et un fallback inutile `last_login_at or
  last_login` tranainait dans AdminService. Supprimee pour clarifier le modele.

Revision ID: drop_last_login_01
Revises: budget_report_01
Create Date: 2026-11-07

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "drop_last_login_01"
down_revision = "budget_report_01"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("users", "last_login")


def downgrade():
    op.add_column(
        "users",
        sa.Column("last_login", sa.DateTime(), nullable=True),
    )
