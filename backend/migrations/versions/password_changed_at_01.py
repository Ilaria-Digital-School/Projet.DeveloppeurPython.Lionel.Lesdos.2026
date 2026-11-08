"""Users: password_changed_at

Horodatage du dernier changement de mot de passe : les sessions web
(identifiant "<id>.<empreinte>") et les jetons JWT (iat) anterieurs sont
refuses. Avant, une reinitialisation ne coupait ni les sessions ouvertes ni
les jetons (refresh valable 7 jours) : un acces vole survivait au changement
de mot de passe.

Les utilisateurs existants restent a NULL : leurs sessions actuelles restent
valides jusqu'a leur prochain changement de mot de passe.

Revision ID: password_changed_at_01
Revises: recurring_failures_01
Create Date: 2026-10-28

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "password_changed_at_01"
down_revision = "recurring_failures_01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("users", "password_changed_at")
