"""
Formulaires pour le module de tableau de bord
"""

from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    DecimalField,
    IntegerField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)

# =============================
# FORMULAIRES BUDGETS INTÉGRÉS
# =============================


class BudgetBaseForm(FlaskForm):
    """Formulaire de base pour les budgets."""

    amount = DecimalField(
        "Montant",
        validators=[
            DataRequired(message="Le montant est obligatoire"),
            NumberRange(min=0.01, message="Le montant doit être supérieur à zéro"),
        ],
        places=2,
        description="Montant budgétisé pour la période",
    )

    period = SelectField(
        "Période",
        choices=[
            ("monthly", "Mensuel"),
            ("yearly", "Annuel"),
            ("custom", "Personnalisé"),
        ],
        validators=[DataRequired(message="La période est obligatoire")],
        description="Période de budgétisation",
    )

    start_date = DateField(
        "Date de début",
        validators=[DataRequired(message="La date de début est obligatoire")],
        default=date.today,
        format="%Y-%m-%d",
        description="Date de début de la période de budgétisation",
    )

    end_date = DateField(
        "Date de fin",
        validators=[Optional()],
        format="%Y-%m-%d",
        description="Date de fin (requise pour les périodes personnalisées)",
    )

    notification_threshold = IntegerField(
        "Seuil de notification (%)",
        validators=[
            Optional(),
            NumberRange(min=1, max=100, message="Le seuil doit être entre 1 et 100%"),
        ],
        default=90,
        description="Seuil de notification de dépassement en pourcentage",
    )

    notes = TextAreaField(
        "Notes",
        validators=[
            Optional(),
            Length(max=500, message="Les notes ne doivent pas dépasser 500 caractères"),
        ],
        description="Notes supplémentaires sur le budget",
    )

    def validate_end_date(self, field):
        """Valide que la date de fin est postérieure à la date de début."""
        if self.period.data == "custom" and not field.data:
            raise ValidationError(
                "La date de fin est requise pour une période personnalisée"
            )

        if field.data and field.data <= self.start_date.data:
            raise ValidationError(
                "La date de fin doit être postérieure à la date de début"
            )


class CreateBudgetForm(BudgetBaseForm):
    """Formulaire de création d'un budget."""

    category_id = SelectField(
        "Catégorie",
        coerce=int,
        choices=[],
        validate_choice=False,
        validators=[DataRequired(message="La catégorie est obligatoire")],
        description="Catégorie à laquelle le budget s'applique",
    )

    name = StringField(
        "Nom du budget",
        validators=[
            DataRequired(message="Le nom du budget est obligatoire"),
            Length(max=100, message="Le nom ne doit pas dépasser 100 caractères"),
        ],
        description="Nom explicite pour identifier ce budget",
    )


class UpdateBudgetForm(BudgetBaseForm):
    """Formulaire de mise à jour d'un budget."""

    category_id = SelectField(
        "Catégorie",
        coerce=int,
        choices=[],
        validate_choice=False,
        validators=[Optional()],
        description="Catégorie à laquelle le budget s'applique",
    )

    name = StringField(
        "Nom du budget",
        validators=[
            Optional(),
            Length(max=100, message="Le nom ne doit pas dépasser 100 caractères"),
        ],
        description="Nom explicite pour identifier ce budget",
    )

    def __init__(self, *args, **kwargs):
        """Initialise le formulaire avec des champs non obligatoires pour la mise à jour."""
        super().__init__(*args, **kwargs)
        # Rendre les champs optionnels pour la mise à jour
        for field in self:
            if hasattr(field, "validators") and DataRequired in [
                v.__class__ for v in field.validators
            ]:
                field.validators = [
                    v for v in field.validators if not isinstance(v, DataRequired)
                ]
                field.validators.append(Optional())


def get_budget_form(data=None, csrf_enabled=True, **kwargs):
    """
    Factory function pour obtenir le formulaire approprié en fonction des données fournies.

    Args:
        data (dict, optional): Données du formulaire. Si None, crée un nouveau formulaire vide.
            Si contient une clé 'id', utilise UpdateBudgetForm, sinon CreateBudgetForm.
        csrf_enabled (bool): Si False, désactive la validation CSRF (pour les appels API).
        **kwargs: Arguments supplémentaires à passer au constructeur du formulaire.

    Returns:
        BudgetBaseForm: Une instance de CreateBudgetForm ou UpdateBudgetForm selon le cas.

    Example:
        # Pour un nouveau formulaire
        form = get_budget_form()

        # Pour un formulaire de mise à jour
        form = get_budget_form(data={'id': 1, 'name': 'Mon budget'})
    """
    if not csrf_enabled:
        kwargs["meta"] = {"csrf": False}
        kwargs["formdata"] = (
            None  # Empêcher Flask-WTF de lire request.form (contexte API)
        )
    if data and "id" in data:
        return UpdateBudgetForm(data=data, **kwargs)
    return CreateBudgetForm(data=data, **kwargs)
