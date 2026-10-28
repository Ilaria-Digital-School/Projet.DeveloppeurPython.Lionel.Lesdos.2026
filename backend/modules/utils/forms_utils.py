"""
Form utilities for the Appli_Web_Budget application.

This module provides utility functions for form handling and validation.
"""

from flask_wtf import FlaskForm
from wtforms import DecimalField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange


def get_budget_form():
    """
    Returns a budget form class for creating and editing budgets.

    Returns:
        FlaskForm: A form class for budget operations
    """

    class BudgetForm(FlaskForm):
        """Form for budget creation and editing."""

        name = StringField(
            "Nom du budget",
            validators=[
                DataRequired(message="Le nom du budget est requis"),
                Length(
                    min=1,
                    max=100,
                    message="Le nom doit contenir entre 1 et 100 caractères",
                ),
            ],
        )

        amount = DecimalField(
            "Montant",
            validators=[
                DataRequired(message="Le montant est requis"),
                NumberRange(min=0.01, message="Le montant doit être positif"),
            ],
            places=2,
        )

        category = SelectField(
            "Catégorie",
            validators=[DataRequired(message="La catégorie est requise")],
            coerce=int,
        )

        description = TextAreaField(
            "Description",
            validators=[
                Length(
                    max=500,
                    message="La description ne peut pas dépasser 500 caractères",
                )
            ],
        )

    return BudgetForm
