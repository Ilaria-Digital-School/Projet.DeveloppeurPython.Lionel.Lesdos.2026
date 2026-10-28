"""
Routes d'authentification web (HTML).

Ce module contient les routes d'authentification pour l'interface utilisateur :
- Connexion / Inscription / Déconnexion
- Réinitialisation de mot de passe
- Vérification 2FA

Les routes API JSON ont été migrées vers /api/v1/auth.
"""

import logging

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from api.v1.auth import auth_limiter
from app.utils.errors import ValidationError
from core.extensions import db
from core.models.user import User

# Imports des services et modèles
from core.services.auth import AuthSecurityService
from core.services.user.services import UserService

# Import des formulaires
from .auth_forms import (
    LoginForm,
    RegistrationForm,
    ResetPasswordForm,
    ResetPasswordRequestForm,
)

# Configuration du logger
logger = logging.getLogger(__name__)

# Création du blueprint unifié pour l'authentification
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# ============================================================================
# ROUTES WEB (Interface HTML)
# ============================================================================


@auth_bp.route("/login", methods=["GET", "POST"])
@auth_limiter.limit("5 per minute", methods=["POST"])
def login():
    """
    Page de connexion web.
    GET: Affiche le formulaire de connexion
    POST: Traite la connexion
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_bp.dashboard"))

    form = LoginForm()

    if form.validate_on_submit():
        try:
            from core.services.auth.security_service import init_security_service

            security_svc = init_security_service(db)

            # Chercher l'utilisateur pour vérifier le verrouillage
            lookup_user = User.query.filter_by(email=form.email.data.lower()).first()
            if lookup_user:
                is_locked, unlock_time = security_svc.is_account_locked(lookup_user.id)
                if is_locked:
                    flash(
                        "Compte temporairement verrouillé suite à trop de tentatives. Réessayez plus tard.",
                        "error",
                    )
                    return render_template(
                        "auth/login.html", title="Connexion", form=form
                    )

            # Utiliser le service d'authentification
            auth_service = AuthSecurityService(db=db)
            user, tokens = auth_service.authenticate(
                form.email.data, form.password.data, request.remote_addr
            )

            if user:
                if getattr(user, "_suppression_annulee", False):
                    flash("La suppression de votre compte a été annulée.", "success")

                # Vérifier que l'email est vérifié (seulement si l'envoi d'emails de vérification est activé)
                from flask import current_app

                if (
                    current_app.config.get("SECURITY_SEND_REGISTER_EMAIL", False)
                    and hasattr(user, "email_verified")
                    and not user.email_verified
                ):
                    flash(
                        "Veuillez vérifier votre adresse email avant de vous connecter.",
                        "warning",
                    )
                    return render_template(
                        "auth/login.html", title="Connexion", form=form
                    )

                # Vérifier si la 2FA est activée
                if user.two_factor_enabled:
                    # Pas de "succès" enregistré avant la 2FA : sinon le compteur
                    # d'échecs serait remis à zéro par le seul mot de passe, et
                    # les échecs de 2FA ne mèneraient jamais au verrouillage
                    from core.security.two_factor_flow import demarrer_2fa

                    # Stocker temporairement l'utilisateur en session pour la vérification 2FA
                    session["2fa_user_id"] = user.id
                    session["2fa_remember_me"] = form.remember_me.data
                    # Validation stricte du next_page avant stockage en session
                    _next = request.args.get("next")
                    if not _next or not _next.startswith("/") or _next.startswith("//"):
                        _next = url_for("dashboard_bp.dashboard")
                    session["2fa_next_page"] = _next

                    two_factor_method, envoye = demarrer_2fa(user)
                    if not envoye:
                        flash("Erreur lors de l'envoi du code par email.", "error")
                    session["2fa_method"] = two_factor_method
                    logger.info(
                        f"2FA requise pour l'utilisateur: {user.email} (méthode: {two_factor_method})"
                    )
                    return redirect(url_for("auth.verify_2fa"))
                else:
                    # Connexion normale sans 2FA
                    security_svc.record_login_attempt(user.id, success=True)
                    # Regenerer la session pour eviter la session fixation
                    session.clear()
                    current_app.session_interface.regenerate(session)
                    login_user(user, remember=form.remember_me.data)
                    logger.info(f"Connexion réussie pour l'utilisateur: {user.email}")

                    # Enregistrer l'appareil
                    _register_login_device(user)

                    # Redirection vers la page demandée ou dashboard
                    next_page = request.args.get("next")
                    # Validation stricte : chemin relatif uniquement, pas de protocol-relative URLs
                    if (
                        not next_page
                        or not next_page.startswith("/")
                        or next_page.startswith("//")
                    ):
                        next_page = url_for("dashboard_bp.dashboard")
                    return redirect(next_page)
            else:
                # Enregistrer la tentative échouée
                if lookup_user:
                    is_ok, msg = security_svc.record_login_attempt(
                        lookup_user.id, success=False
                    )
                    if not is_ok:
                        flash(
                            "Compte temporairement verrouillé suite à trop de tentatives. Réessayez plus tard.",
                            "error",
                        )
                    else:
                        flash("Email ou mot de passe incorrect.", "error")
                else:
                    flash("Email ou mot de passe incorrect.", "error")
                logger.warning(
                    f"Tentative de connexion échouée pour: {form.email.data}"
                )

        except Exception as e:
            logger.error(f"Erreur lors de la connexion: {e}")
            flash("Une erreur est survenue lors de la connexion.", "error")

    return render_template("auth/login.html", title="Connexion", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
@auth_limiter.limit("5 per minute", methods=["POST"])
def register():
    """
    Page d'inscription web.
    GET: Affiche le formulaire d'inscription
    POST: Traite l'inscription
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_bp.dashboard"))

    form = RegistrationForm()

    if form.validate_on_submit():
        try:
            # Utiliser le service utilisateur pour créer un compte
            user_service = UserService()
            user = user_service.create_user(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data,
            )

            if user:
                flash(
                    "Inscription réussie ! Vous pouvez maintenant vous connecter.",
                    "success",
                )
                logger.info(f"Nouvel utilisateur créé: {user.email}")
                return redirect(url_for("auth.login"))
            else:
                flash("Erreur lors de la création du compte.", "error")

        except ValidationError as e:
            flash(str(e), "error")
        except Exception as e:
            logger.error(f"Erreur lors de l'inscription: {e}")
            flash("Une erreur est survenue lors de l'inscription.", "error")

    return render_template("auth/register.html", title="Inscription", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """Déconnexion de l'utilisateur."""
    logger.info(f"Déconnexion de l'utilisateur: {current_user.email}")
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/reset-password-request", methods=["GET", "POST"])
@auth_limiter.limit("3 per minute;10 per hour", methods=["POST"])
def reset_password_request():
    """
    Page de demande de réinitialisation de mot de passe.
    GET: Affiche le formulaire de demande
    POST: Traite la demande
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_bp.dashboard"))

    form = ResetPasswordRequestForm()

    if form.validate_on_submit():
        try:
            auth_service = AuthSecurityService()
            result = auth_service.request_password_reset(form.email.data)

            if result:
                flash("Un email de réinitialisation a été envoyé.", "info")
                logger.info(f"Demande de réinitialisation pour: {form.email.data}")
            else:
                flash("Erreur lors de l'envoi de l'email.", "error")

        except Exception as e:
            logger.error(f"Erreur lors de la demande de réinitialisation: {e}")
            flash("Une erreur est survenue.", "error")

    return render_template(
        "auth/reset_password_request.html",
        title="Réinitialiser le mot de passe",
        form=form,
    )


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
# auth_limiter (et non un Limiter local jamais rattaché à l'app par init_app,
# dont la limite était sans effet)
@auth_limiter.limit("5 per minute", methods=["POST"])
def reset_password(token):
    """
    Page de réinitialisation de mot de passe avec token.
    GET: Affiche le formulaire de nouveau mot de passe
    POST: Traite la réinitialisation
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_bp.dashboard"))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        try:
            auth_service = AuthSecurityService()
            result = auth_service.reset_password_with_token(token, form.password.data)

            if result:
                flash("Votre mot de passe a été réinitialisé.", "success")
                return redirect(url_for("auth.login"))
            else:
                flash("Token invalide ou expiré.", "error")

        except Exception as e:
            logger.error(f"Erreur lors de la réinitialisation: {e}")
            flash("Une erreur est survenue.", "error")

    return render_template(
        "auth/reset_password.html", title="Nouveau mot de passe", form=form, token=token
    )


# ============================================================================
# ROUTES 2FA (Two-Factor Authentication)
# ============================================================================


@auth_bp.route("/verify-2fa", methods=["GET", "POST"])
@auth_limiter.limit("10 per minute", methods=["POST"])
def verify_2fa():
    """
    Page de vérification 2FA après connexion réussie avec mot de passe.

    Chaque code faux compte comme un échec de connexion : au bout de
    LOGIN_ATTEMPTS_LIMIT, le compte est verrouillé et il faut se reconnecter.
    """
    from core.security.two_factor_flow import verifier_2fa
    from core.services.auth.security_service import init_security_service

    # Vérifier que l'utilisateur est bien en attente de vérification 2FA
    if "2fa_user_id" not in session:
        flash("Session expirée. Veuillez vous connecter à nouveau.", "error")
        return redirect(url_for("auth.login"))

    user = db.session.get(User, session["2fa_user_id"])
    if not user or not user.two_factor_enabled:
        flash("Erreur de vérification 2FA.", "error")
        session.pop("2fa_user_id", None)
        return redirect(url_for("auth.login"))

    security_svc = init_security_service(db)

    def _abandonner_2fa():
        """Compte verrouillé : invalider le code et la connexion en cours."""
        user.email_2fa_code = None
        db.session.commit()
        for cle in ("2fa_user_id", "2fa_remember_me", "2fa_next_page", "2fa_method"):
            session.pop(cle, None)
        flash(
            "Compte temporairement verrouillé suite à trop de tentatives. Réessayez plus tard.",
            "error",
        )
        return redirect(url_for("auth.login"))

    if security_svc.is_account_locked(user.id)[0]:
        return _abandonner_2fa()

    if request.method == "POST":
        try:
            ok, message = verifier_2fa(
                user,
                code=request.form.get("code", ""),
                backup_code=request.form.get("backup_code", ""),
            )
            if not ok:
                logger.warning(
                    f"❌ Vérification 2FA échouée pour {user.email}: {message}"
                )
                non_verrouille, _ = security_svc.record_login_attempt(
                    user.id, success=False
                )
                if not non_verrouille:
                    return _abandonner_2fa()
                flash(message or "Code de vérification invalide ou expiré.", "error")
            else:
                security_svc.record_login_attempt(user.id, success=True)
                if message:
                    flash(message, "warning")  # code de récupération utilisé

                # Finaliser la connexion
                remember_me = session.get("2fa_remember_me", False)
                next_page = session.get(
                    "2fa_next_page", url_for("dashboard_bp.dashboard")
                )

                # Re-validation défensive du next_page
                if (
                    not next_page
                    or not next_page.startswith("/")
                    or next_page.startswith("//")
                ):
                    next_page = url_for("dashboard_bp.dashboard")

                # Nettoyer la session 2FA et regenerer pour eviter la session fixation
                session.clear()
                current_app.session_interface.regenerate(session)

                # Connecter l'utilisateur
                login_user(user, remember=remember_me)
                logger.info(f"📱 ✅ Connexion 2FA complète pour {user.email}")

                # Enregistrer l'appareil
                _register_login_device(user)

                flash("Connexion réussie !", "success")
                return redirect(next_page)

        except Exception as e:
            logger.error(f"📱 💥 Erreur vérification 2FA: {str(e)}")
            flash("Erreur lors de la vérification. Veuillez réessayer.", "error")

    # Récupérer la méthode 2FA depuis la session
    two_factor_method = session.get("2fa_method", "app")

    return render_template(
        "auth/verify_2fa.html",
        title="Vérification en deux étapes",
        user_email=user.email,
        two_factor_method=two_factor_method,
    )


def _register_login_device(user):
    """Enregistre l'appareil utilisé pour la connexion web."""
    try:
        import hashlib

        from user_agents import parse as parse_ua

        from core.services.devices.device_services import DeviceService

        ua_string = request.headers.get("User-Agent", "")
        # IP de repli si remote_addr absent (valeur, pas un bind socket)
        ip = request.remote_addr or "0.0.0.0"  # nosec B104
        ua = parse_ua(ua_string)

        device_id = hashlib.sha256(f"{ua_string}:{ip}".encode()).hexdigest()[:64]

        if ua.is_mobile:
            device_type = "mobile"
        elif ua.is_tablet:
            device_type = "tablet"
        else:
            device_type = "desktop"

        browser = ua.browser.family or "Unknown"
        os_name = ua.os.family or "Unknown"
        name = f"{browser} sur {os_name}"

        device_data = {
            "name": name,
            "device_id": device_id,
            "device_type": device_type,
            "os": os_name,
            "os_version": ua.os.version_string or None,
            "browser": browser,
            "browser_version": ua.browser.version_string or None,
        }

        device, _ = DeviceService.register_device(
            user_id=user.id,
            device_data=device_data,
            ip_address=ip,
            user_agent=ua_string,
        )

        if device:
            from datetime import datetime, timezone

            device.last_used = datetime.now(timezone.utc)
            device.ip_address = ip
            db.session.commit()

    except Exception as e:
        logger.warning(f"Impossible d'enregistrer l'appareil: {e}")
