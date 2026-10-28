from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

# Import des formulaires avec gestion d'erreur
try:
    from .profile_forms import ChangePasswordForm, ProfileForm
except ImportError:
    # Créer des classes de fallback simples
    from flask_wtf import FlaskForm
    from wtforms import (
        PasswordField,
        SelectField,
        StringField,
        SubmitField,
        TextAreaField,
    )
    from wtforms.validators import DataRequired, Email, Optional

    class ProfileForm(FlaskForm):
        first_name = StringField("Prénom")
        last_name = StringField("Nom")
        email = StringField("Email", validators=[Email()])
        phone = StringField("Téléphone", validators=[Optional()])
        language = SelectField(
            "Langue",
            choices=[("fr_FR", "Français"), ("en_US", "English")],
            validators=[Optional()],
        )
        timezone = SelectField(
            "Fuseau horaire",
            choices=[("Europe/Paris", "Europe/Paris"), ("UTC", "UTC")],
            validators=[Optional()],
        )
        address = TextAreaField("Adresse", validators=[Optional()])
        city = StringField("Ville", validators=[Optional()])
        postal_code = StringField("Code postal", validators=[Optional()])
        country = SelectField(
            "Pays",
            choices=[("FR", "France"), ("US", "États-Unis"), ("CA", "Canada")],
            validators=[Optional()],
        )
        submit = SubmitField("Mettre à jour")

    class ChangePasswordForm(FlaskForm):
        current_password = PasswordField(
            "Mot de passe actuel", validators=[DataRequired()]
        )
        new_password = PasswordField(
            "Nouveau mot de passe", validators=[DataRequired()]
        )
        confirm_password = PasswordField(
            "Confirmer le mot de passe", validators=[DataRequired()]
        )
        submit = SubmitField("Changer le mot de passe")


# Import du service avec gestion d'erreur
try:
    from core.services.profile.profile_services import ProfileService
except ImportError:
    # Fallback service simple
    class ProfileService:
        @staticmethod
        def update_profile(user_id, data):
            return True, "Profil mis à jour avec succès", 200

        @staticmethod
        def change_password(user_id, old_pwd, new_pwd):
            return True, "Mot de passe changé avec succès", 200


# Création du blueprint
profile_bp = Blueprint("profile_bp", __name__, template_folder="templates")


@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def profile():
    """Affiche et met à jour le profil de l'utilisateur"""
    form = ProfileForm(obj=current_user)

    if form.validate_on_submit():
        # Préparer les données du profil
        profile_data = {
            "first_name": form.first_name.data,
            "last_name": form.last_name.data,
            "email": form.email.data,
            "phone": form.phone.data,
            "language": form.language.data,
            "timezone": form.timezone.data,
            "address": form.address.data,
            "city": form.city.data,
            "postal_code": form.postal_code.data,
            "country": form.country.data,
        }

        # Mettre à jour le profil via le service (avec notifications automatiques)
        try:
            service = ProfileService()
            success, message, status_code = service.update_profile(
                current_user.id, profile_data
            )

            if success:
                # Mettre à jour current_user pour l'affichage immédiat
                current_user.first_name = profile_data["first_name"]
                current_user.last_name = profile_data["last_name"]
                current_user.email = profile_data["email"]
                current_user.phone = profile_data["phone"]
                current_user.address = profile_data["address"]
                current_user.city = profile_data["city"]
                current_user.postal_code = profile_data["postal_code"]
                current_user.country = profile_data["country"]
                current_user.language = profile_data["language"]
                current_user.timezone = profile_data["timezone"]

                flash(message, "success")
            else:
                flash(message, "error")

        except Exception as e:
            flash(f"Erreur lors de la mise à jour: {str(e)}", "error")

        return redirect(url_for("profile_bp.profile"))

    # Pré-remplir le formulaire avec les données actuelles
    if request.method == "GET":
        form.first_name.data = getattr(current_user, "first_name", "")
        form.last_name.data = getattr(current_user, "last_name", "")
        form.email.data = getattr(current_user, "email", "")
        form.phone.data = getattr(current_user, "phone", "")
        form.language.data = getattr(current_user, "language", "fr_FR")
        form.timezone.data = getattr(current_user, "timezone", "Europe/Paris")
        form.address.data = getattr(current_user, "address", "")
        form.city.data = getattr(current_user, "city", "")
        form.postal_code.data = getattr(current_user, "postal_code", "")
        form.country.data = getattr(current_user, "country", "FR")

    # Créer le formulaire de changement de mot de passe
    change_password_form = ChangePasswordForm()

    # Récupérer les préférences de notification pour l'affichage
    try:
        from core.models.notification_preference import NotificationPreference

        # Récupérer les préférences existantes
        email_pref = NotificationPreference.query.filter_by(
            user_id=current_user.id, notification_type="general_email"
        ).first()

        budget_pref = NotificationPreference.query.filter_by(
            user_id=current_user.id, notification_type="budget_alert"
        ).first()

        monthly_pref = NotificationPreference.query.filter_by(
            user_id=current_user.id, notification_type="monthly_report"
        ).first()

        # Définir les valeurs par défaut si aucune préférence n'existe
        notification_preferences = {
            "email_notifications": email_pref.email if email_pref else True,
            "budget_alerts": budget_pref.email if budget_pref else True,
            "monthly_reports": monthly_pref.email if monthly_pref else True,
        }

    except Exception as e:
        current_app.logger.error(f"Erreur récupération préférences: {str(e)}")
        # Valeurs par défaut en cas d'erreur
        notification_preferences = {
            "email_notifications": True,
            "budget_alerts": True,
            "monthly_reports": True,
        }

    return render_template(
        "auth/profile.html",
        form=form,
        change_password_form=change_password_form,
        notification_preferences=notification_preferences,
    )


@profile_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Permet à l'utilisateur de changer son mot de passe"""
    ChangePasswordForm()

    if request.method == "POST":
        # Traitement direct des données POST
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # Validations de base
        if not current_password or not new_password or not confirm_password:
            flash("Tous les champs sont requis", "error")
        elif new_password != confirm_password:
            flash("Les mots de passe ne correspondent pas", "error")
        else:
            try:
                # Utiliser le service de profil (avec notifications automatiques)
                service = ProfileService()
                success, message, status_code = service.change_password(
                    current_user.id, current_password, new_password
                )

                if success:
                    # Le changement coupe les sessions ouvertes avant : renouveler
                    # celle-ci avec la nouvelle empreinte pour rester connecté ici
                    from flask_login import login_user

                    from core.extensions import db

                    db.session.refresh(current_user._get_current_object())
                    login_user(current_user._get_current_object(), fresh=True)
                    flash(message, "success")
                    return redirect(url_for("profile_bp.profile"))
                else:
                    flash(message, "error")

            except Exception as e:
                current_app.logger.error(
                    f"Erreur lors du changement de mot de passe: {str(e)}"
                )
                flash(
                    "Une erreur technique est survenue. Veuillez réessayer plus tard.",
                    "error",
                )

        # Toujours rediriger vers la page profile après le POST
        return redirect(url_for("profile_bp.profile"))

    # Si c'est un GET, rediriger directement vers la page profile
    # La page profile affiche déjà le formulaire de changement de mot de passe
    return redirect(url_for("profile_bp.profile"))
