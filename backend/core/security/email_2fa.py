"""
Email-based Two-Factor Authentication (2FA) Service

This module provides email-based 2FA functionality as an alternative
to TOTP-based authenticator apps.
"""

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Tuple

from flask import current_app, render_template
from flask_mail import Message

from core.extensions import db, mail


class EmailTwoFactorAuth:
    """Handles email-based two-factor authentication operations."""

    @staticmethod
    def generate_email_code(length: int = 6) -> str:
        """
        Generate a random numeric code for email 2FA.

        Args:
            length: Length of the code (default 6 digits)

        Returns:
            String containing random digits
        """
        return "".join(secrets.choice(string.digits) for _ in range(length))

    @staticmethod
    def send_2fa_email(user_email: str, code: str) -> bool:
        """
        Send 2FA code via email.

        Args:
            user_email: Email address to send code to
            code: 6-digit verification code

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            subject = "Code de vérification - Budget App"
            sender = current_app.config.get("MAIL_DEFAULT_SENDER")

            # Render email templates
            text_body = render_template(
                "emails/2fa_code.txt", code=code, expiry_minutes=15
            )
            html_body = render_template(
                "emails/2fa_code.html", code=code, expiry_minutes=15
            )

            msg = Message(
                subject=subject,
                sender=sender,
                recipients=[user_email],
                body=text_body,
                html=html_body,
            )

            mail.send(msg)
            current_app.logger.info(f"📧 Code 2FA envoyé par email à {user_email}")
            return True

        except Exception as e:
            current_app.logger.error(f"📧 Erreur envoi email 2FA: {str(e)}")
            return False

    @staticmethod
    def store_email_2fa_code(user, code: str, expiry_minutes: int = 15) -> bool:
        """
        Store 2FA code in database with expiration.

        Args:
            user: User object
            code: 6-digit code to store
            expiry_minutes: Minutes until code expires (default 15)

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Store code and expiration in dedicated email_2fa_code field
            expiry = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)

            # Format: "CODE|EXPIRY_TIMESTAMP"
            user.email_2fa_code = f"{code}|{expiry.timestamp()}"
            db.session.commit()

            current_app.logger.info(f"📧 Code 2FA stocké pour {user.email}")
            return True

        except Exception as e:
            current_app.logger.error(f"📧 Erreur stockage code 2FA: {str(e)}")
            db.session.rollback()
            return False

    @staticmethod
    def verify_email_2fa_code(user, submitted_code: str) -> Tuple[bool, str]:
        """
        Verify email 2FA code.

        Args:
            user: User object
            submitted_code: Code submitted by user

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not user.email_2fa_code:
                return False, "Aucun code 2FA en attente"

            # Parse stored code and expiry
            if "|" not in user.email_2fa_code:
                return False, "Code 2FA invalide (format)"

            stored_code, expiry_str = user.email_2fa_code.split("|", 1)
            expiry = datetime.fromtimestamp(float(expiry_str), tz=timezone.utc)

            # Check if code expired
            if datetime.now(timezone.utc) > expiry:
                # Clean expired code
                user.email_2fa_code = None
                db.session.commit()
                return False, "Code expiré. Demandez un nouveau code."

            # Check code match
            if stored_code != submitted_code.strip():
                return False, "Code incorrect"

            # Code valid - clean it (one-time use)
            user.email_2fa_code = None
            db.session.commit()

            current_app.logger.info(
                f"📧 Code 2FA vérifié avec succès pour {user.email}"
            )
            return True, "Code vérifié avec succès"

        except Exception as e:
            current_app.logger.error(f"📧 Erreur vérification code 2FA: {str(e)}")
            return False, "Erreur de vérification"

    @staticmethod
    def has_pending_code(user) -> bool:
        """
        Check if user has a pending (non-expired) 2FA code.

        Args:
            user: User object

        Returns:
            True if pending code exists, False otherwise
        """
        try:
            if not user.email_2fa_code or "|" not in user.email_2fa_code:
                return False

            _, expiry_str = user.email_2fa_code.split("|", 1)
            expiry = datetime.fromtimestamp(float(expiry_str), tz=timezone.utc)

            return datetime.now(timezone.utc) <= expiry

        except ValueError, AttributeError, TypeError:
            return False

    @staticmethod
    def clean_expired_codes():
        """
        Clean expired 2FA codes from database.
        This can be run as a background task.
        """
        try:
            from core.models.user import User

            users_with_codes = User.query.filter(
                User.email_2fa_code.isnot(None), User.email_2fa_code.like("%|%")
            ).all()

            cleaned_count = 0
            for user in users_with_codes:
                try:
                    _, expiry_str = user.email_2fa_code.split("|", 1)
                    expiry = datetime.fromtimestamp(float(expiry_str), tz=timezone.utc)

                    if datetime.now(timezone.utc) > expiry:
                        user.email_2fa_code = None
                        cleaned_count += 1

                except ValueError, AttributeError, TypeError:
                    # Invalid format, clean it
                    user.email_2fa_code = None
                    cleaned_count += 1

            if cleaned_count > 0:
                db.session.commit()
                current_app.logger.info(
                    f"📧 {cleaned_count} codes 2FA expirés nettoyés"
                )

        except Exception as e:
            current_app.logger.error(f"📧 Erreur nettoyage codes expirés: {str(e)}")
            db.session.rollback()
