"""Add ON DELETE CASCADE to foreign keys referencing users

Permet la suppression physique d'un utilisateur (UserService.delete_user)
en laissant PostgreSQL supprimer automatiquement les données liées.

Revision ID: user_fk_cascade_01
Revises: add_recurring_tx_01
Create Date: 2026-07-06

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "user_fk_cascade_01"
down_revision = "add_recurring_tx_01"
branch_labels = None
depends_on = None

# (nom_contrainte, table, colonne) des FK référençant users.id
# transactions.user_id est déjà en CASCADE (non listée ici)
USER_FOREIGN_KEYS = [
    ("ComptesBancaires_utilisateur_id_fkey", "ComptesBancaires", "utilisateur_id"),
    ("budget_history_user_id_fkey", "budget_history", "user_id"),
    ("budgets_user_id_fkey", "budgets", "user_id"),
    ("categories_user_id_fkey", "categories", "user_id"),
    ("device_login_history_user_id_fkey", "device_login_history", "user_id"),
    ("devices_user_id_fkey", "devices", "user_id"),
    ("notification_preferences_user_id_fkey", "notification_preferences", "user_id"),
    ("notifications_user_id_fkey", "notifications", "user_id"),
    ("recurring_transactions_user_id_fkey", "recurring_transactions", "user_id"),
    ("reports_user_id_fkey", "reports", "user_id"),
    ("user_roles_user_id_fkey", "user_roles", "user_id"),
    ("user_settings_user_id_fkey", "user_settings", "user_id"),
]


def upgrade():
    for constraint_name, table, column in USER_FOREIGN_KEYS:
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(
            constraint_name,
            table,
            "users",
            [column],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade():
    for constraint_name, table, column in USER_FOREIGN_KEYS:
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(
            constraint_name,
            table,
            "users",
            [column],
            ["id"],
        )
