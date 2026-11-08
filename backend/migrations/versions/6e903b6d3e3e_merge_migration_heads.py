"""Merge migration heads

Revision ID: 6e903b6d3e3e
Revises: 0a724edb00f6, add_profile_fields
Create Date: 2025-08-07 01:56:11.551888

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6e903b6d3e3e"
down_revision = ("0a724edb00f6", "add_profile_fields")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
