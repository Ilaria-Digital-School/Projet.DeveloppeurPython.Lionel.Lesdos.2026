"""Align database schema with SQLAlchemy models

`flask db check` signalait 57 ecarts entre les modeles et la base produite par
les migrations (identiques sur une base locale et sur une base vide rejouee de
zero). Les tests creent leurs tables depuis les modeles (create_all) et ne
pouvaient pas le voir.

Arbitrage : rien n'est supprime en base.
- Ce qui existe en base sans etre dans les modeles (colonnes roles.is_system,
  permissions.category, role_permissions.assigned_at, CHECK sur
  categories.category_type, tailles de colonnes, ON DELETE des cles etrangeres
  de security_events/user_sessions, index composite des recurrences) a ete
  ajoute aux modeles, sans migration.
- Ce que les modeles declarent en plus est cree ici : index manquants et
  ON DELETE CASCADE sur device_login_history.device_id (supprimer un appareil
  ayant un historique de connexion echouait sur la cle etrangere).

Ecrite de facon defensive (IF EXISTS / IF NOT EXISTS) : la base de production
n'a pas pu etre comparee directement.

Revision ID: align_schema_models_01
Revises: security_session_tables_01
Create Date: 2026-10-28

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "align_schema_models_01"
down_revision = "security_session_tables_01"
branch_labels = None
depends_on = None

# (nom, table, expression) — expressions telles que declarees dans les modeles
INDEX = [
    ("ix_budget_history_changed_at", "budget_history", "changed_at"),
    ("idx_login_history_user_time", "device_login_history", "user_id, login_time"),
    ("idx_login_history_device_time", "device_login_history", "device_id, login_time"),
    (
        "idx_login_history_success",
        "device_login_history",
        "user_id, was_successful, login_time",
    ),
    ("ix_device_login_history_ip_address", "device_login_history", "ip_address"),
    ("ix_device_login_history_login_time", "device_login_history", "login_time"),
    ("ix_device_login_history_was_successful", "device_login_history", "was_successful"),
    ("idx_device_user_active", "devices", "user_id, is_active"),
    ("idx_device_trusted", "devices", "user_id, is_trusted"),
    ("idx_device_user_heartbeat", "devices", "user_id, last_heartbeat"),
    ("ix_devices_browser", "devices", "browser"),
    ("ix_devices_created_at", "devices", "created_at"),
    ("ix_devices_device_id", "devices", "device_id"),
    ("ix_devices_device_type", "devices", "device_type"),
    ("ix_devices_is_active", "devices", "is_active"),
    ("ix_devices_is_primary", "devices", "is_primary"),
    ("ix_devices_is_trusted", "devices", "is_trusted"),
    ("ix_devices_last_heartbeat", "devices", "last_heartbeat"),
    ("ix_devices_last_used", "devices", "last_used"),
    ("ix_devices_name", "devices", "name"),
    ("ix_devices_os", "devices", "os"),
    ("ix_devices_revoked_at", "devices", "revoked_at"),
    ("ix_devices_two_factor_enabled", "devices", "two_factor_enabled"),
    ("ix_devices_updated_at", "devices", "updated_at"),
    ("ix_devices_verification_token", "devices", "verification_token"),
    (
        "ix_devices_verification_token_expires",
        "devices",
        "verification_token_expires",
    ),
    ("idx_user_email_lower", "users", "lower(email)"),
    ("idx_user_username_lower", "users", "lower(username)"),
]


def upgrade():
    for nom, table, expression in INDEX:
        op.execute(f"CREATE INDEX IF NOT EXISTS {nom} ON {table} ({expression})")

    # Doublon de la contrainte d'unicite token_blacklist_jti_key
    op.execute("DROP INDEX IF EXISTS ix_token_blacklist_jti")

    # Supprimer un appareil supprime son historique de connexion
    op.execute(
        "ALTER TABLE device_login_history "
        "DROP CONSTRAINT IF EXISTS device_login_history_device_id_fkey"
    )
    op.execute(
        "ALTER TABLE device_login_history "
        "ADD CONSTRAINT device_login_history_device_id_fkey "
        "FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE"
    )

    # Defauts serveur alignes sur ce que SQLAlchemy stocke (nom du membre d'Enum)
    op.execute("ALTER TABLE email_queue ALTER COLUMN status SET DEFAULT 'PENDING'")
    op.execute(
        "ALTER TABLE user_settings ALTER COLUMN setting_type SET DEFAULT 'STRING'"
    )


def downgrade():
    op.execute(
        "ALTER TABLE user_settings ALTER COLUMN setting_type SET DEFAULT 'string'"
    )
    op.execute("ALTER TABLE email_queue ALTER COLUMN status SET DEFAULT 'pending'")

    op.execute(
        "ALTER TABLE device_login_history "
        "DROP CONSTRAINT IF EXISTS device_login_history_device_id_fkey"
    )
    op.execute(
        "ALTER TABLE device_login_history "
        "ADD CONSTRAINT device_login_history_device_id_fkey "
        "FOREIGN KEY (device_id) REFERENCES devices(id)"
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_token_blacklist_jti ON token_blacklist (jti)")

    for nom, _table, _expression in reversed(INDEX):
        op.execute(f"DROP INDEX IF EXISTS {nom}")
