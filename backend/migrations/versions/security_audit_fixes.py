"""Security audit fixes: add reset_token fields to users and token_blacklist table

Revision ID: security_audit_01
Revises: 6e903b6d3e3e
Create Date: 2026-02-15

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "security_audit_01"
down_revision = "6e903b6d3e3e"
branch_labels = None
depends_on = None


def upgrade():
    # Add reset_token fields to users table
    op.add_column("users", sa.Column("reset_token", sa.String(256), nullable=True))
    op.add_column(
        "users", sa.Column("reset_token_expires", sa.DateTime(), nullable=True)
    )
    op.create_index("ix_users_reset_token", "users", ["reset_token"])

    # Create token_blacklist table for JWT revocation
    op.create_table(
        "token_blacklist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("jti", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_token_blacklist_jti", "token_blacklist", ["jti"])


def downgrade():
    op.drop_table("token_blacklist")
    op.drop_index("ix_users_reset_token", table_name="users")
    op.drop_column("users", "reset_token_expires")
    op.drop_column("users", "reset_token")
