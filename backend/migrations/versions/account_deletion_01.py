"""Users: deletion_scheduled_at

DELETE /api/v1/settings/account promettait une suppression definitive a J+7,
annulable en se reconnectant. Aucune date n'etait enregistree, aucune purge
n'existait (les donnees restaient indefiniment) et la connexion d'un compte
desactive etait refusee (annulation impossible).

Revision ID: account_deletion_01
Revises: password_changed_at_01
Create Date: 2026-10-28

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "account_deletion_01"
down_revision = "password_changed_at_01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("deletion_scheduled_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("users", "deletion_scheduled_at")
