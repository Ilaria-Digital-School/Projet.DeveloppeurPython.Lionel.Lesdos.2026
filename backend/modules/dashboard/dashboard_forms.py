"""
Formulaires pour le module de tableau de bord
"""

from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)


class DateRangeForm(FlaskForm):
    """Formulaire pour sélectionner une plage de dates"""

    start_date = DateField(
        "Date de début",
        validators=[DataRequired(message="La date de début est requise")],
        default=date.today().replace(day=1),  # Premier jour du mois en cours
        format="%Y-%m-%d",
        render_kw={"class": "form-control", "type": "date"},
    )

    end_date = DateField(
        "Date de fin",
        validators=[DataRequired(message="La date de fin est requise")],
        default=date.today(),
        format="%Y-%m-%d",
        render_kw={"class": "form-control", "type": "date"},
    )

    submit = SubmitField("Appliquer", render_kw={"class": "btn btn-primary"})

    def validate(self, **kwargs):
        # Validation standard
        if not super().validate():
            return False

        # Validation personnalisée pour s'assurer que la date de début est avant la date de fin
        if self.start_date.data > self.end_date.data:
            self.end_date.errors.append(
                "La date de fin doit être postérieure à la date de début"
            )
            return False

        return True


class QuickTransactionForm(FlaskForm):
    """Formulaire pour ajouter rapidement une transaction depuis le tableau de bord"""

    amount = DecimalField(
        "Montant",
        validators=[
            DataRequired(message="Le montant est requis"),
            NumberRange(min=0.01, message="Le montant doit être supérieur à zéro"),
        ],
        places=2,
        render_kw={
            "class": "form-control",
            "placeholder": "0.00",
            "step": "0.01",
            "min": "0.01",
        },
    )

    description = StringField(
        "Description",
        validators=[
            DataRequired(message="La description est requise"),
            Length(
                max=100, message="La description ne doit pas dépasser 100 caractères"
            ),
        ],
        render_kw={
            "class": "form-control",
            "placeholder": "Description de la transaction",
        },
    )

    transaction_type = SelectField(
        "Type",
        choices=[("expense", "Dépense"), ("income", "Revenu")],
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    category_id = SelectField(
        "Catégorie",
        coerce=int,
        validators=[DataRequired(message="Veuillez sélectionner une catégorie")],
        render_kw={"class": "form-select"},
    )

    date = DateField(
        "Date",
        validators=[DataRequired(message="La date est requise")],
        default=date.today,
        format="%Y-%m-%d",
        render_kw={"class": "form-control", "type": "date"},
    )

    submit = SubmitField("Ajouter", render_kw={"class": "btn btn-success w-100"})


class BudgetGoalForm(FlaskForm):
    """Formulaire pour définir un objectif budgétaire"""

    amount = DecimalField(
        "Montant cible",
        validators=[
            DataRequired(message="Le montant est requis"),
            NumberRange(min=0.01, message="Le montant doit être supérieur à zéro"),
        ],
        places=2,
        render_kw={
            "class": "form-control",
            "placeholder": "0.00",
            "step": "0.01",
            "min": "0.01",
        },
    )

    period = SelectField(
        "Période",
        choices=[
            ("monthly", "Mensuel"),
            ("quarterly", "Trimestriel"),
            ("yearly", "Annuel"),
        ],
        default="monthly",
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    category_id = SelectField(
        "Catégorie (optionnel)",
        coerce=int,
        validators=[Optional()],
        render_kw={"class": "form-select"},
    )

    notes = TextAreaField(
        "Notes (optionnel)",
        validators=[Optional(), Length(max=500)],
        render_kw={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Ajoutez des notes ou des détails sur cet objectif",
        },
    )

    submit = SubmitField("Définir l'objectif", render_kw={"class": "btn btn-primary"})


class DashboardPreferencesForm(FlaskForm):
    """Formulaire pour les préférences du tableau de bord"""

    default_view = SelectField(
        "Vue par défaut",
        choices=[
            ("overview", "Aperçu général"),
            ("transactions", "Dernières transactions"),
            ("budgets", "Budgets et objectifs"),
            ("analytics", "Analyses et rapports"),
        ],
        default="overview",
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    currency = SelectField(
        "Devise",
        choices=[
            ("EUR", "Euro (€)"),
            ("USD", "Dollar US ($)"),
            ("GBP", "Livre sterling (£)"),
            ("JPY", "Yen (¥)"),
        ],
        default="EUR",
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    show_charts = BooleanField(
        "Afficher les graphiques", default=True, render_kw={"class": "form-check-input"}
    )

    show_quick_add = BooleanField(
        "Afficher le formulaire d'ajout rapide",
        default=True,
        render_kw={"class": "form-check-input"},
    )

    submit = SubmitField(
        "Enregistrer les préférences", render_kw={"class": "btn btn-primary"}
    )


class ExportDataForm(FlaskForm):
    """Formulaire pour l'export des données du tableau de bord"""

    format = SelectField(
        "Format d'export",
        choices=[("csv", "CSV (Excel)"), ("json", "JSON"), ("pdf", "PDF")],
        default="csv",
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    data_type = SelectField(
        "Données à exporter",
        choices=[
            ("transactions", "Transactions"),
            ("budgets", "Budgets"),
            ("all", "Toutes les données"),
        ],
        default="transactions",
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    date_range = SelectField(
        "Période",
        choices=[
            ("current_month", "Mois en cours"),
            ("last_month", "Mois dernier"),
            ("current_year", "Année en cours"),
            ("last_year", "Année dernière"),
            ("custom", "Période personnalisée"),
        ],
        default="current_month",
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    custom_start_date = DateField(
        "Date de début",
        validators=[Optional()],
        format="%Y-%m-%d",
        render_kw={"class": "form-control", "type": "date", "disabled": True},
    )

    custom_end_date = DateField(
        "Date de fin",
        validators=[Optional()],
        format="%Y-%m-%d",
        render_kw={"class": "form-control", "type": "date", "disabled": True},
    )

    include_charts = BooleanField(
        "Inclure les graphiques (PDF uniquement)",
        default=True,
        render_kw={"class": "form-check-input"},
    )

    submit = SubmitField("Exporter les données", render_kw={"class": "btn btn-primary"})

    def validate(self, **kwargs):
        # Validation standard
        if not super().validate():
            return False

        # Validation pour la période personnalisée
        if self.date_range.data == "custom":
            if not self.custom_start_date.data or not self.custom_end_date.data:
                self.date_range.errors.append(
                    "Veuillez spécifier une période personnalisée"
                )
                return False

            if self.custom_start_date.data > self.custom_end_date.data:
                self.custom_end_date.errors.append(
                    "La date de fin doit être postérieure à la date de début"
                )
                return False

        return True


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
