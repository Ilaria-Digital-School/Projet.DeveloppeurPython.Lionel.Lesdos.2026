"""
Formulaires pour la gestion des transactions.
"""

from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    DecimalField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, NumberRange, Optional

from core.models.transactions import TransactionType  # Import direct de l'énumération


class TransactionForm(FlaskForm):
    """Formulaire pour la création et la modification de transactions."""

    @staticmethod
    def get_transaction_choices():
        """Génère les choix pour le champ de sélection du type de transaction."""
        return [
            ("", "Sélectionnez un type de transaction"),  # Option vide par défaut
            *[(t.value, t.display_name) for t in TransactionType],
        ]

    transaction_type = SelectField(
        "Type de transaction *",
        choices=[],  # Initialisé dans __init__
        default="",
        validators=[DataRequired("Le type de transaction est requis")],
        render_kw={"class": "form-select"},  # Classe Bootstrap pour le style
    )

    def __init__(self, *args, **kwargs):
        super(TransactionForm, self).__init__(*args, **kwargs)
        self.transaction_type.choices = self.get_transaction_choices()

    amount = StringField(
        "Montant",
        validators=[DataRequired("Le montant est obligatoire")],
        render_kw={
            "step": "any",
            "min": "0.01",
            "inputmode": "decimal",
            "title": "Entrez un montant (ex: 12 ou 12.34)",
        },
    )

    fees = DecimalField(
        "Frais",
        validators=[
            Optional(),
            NumberRange(min=0, message="Les frais ne peuvent pas être négatifs"),
        ],
        default=0.0,
        places=2,
    )

    description = StringField(
        "Description", validators=[DataRequired("La description est obligatoire")]
    )

    date = DateField(
        "Date",
        format="%Y-%m-%d",
        validators=[DataRequired("La date est obligatoire")],
        render_kw={
            "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm",
            "type": "date",
            "pattern": r"\d{4}-\d{2}-\d{2}",
        },
    )

    notes = TextAreaField("Notes", validators=[Optional()])

    account_id = SelectField(
        "Compte",
        coerce=int,
        validators=[DataRequired("Veuillez sélectionner un compte")],
    )

    category_id = SelectField(
        "Catégorie",
        coerce=lambda x: int(x) if x else None,
        validators=[Optional()],
        render_kw={"class": "form-select"},
    )
