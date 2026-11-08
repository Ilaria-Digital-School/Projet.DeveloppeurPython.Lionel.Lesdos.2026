"""
Module pour l'envoi d'emails dans l'application.
"""

from flask import current_app, render_template
from flask_mail import Message

from core.extensions import mail


def send_email(subject, sender, recipients, text_body, html_body):
    """
    Envoie un email.

    Args:
        subject: Sujet de l'email
        sender: Adresse email de l'expéditeur
        recipients: Liste des adresses email des destinataires
        text_body: Corps du message en texte brut
        html_body: Corps du message en HTML
    """
    msg = Message(
        subject=subject,
        sender=sender,
        recipients=recipients,
        body=text_body,
        html=html_body,
    )
    mail.send(msg)


def send_password_reset_email(user_email, reset_url):
    """
    Envoie un email de réinitialisation de mot de passe.

    Args:
        user_email: Adresse email de l'utilisateur
        reset_url: URL de réinitialisation à inclure dans l'email
    """
    subject = "Réinitialisation de votre mot de passe"
    sender = current_app.config["MAIL_DEFAULT_SENDER"]
    recipients = [user_email]

    # Rendu des templates d'email
    from datetime import datetime

    template_vars = {
        "reset_url": reset_url,
        "user": {"first_name": "Utilisateur"},  # Nom générique
        "app_name": "Budget App",
        "now": datetime.now(),
    }
    text_body = render_template("emails/reset_password.txt", **template_vars)
    html_body = render_template("emails/reset_password.html", **template_vars)

    send_email(subject, sender, recipients, text_body, html_body)
