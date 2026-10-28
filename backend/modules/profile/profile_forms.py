"""
Formulaires pour la gestion du profil utilisateur.
"""

import re

from flask_wtf import FlaskForm
from wtforms import (
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.fields import TelField
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Optional,
    ValidationError,
)

try:
    from flask_babel import lazy_gettext as _l
except ImportError:

    def _l(s):
        return s


# from core.validators.modules.common import PhoneValidator, ZipCodeValidator
# from core.validators.core import ValidationError as ValidatorError
# from zxcvbn import zxcvbn


class PasswordStrength:
    """
    Validateur personnalisé pour la force du mot de passe.
    Version simplifiée sans zxcvbn.

    Args:
        min_score (int): Score minimum requis (0-4)
        user_inputs (list): Liste d'informations utilisateur à éviter
    """

    def __init__(self, min_score=3, user_inputs=None, message=None):
        self.min_score = min_score
        self.user_inputs = user_inputs or []
        self.message = message or _l(
            "Le mot de passe est trop faible. Il doit contenir au moins 12 caractères "
            "avec des majuscules, minuscules, chiffres et caractères spéciaux."
        )

    def __call__(self, form, field):
        if not field.data:
            return

        # Vérification de base de la longueur
        if len(field.data) < 12:
            raise ValidationError(
                _l("Le mot de passe doit contenir au moins 12 caractères")
            )

        # Vérification des exigences de base
        import re

        if not re.search(r"[A-Z]", field.data):
            raise ValidationError(
                _l("Le mot de passe doit contenir au moins une majuscule")
            )
        if not re.search(r"[a-z]", field.data):
            raise ValidationError(
                _l("Le mot de passe doit contenir au moins une minuscule")
            )
        if not re.search(r"[0-9]", field.data):
            raise ValidationError(
                _l("Le mot de passe doit contenir au moins un chiffre")
            )
        if not re.search(r"[^A-Za-z0-9]", field.data):
            raise ValidationError(
                _l("Le mot de passe doit contenir au moins un caractère spécial")
            )


def validate_phone(form, field):
    """Valide le format du numéro de téléphone"""
    if not field.data:
        return
    # Validation simple pour l'instant
    import re

    if not re.match(r"^\+?[\d\s\-\(\)]+$", field.data):
        raise ValidationError(_l("Format de numéro de téléphone invalide"))


def validate_postal_code(form, field):
    """Valide le format du code postal en fonction du pays"""
    if not field.data:
        return
    # Validation simple pour l'instant
    import re

    if not re.match(r"^[\d\-\s]{3,10}$", field.data):
        raise ValidationError(_l("Format de code postal invalide"))


class ProfileForm(FlaskForm):
    """Formulaire de mise à jour du profil utilisateur."""

    # Informations de base
    first_name = StringField(_l("Prénom"), validators=[DataRequired()])
    last_name = StringField(_l("Nom"), validators=[DataRequired()])
    username = StringField(_l("Nom d'utilisateur"), validators=[Optional()])
    email = StringField(_l("Email"), validators=[DataRequired(), Email()])

    # Coordonnées
    phone = TelField(
        _l("Téléphone"),
        validators=[
            Optional(),
            validate_phone,
            Length(
                max=20,
                message=_l("Le numéro de téléphone ne doit pas dépasser 20 caractères"),
            ),
        ],
    )

    address = TextAreaField(
        _l("Adresse"),
        validators=[
            Optional(),
            Length(
                max=500, message=_l("L'adresse ne doit pas dépasser 500 caractères")
            ),
        ],
    )

    city = StringField(
        _l("Ville"),
        validators=[
            Optional(),
            Length(
                max=100,
                message=_l("Le nom de la ville ne doit pas dépasser 100 caractères"),
            ),
        ],
    )

    postal_code = StringField(
        _l("Code postal"),
        validators=[
            Optional(),
            validate_postal_code,
            Length(
                max=10, message=_l("Le code postal ne doit pas dépasser 10 caractères")
            ),
        ],
    )

    country = SelectField(
        _l("Pays"),
        choices=[
            ("FR", "France"),
            ("BE", "Belgique"),
            ("CH", "Suisse"),
            ("CA", "Canada"),
            ("US", "États-Unis"),
            # Ajouter d'autres pays selon les besoins
        ],
        validators=[DataRequired()],
    )

    # Préférences
    language = SelectField(
        _l("Langue préférée"),
        choices=[
            ("fr_FR", "Français"),
            ("en_US", "English"),
            ("es_ES", "Español"),
            ("de_DE", "Deutsch"),
        ],
        validators=[DataRequired()],
    )

    timezone = SelectField(
        _l("Fuseau horaire"),
        choices=[
            ("Europe/Paris", "Europe/Paris (CET)"),
            ("UTC", "UTC"),
            ("America/New_York", "America/New_York (EST)"),
            ("Asia/Tokyo", "Asia/Tokyo (JST)"),
            # Ajoutez d'autres fuseaux horaires selon les besoins
        ],
        validators=[DataRequired()],
    )

    # Bouton de soumission
    submit = SubmitField(_l("Mettre à jour le profil"))


class ChangePasswordForm(FlaskForm):
    """Formulaire de changement de mot de passe"""

    current_password = PasswordField(
        _l("Mot de passe actuel"),
        validators=[DataRequired(message=_l("Le mot de passe actuel est requis"))],
    )

    new_password = PasswordField(
        _l("Nouveau mot de passe"),
        validators=[
            DataRequired(message=_l("Le nouveau mot de passe est requis")),
            Length(
                min=12,
                message=_l("Le mot de passe doit contenir au moins 12 caractères"),
            ),
            EqualTo(
                "confirm_password", message=_l("Les mots de passe doivent correspondre")
            ),
            PasswordStrength(
                min_score=3,
                message=_l(
                    "Le mot de passe est trop faible. Il doit contenir au moins 12 caractères avec des majuscules, minuscules, chiffres et caractères spéciaux."
                ),
            ),
        ],
    )

    confirm_password = PasswordField(
        _l("Confirmer le nouveau mot de passe"),
        validators=[
            DataRequired(message=_l("Veuillez confirmer votre nouveau mot de passe"))
        ],
    )

    submit = SubmitField(_l("Changer le mot de passe"))

    def validate_new_password(self, field):
        """Valide la force du mot de passe"""
        password = field.data
        if len(password) < 8:
            raise ValidationError(
                _l("Le mot de passe doit contenir au moins 8 caractères")
            )
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _l("Le mot de passe doit contenir au moins une majuscule")
            )
        if not re.search(r"[a-z]", password):
            raise ValidationError(
                _l("Le mot de passe doit contenir au moins une minuscule")
            )
        if not re.search(r"[0-9]", password):
            raise ValidationError(
                _l("Le mot de passe doit contenir au moins un chiffre")
            )
        if not re.search(r"[^A-Za-z0-9]", password):
            raise ValidationError(
                _l("Le mot de passe doit contenir au moins un caractère spécial")
            )
