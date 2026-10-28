"""Unify category_type on the English convention

- Convertit les valeurs françaises (depense/revenu/transfert) vers
  l'anglais (expense/income/transfer)
- Corrige is_expense d'après category_type (income -> False, sinon True) :
  jusqu'ici le seeding ne renseignait jamais is_expense (défaut True),
  d'où des revenus comme "Salaire" affichés en dépense
- Nettoie les descriptions générées ("Catégorie par défaut pour les
  retrait", "Catégorie personnelle pour ...") -> "Catégorie par défaut"
- Ajoute une contrainte CHECK pour verrouiller la convention

Revision ID: unify_category_type_01
Revises: user_fk_cascade_01
Create Date: 2026-07-06

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "unify_category_type_01"
down_revision = "user_fk_cascade_01"
branch_labels = None
depends_on = None

CHECK_NAME = "ck_categories_category_type"

FR_TO_EN = [
    ("depense", "expense"),
    ("revenu", "income"),
    ("transfert", "transfer"),
]


def upgrade():
    # 1. Unifier category_type sur la convention anglaise
    for fr, en in FR_TO_EN:
        op.execute(
            sa.text(
                "UPDATE categories SET category_type = :en WHERE category_type = :fr"
            ).bindparams(en=en, fr=fr)
        )

    # 2. Recaler is_expense sur category_type
    #    (convention du code existant : is_expense = type != 'income')
    op.execute(
        "UPDATE categories SET is_expense = (category_type != 'income') "
        "WHERE is_expense != (category_type != 'income')"
    )

    # 3. Nettoyer les descriptions générées automatiquement
    op.execute(
        "UPDATE categories SET description = 'Catégorie par défaut' "
        "WHERE description LIKE 'Catégorie par défaut pour%' "
        "   OR description LIKE 'Catégorie personnelle pour%'"
    )

    # 4. Verrouiller la convention avec une contrainte CHECK
    op.create_check_constraint(
        CHECK_NAME,
        "categories",
        "category_type IN ('expense', 'income', 'transfer')",
    )


def downgrade():
    op.drop_constraint(CHECK_NAME, "categories", type_="check")

    # Retour aux valeurs françaises (les descriptions et is_expense
    # d'origine ne sont pas restaurables : correction de données)
    for fr, en in FR_TO_EN:
        op.execute(
            sa.text(
                "UPDATE categories SET category_type = :fr WHERE category_type = :en"
            ).bindparams(en=en, fr=fr)
        )
