"""Create security_events and user_sessions tables

Ces deux tables figurent au MPD (livrable 03_Schemas_BDD) et ont un modele
SQLAlchemy (SecurityEvent, UserSession), mais aucune migration ne les creait :
l'autogenerate d'Alembic tournait a vide, `migrations/env.py` important
`Session` alors que la classe se nomme `UserSession`, ce qui laissait
`target_metadata = None`.

Consequence corrigee ici : `log_security_event()` (appele par
core/models/device.py) echouait silencieusement, son commit etant rattrape par
un try/except qui se contentait de journaliser l'erreur.

Les regles ON DELETE reprennent celles du MPD.

Revision ID: security_session_tables_01
Revises: unify_category_type_01
Create Date: 2026-08-15

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "security_session_tables_01"
down_revision = "unify_category_type_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "security_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["device_id"], ["devices.id"], name="fk_se_device", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_se_user", ondelete="SET NULL"
        ),
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_activity", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_sessions_user", ondelete="CASCADE"
        ),
    )


def downgrade():
    op.drop_table("user_sessions")
    op.drop_table("security_events")
