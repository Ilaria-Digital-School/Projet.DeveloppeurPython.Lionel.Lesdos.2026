"""
Formulaires pour la gestion des catégories.
"""

from flask_wtf import FlaskForm
from wtforms import HiddenField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length


class CategoryForm(FlaskForm):
    """Formulaire pour la création et la modification de catégories."""

    # Champs cachés
    id = HiddenField("ID")

    # Champs visibles
    name = StringField(
        "Nom de la catégorie",
        validators=[
            DataRequired(message="Le nom de la catégorie est requis"),
            Length(max=100, message="Le nom ne peut pas dépasser 100 caractères"),
        ],
        render_kw={
            "placeholder": "Ex: Alimentation, Loyer, Salaire...",
            "class": "form-control",
            "autocomplete": "off",
        },
    )

    type = SelectField(
        "Type de catégorie",
        choices=[
            ("expense", "Dépense"),
            ("income", "Revenu"),
            ("transfer", "Transfert"),
        ],
        validators=[DataRequired(message="Le type de catégorie est requis")],
        render_kw={"class": "form-select", "aria-label": "Type de catégorie"},
    )

    # Bouton de soumission
    submit = SubmitField(
        "Enregistrer",
        render_kw={"class": "btn btn-primary", "data-cy": "save-category-button"},
    )
