"""
Formulaires d'authentification unifiés.

Ce module contient tous les formulaires d'authentification avec validation avancée.
"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField

# Imports des validateurs et modèles (temporairement simplifiés)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Regexp,
    ValidationError,
)

from core.models.user import User


class UsernameValidator:
    """Validateur personnalisé pour les noms d'utilisateur."""

    def __init__(self, min_length=3, max_length=30, allow_unicode=True, message=None):
        self.min_length = min_length
        self.max_length = max_length
        self.allow_unicode = allow_unicode
        self.message = message or "Nom d'utilisateur invalide"

    def __call__(self, form, field):
        username = field.data
        if not username:
            return

        # Vérification de la longueur
        if len(username) < self.min_length or len(username) > self.max_length:
            raise ValidationError(
                f"Le nom d'utilisateur doit contenir entre {self.min_length} et {self.max_length} caractères."
            )

        # Vérification des caractères autorisés
        import re

        pattern = r"^[a-zA-Z0-9._-]+$"
        if not re.match(pattern, username):
            raise ValidationError(
                "Le nom d'utilisateur ne peut contenir que des lettres, chiffres, points, tirets et tirets bas."
            )


class EmailField(StringField):
    """Champ de formulaire personnalisé pour la validation d'email."""

    def __init__(self, label="", validators=None, **kwargs):
        if validators is None:
            validators = []

        # Ajout des validateurs standards
        validators.insert(0, DataRequired(message="L'adresse email est requise"))
        validators.append(Email(message="Veuillez entrer une adresse email valide."))

        super().__init__(label, validators, **kwargs)


class PasswordFieldWithValidation(PasswordField):
    """Champ de mot de passe avec validation personnalisée."""

    def __init__(self, label="", validators=None, **kwargs):
        if validators is None:
            validators = []

        # Ajout des validateurs standards
        validators.insert(0, DataRequired(message="Le mot de passe est requis"))
        validators.append(
            Length(
                min=12, message="Le mot de passe doit contenir au moins 12 caractères"
            )
        )
        validators.append(
            Regexp(
                r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).+$",
                message="Le mot de passe doit contenir au moins une majuscule, une minuscule, un chiffre et un caractère spécial.",
            )
        )

        super().__init__(label, validators, **kwargs)


class UsernameField(StringField):
    """Champ de nom d'utilisateur avec validation personnalisée."""

    def __init__(self, label="", validators=None, **kwargs):
        if validators is None:
            validators = []

        # Ajout du validateur de nom d'utilisateur personnalisé
        username_validator = UsernameValidator(
            min_length=3,
            max_length=30,
            allow_unicode=True,
            message=(
                "Le nom d'utilisateur doit contenir entre 3 et 30 caractères, "
                "et ne peut contenir que des lettres, chiffres, points, tirets et tirets bas."
            ),
        )
        validators.insert(0, DataRequired(message="Le nom d'utilisateur est requis"))
        validators.append(username_validator)
        validators.append(Length(min=3, max=30))

        super().__init__(label, validators, **kwargs)


# ============================================================================
# FORMULAIRES D'AUTHENTIFICATION
# ============================================================================


class LoginForm(FlaskForm):
    """Formulaire de connexion utilisateur."""

    email = EmailField(
        "Email", render_kw={"placeholder": "votre@email.com", "autocomplete": "email"}
    )
    password = PasswordField(
        "Mot de passe",
        validators=[DataRequired(message="Le mot de passe est requis")],
        render_kw={
            "placeholder": "Votre mot de passe",
            "autocomplete": "current-password",
        },
    )
    remember_me = BooleanField("Se souvenir de moi")
    submit = SubmitField("Se connecter")


