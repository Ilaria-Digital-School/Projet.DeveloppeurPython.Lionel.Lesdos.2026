import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, DecimalField, SelectField, StringField, SubmitField
from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)


def validate_iban(form, field):
    if field.data and field.data.strip():  # Vérifie si le champ n'est pas vide
        # Supprimer les espaces et mettre en majuscules
        iban = field.data.replace(" ", "").upper()

        # IBAN doit commencer par 2 lettres puis 2 chiffres, puis 11-30 caractères alphanumériques
        # Longueur minimale : 15, maximale : 34
        if len(iban) < 15 or len(iban) > 34:
            raise ValidationError(
                f"Longueur IBAN invalide: {len(iban)} caractères. Doit être entre 15 et 34 caractères."
            )

        if not re.match(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$", iban):
            raise ValidationError(
                f"Format IBAN invalide. Doit commencer par 2 lettres + 2 chiffres. Exemple: FR7630006000011234567890189"
            )


def validate_bic(form, field):
    if field.data and field.data.strip():  # Vérifie si le champ n'est pas vide
        bic = field.data.strip().upper()

        # BIC : 8 ou 11 caractères, format SWIFT standard
        if len(bic) not in [8, 11]:
            raise ValidationError(
                f"Longueur BIC invalide: {len(bic)} caractères. Doit faire 8 ou 11 caractères."
            )

        # Format BIC: 4 lettres (banque) + 2 lettres (pays) + 2 caractères (localisation) + 3 caractères optionnels (branche)
        if not re.match(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$", bic):
            raise ValidationError(
                f"Format BIC invalide. Doit être: 4 lettres + 2 lettres pays + 2 caractères + 3 optionnels. Exemple: AGRIFRPP"
            )


class EditAccountForm(FlaskForm):
    """Formulaire de modification d'un compte existant."""

    # Informations de base
    name = StringField(
        "Nom du compte *",
        validators=[DataRequired(message="Le nom du compte est requis")],
        render_kw={"placeholder": "Ex: Compte Courant BNP"},
    )

    account_type = SelectField(
        "Type de compte *",
        choices=[
            ("checking", "Compte courant"),
            ("savings", "Épargne"),
            ("credit_card", "Carte de crédit"),
            ("cash", "Espèces"),
            ("investment", "Investissement"),
            ("loan", "Prêt"),
            ("other", "Autre"),
        ],
        validators=[DataRequired()],
    )

    # Informations bancaires (optionnelles)
    iban = StringField(
        "IBAN",
        validators=[Optional(), validate_iban],
        render_kw={"placeholder": "FR76 XXXX XXXX XXXX XXXX XXXX XXX"},
    )

    bic = StringField(
        "BIC/SWIFT",
        validators=[Optional(), validate_bic],
        render_kw={"placeholder": "Ex: AGRIFRPP"},
    )

    account_number = StringField(
        "Numéro de compte",
        validators=[Optional()],
        render_kw={"placeholder": "Numéro de compte bancaire"},
    )

    # Solde et limites
    current_balance = DecimalField(
        "Solde actuel",
        validators=[Optional(), NumberRange(min=0)],
        places=2,
        render_kw={"placeholder": "0.00"},
    )

    # Options
    is_active = BooleanField("Compte actif", default=True)
    include_in_balance = BooleanField("Inclure dans le solde total", default=True)

    # Bouton de soumission
    submit = SubmitField("Mettre à jour le compte")


class AddAccountForm(FlaskForm):
    # Informations de base
    name = StringField(
        "Nom du compte *",
        validators=[DataRequired(message="Le nom du compte est requis")],
        render_kw={"placeholder": "Ex: Compte Courant BNP"},
    )

    account_type = SelectField(
        "Type de compte *",
        choices=[
            ("checking", "Compte courant"),
            ("savings", "Épargne"),
            ("credit_card", "Carte de crédit"),
            ("cash", "Espèces"),
            ("investment", "Investissement"),
            ("other", "Autre"),
        ],
        validators=[DataRequired()],
    )

    initial_balance = DecimalField(
        "Solde initial *",
        validators=[
            DataRequired(message="Le solde initial est requis"),
            NumberRange(min=0, message="Le solde ne peut pas être négatif"),
        ],
        default=0.0,
        render_kw={"step": "0.01"},
    )

    currency = SelectField(
        "Devise *",
        choices=[
            ("EUR", "Euro (€)"),
            ("USD", "Dollar US ($)"),
            ("GBP", "Livre Sterling (£)"),
            ("CHF", "Franc Suisse (CHF)"),
        ],
        default="EUR",
    )

    # Informations bancaires
    bank_name = StringField(
        "Nom de la banque",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Ex: BNP Paribas"},
    )

    account_number = StringField(
        "Numéro de compte",
        validators=[Optional(), Length(max=34)],
        render_kw={"placeholder": "Numéro de compte bancaire"},
    )

    iban = StringField(
        "IBAN",
        validators=[Optional(), validate_iban],
        render_kw={
            "placeholder": "FR76 3000 6000 0112 3456 7890 189",
            "class": "uppercase",
        },
    )

    bic = StringField(
        "BIC/SWIFT",
        validators=[Optional(), validate_bic],
        render_kw={"placeholder": "Ex: AGRIFRPP", "class": "uppercase"},
    )

    is_active = BooleanField("Compte actif", default=True)

    submit = SubmitField(
        "Enregistrer le compte",
        render_kw={
            "class": "bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        },
    )

    def validate(self, **kwargs):
        # Validation standard d'abord
        if not super().validate():
            return False

        # Les champs IBAN et BIC sont optionnels
        # Ils ne sont validés que s'ils contiennent des données non vides
        if self.iban.data and self.iban.data.strip():
            try:
                validate_iban(self, self.iban)
            except ValidationError as e:
                self.iban.errors.append(str(e))
                return False

        if self.bic.data and self.bic.data.strip():
            try:
                validate_bic(self, self.bic)
            except ValidationError as e:
                self.bic.errors.append(str(e))
                return False

        return True
