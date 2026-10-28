"""ComptesBancaires: decouvert_autorise

Une depense etait refusee des que le solde devenait negatif, alors qu'un
compte courant peut passer a decouvert dans la limite fixee par la banque.
L'import d'un releve reel echouait donc en entier sur un seul jour de
decouvert. 0 par defaut : le comportement des comptes existants ne change pas.

Revision ID: account_overdraft_01
Revises: account_deletion_01
Create Date: 2026-10-28

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "account_overdraft_01"
down_revision = "account_deletion_01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ComptesBancaires",
        sa.Column(
            "decouvert_autorise",
            sa.Numeric(12, 2),
            server_default="0",
            nullable=False,
        ),
    )


def downgrade():
    op.drop_column("ComptesBancaires", "decouvert_autorise")
