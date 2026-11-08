"""Add email_2fa_code field to users table

Revision ID: email_2fa_code_01
Revises: security_audit_01
Create Date: 2026-02-16

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "email_2fa_code_01"
down_revision = "security_audit_01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("email_2fa_code", sa.String(100), nullable=True))


def downgrade():
    op.drop_column("users", "email_2fa_code")