class RegistrationForm(FlaskForm):
    """Formulaire d'inscription utilisateur avec validation avancée."""

    username = UsernameField(
        "Nom d'utilisateur",
        render_kw={
            "placeholder": "3 à 30 caractères, lettres, chiffres et _-.",
            "autocomplete": "username",
            "minlength": 3,
            "maxlength": 30,
        },
    )
    email = EmailField(
        "Email", render_kw={"placeholder": "votre@email.com", "autocomplete": "email"}
    )
    password = PasswordFieldWithValidation(
        "Mot de passe",
        render_kw={
            "placeholder": "12 caractères min, majuscules, chiffres et caractères spéciaux",
            "autocomplete": "new-password",
            "minlength": 12,
        },
    )
    password2 = PasswordField(
        "Confirmer le mot de passe",
        validators=[
            DataRequired(message="Veuillez confirmer votre mot de passe"),
            EqualTo("password", message="Les mots de passe doivent correspondre"),
        ],
        render_kw={
            "placeholder": "Confirmez votre mot de passe",
            "autocomplete": "new-password",
        },
    )
    submit = SubmitField("S'inscrire")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Amélioration de l'accessibilité
        self.username.label.text = "Nom d'utilisateur *"
        self.email.label.text = "Adresse email *"
        self.password.label.text = "Mot de passe *"
        self.password2.label.text = "Confirmer le mot de passe *"

    def validate_username(self, field):
        """Vérifie si le nom d'utilisateur est déjà utilisé."""
        user = User.query.filter_by(username=field.data).first()
        if user:
            raise ValidationError("Ce nom d'utilisateur n'est pas disponible.")

    def validate_email(self, field):
        """Vérifie si l'email est déjà enregistré."""
        user = User.query.filter_by(email=field.data.lower()).first()
        if user:
            raise ValidationError(
                "Impossible de créer un compte avec cette adresse email."
            )


class ResetPasswordRequestForm(FlaskForm):
    """Formulaire de demande de réinitialisation de mot de passe."""

    email = EmailField(
        "Email", render_kw={"placeholder": "votre@email.com", "autocomplete": "email"}
    )
    submit = SubmitField("Demander la réinitialisation du mot de passe")


class ResetPasswordForm(FlaskForm):
    """Formulaire de réinitialisation de mot de passe avec validation avancée."""

    password = PasswordFieldWithValidation(
        "Nouveau mot de passe",
        render_kw={
            "placeholder": "12 caractères min, majuscules, chiffres et caractères spéciaux",
            "autocomplete": "new-password",
            "minlength": 12,
        },
    )
    password2 = PasswordField(
        "Confirmer le mot de passe",
        validators=[
            DataRequired(message="Veuillez confirmer votre mot de passe"),
            EqualTo("password", message="Les mots de passe doivent correspondre"),
        ],
        render_kw={
            "placeholder": "Confirmez votre mot de passe",
            "autocomplete": "new-password",
        },
    )
    submit = SubmitField("Réinitialiser le mot de passe")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Amélioration de l'accessibilité
        self.password.label.text = "Nouveau mot de passe *"
        self.password2.label.text = "Confirmer le mot de passe *"


# ============================================================================
# FORMULAIRES SIMPLES (pour compatibilité)
# ============================================================================


class SimpleLoginForm(FlaskForm):
    """Formulaire de connexion simplifié."""

    email = StringField("Email", validators=[DataRequired(message="Email requis")])
    password = PasswordField(
        "Mot de passe", validators=[DataRequired(message="Mot de passe requis")]
    )
    submit = SubmitField("Se connecter")


class SimpleRegistrationForm(FlaskForm):
    """Formulaire d'inscription simplifié."""

    username = StringField(
        "Nom d'utilisateur",
        validators=[
            DataRequired(message="Nom d'utilisateur requis"),
            Length(min=3, max=30),
        ],
    )
    email = StringField("Email", validators=[DataRequired(message="Email requis")])
    password = PasswordField(
        "Mot de passe",
        validators=[DataRequired(message="Mot de passe requis"), Length(min=12)],
    )
    submit = SubmitField("S'inscrire")

    def validate_username(self, field):
        """Vérifie si le nom d'utilisateur est déjà utilisé."""
        user = User.query.filter_by(username=field.data).first()
        if user:
            raise ValidationError("Ce nom d'utilisateur n'est pas disponible.")

    def validate_email(self, field):
        """Vérifie si l'email est déjà enregistré."""
        user = User.query.filter_by(email=field.data.lower()).first()
        if user:
            raise ValidationError(
                "Impossible de créer un compte avec cette adresse email."
            )
